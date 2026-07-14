#!/usr/bin/env python3
"""Build a normalized Blue Archive crafting table from SchaleDB data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BASE_URL = "https://schaledb.com"
SERVER_INDEX = {"jp": 0, "global": 1, "cn": 2}
JSON_SOURCES = {
    "crafting": "/data/crafting.min.json",
    "groups": "/data/groups.min.json",
    "items": "/data/{language}/items.min.json",
    "furniture": "/data/{language}/furniture.min.json",
}
NORMAL_GIFT_RARITY = "SR"
ADVANCED_GIFT_RARITY = "SSR"


class BuildError(RuntimeError):
    """Raised when source data cannot be converted safely."""


@dataclass(frozen=True)
class BuildConfig:
    output_dir: Path
    server: str
    language: str
    offline: bool
    skip_icons: bool

    @property
    def raw_dir(self) -> Path:
        return self.output_dir / "raw"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download SchaleDB data and build CRAFTING_TABLE."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
        help="Output directory (default: ./generated)",
    )
    parser.add_argument(
        "--server",
        choices=tuple(SERVER_INDEX),
        default="global",
        help="Server used for release filtering (default: global)",
    )
    parser.add_argument(
        "--language",
        default="kr",
        help="SchaleDB language directory (default: kr)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Rebuild from output-dir/raw without network access",
    )
    parser.add_argument(
        "--skip-icons",
        action="store_true",
        help="Do not download craft-node icons",
    )
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(
        value, ensure_ascii=False, indent=2, sort_keys=False
    ).encode("utf-8")
    write_bytes(path, payload + b"\n")


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,image/*;q=0.9,*/*;q=0.1",
            "User-Agent": "BlueArchiveCraftingDataBuilder/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise BuildError(f"Failed to download {url}: {error}") from error


def load_source_json(
    name: str, path_template: str, config: BuildConfig
) -> tuple[Any, dict[str, Any]]:
    raw_path = config.raw_dir / f"{name}.json"
    url = BASE_URL + path_template.format(language=config.language)
    if config.offline:
        if not raw_path.exists():
            raise BuildError(
                f"Offline source is missing: {raw_path}. "
                "Run once without --offline."
            )
        payload = raw_path.read_bytes()
    else:
        payload = download(url)
        write_bytes(raw_path, payload)

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BuildError(f"Invalid JSON from {url}: {error}") from error

    return data, {
        "name": name,
        "url": url,
        "localPath": raw_path.relative_to(config.output_dir).as_posix(),
        "sha256": sha256(payload),
        "bytes": len(payload),
    }


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildError(f"Expected {label} to be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise BuildError(f"Expected {label} to be an array")
    return value


def require_fields(value: dict[str, Any], fields: Iterable[str], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise BuildError(f"{label} is missing fields: {', '.join(missing)}")


def is_released(node: dict[str, Any], server: str) -> bool:
    released = node.get("Released")
    if not isinstance(released, list):
        raise BuildError(f"Node {node.get('Id')} has invalid Released data")
    index = SERVER_INDEX[server]
    if index >= len(released):
        raise BuildError(f"Node {node.get('Id')} has no release flag for {server}")
    return bool(released[index])


def lookup_metadata(
    source_type: str,
    item_id: int,
    items: dict[str, Any],
    furniture: dict[str, Any],
) -> dict[str, Any] | None:
    if source_type == "Item":
        return items.get(str(item_id))
    if source_type == "Furniture":
        return furniture.get(str(item_id))
    return None


def convert_item_type(source_type: str, metadata: dict[str, Any] | None) -> str:
    if source_type == "Furniture":
        return "Furniture"
    if source_type == "Item" and metadata and metadata.get("Category") == "Favor":
        return "Gift"
    return source_type


def convert_gift_grade(
    item_type: str,
    metadata: dict[str, Any] | None,
    item_id: int,
) -> str | None:
    if item_type != "Gift":
        return None
    if metadata is None:
        raise BuildError(f"Gift metadata is missing for item {item_id}")
    rarity = metadata.get("Rarity")
    if rarity == NORMAL_GIFT_RARITY:
        return "Normal"
    if rarity == ADVANCED_GIFT_RARITY:
        return "Advanced"
    raise BuildError(f"Unsupported gift rarity {rarity!r} for item {item_id}")


def make_result_key(result: dict[str, Any]) -> tuple[Any, ...]:
    return (
        result["itemId"],
        result["itemType"],
        result["giftGrade"],
        result["minQuantity"],
        result["maxQuantity"],
    )


def build_node_results(
    node: dict[str, Any],
    groups: dict[str, Any],
    items: dict[str, Any],
    furniture: dict[str, Any],
) -> list[dict[str, Any]]:
    require_fields(node, ("Id", "Tier", "Groups"), "Crafting node")
    node_id = int(node["Id"])
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    node_groups = require_list(node["Groups"], f"Node {node_id}.Groups")
    total_group_weight = sum(float(group.get("Weight", 0)) for group in node_groups)
    if total_group_weight <= 0:
        raise BuildError(f"Node {node_id} has non-positive total group weight")

    for node_group in node_groups:
        require_fields(node_group, ("GroupId", "Weight"), f"Node {node_id} group")
        group_id = str(node_group["GroupId"])
        group = groups.get(group_id)
        if group is None:
            raise BuildError(f"Node {node_id} references missing group {group_id}")
        require_fields(group, ("Items",), f"Group {group_id}")
        # This is the formula used by SchaleDB's CraftNodeRender. Node.Property
        # participates in node appearance calculations, not reward selection.
        group_probability = float(node_group["Weight"]) / total_group_weight

        for source_result in require_list(group["Items"], f"Group {group_id}.Items"):
            require_fields(
                source_result,
                ("Type", "Id", "Chance", "AmountMin", "AmountMax"),
                f"Group {group_id} result",
            )
            source_type = str(source_result["Type"])
            item_id = int(source_result["Id"])
            metadata = lookup_metadata(source_type, item_id, items, furniture)
            if source_type in {"Item", "Furniture"} and metadata is None:
                raise BuildError(
                    f"Metadata is missing for {source_type} {item_id} "
                    f"referenced by group {group_id}"
                )

            item_type = convert_item_type(source_type, metadata)
            result = {
                "itemId": item_id,
                "itemType": item_type,
                "giftGrade": convert_gift_grade(item_type, metadata, item_id),
                "probability": 0.0,
                "minQuantity": int(source_result["AmountMin"]),
                "maxQuantity": int(source_result["AmountMax"]),
            }
            key = make_result_key(result)
            if key not in merged:
                merged[key] = result
            merged[key]["probability"] += (
                group_probability * float(source_result["Chance"])
            )

    results = list(merged.values())
    results.sort(key=lambda result: (result["itemType"], result["itemId"]))
    return results


def build_crafting_table(
    crafting: dict[str, Any],
    groups: dict[str, Any],
    items: dict[str, Any],
    furniture: dict[str, Any],
    server: str,
) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], list[dict[str, Any]]]:
    require_fields(crafting, ("Nodes",), "Crafting data")
    table: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    node_manifest: list[dict[str, Any]] = []

    for node in require_list(crafting["Nodes"], "Crafting data.Nodes"):
        require_fields(
            node,
            ("Id", "Tier", "Quality", "Icon", "NameEn", "NameKr"),
            "Crafting node",
        )
        if not is_released(node, server):
            continue
        stage = str(int(node["Tier"]))
        node_id = str(int(node["Id"]))
        table[stage][node_id] = build_node_results(
            node, groups, items, furniture
        )
        node_manifest.append(
            {
                "nodeId": int(node["Id"]),
                "stage": int(node["Tier"]),
                "quality": int(node["Quality"]),
                "iconId": str(node["Icon"]),
                "nameEn": str(node["NameEn"]),
                "nameKr": str(node["NameKr"]),
            }
        )

    ordered_table = {
        stage: dict(sorted(nodes.items(), key=lambda pair: int(pair[0])))
        for stage, nodes in sorted(table.items(), key=lambda pair: int(pair[0]))
    }
    node_manifest.sort(key=lambda node: (node["stage"], node["nodeId"]))
    return ordered_table, node_manifest


def validate_crafting_table(
    table: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    warnings: list[str] = []
    node_count = 0
    result_count = 0
    for stage, nodes in table.items():
        for node_id, results in nodes.items():
            node_count += 1
            result_count += len(results)
            probability_sum = sum(float(result["probability"]) for result in results)
            if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=0.02):
                warnings.append(
                    f"stage={stage} nodeId={node_id}: "
                    f"result probability sum is {probability_sum:.8f}"
                )
            for result in results:
                probability = float(result["probability"])
                if probability < 0 or probability > 1:
                    raise BuildError(
                        f"Invalid probability {probability} in node {node_id}"
                    )
                if result["minQuantity"] > result["maxQuantity"]:
                    raise BuildError(f"Invalid quantity range in node {node_id}")

    return {
        "valid": not warnings,
        "nodeCount": node_count,
        "resultCount": result_count,
        "warningCount": len(warnings),
        "warnings": warnings,
    }


def build_icon_manifest(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    by_icon: dict[str, list[int]] = defaultdict(list)
    for node in nodes:
        by_icon[node["iconId"]].append(node["nodeId"])
    return {
        icon_id: {
            "url": f"{BASE_URL}/images/craftnode/{icon_id}.png",
            "localPath": f"icons/{icon_id}.png",
            "nodeIds": sorted(node_ids),
        }
        for icon_id, node_ids in sorted(by_icon.items())
    }


def fetch_icons(icon_manifest: dict[str, Any], config: BuildConfig) -> None:
    if config.skip_icons:
        return
    for icon_id, icon in icon_manifest.items():
        path = config.output_dir / icon["localPath"]
        if config.offline:
            if not path.exists():
                raise BuildError(f"Offline icon is missing: {path}")
            continue
        payload = download(icon["url"])
        if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
            raise BuildError(f"Icon {icon_id} is not a PNG: {icon['url']}")
        write_bytes(path, payload)
        icon["sha256"] = sha256(payload)
        icon["bytes"] = len(payload)


def run(config: BuildConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    loaded: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    for name, path_template in JSON_SOURCES.items():
        loaded[name], source = load_source_json(name, path_template, config)
        sources.append(source)

    table, node_manifest = build_crafting_table(
        require_mapping(loaded["crafting"], "crafting"),
        require_mapping(loaded["groups"], "groups"),
        require_mapping(loaded["items"], "items"),
        require_mapping(loaded["furniture"], "furniture"),
        config.server,
    )
    validation = validate_crafting_table(table)
    icon_manifest = build_icon_manifest(node_manifest)
    fetch_icons(icon_manifest, config)

    metadata = {
        "schemaVersion": 1,
        "generatedAt": utc_now(),
        "server": config.server,
        "language": config.language,
        "source": "SchaleDB",
        "sources": sources,
        "giftGradeRules": {
            "category": "Favor",
            NORMAL_GIFT_RARITY: "Normal",
            ADVANCED_GIFT_RARITY: "Advanced",
        },
    }
    write_json(
        config.output_dir / "crafting_table.json",
        {"metadata": metadata, "craftingTable": table},
    )
    write_json(
        config.output_dir / "node_manifest.json",
        {"metadata": metadata, "nodes": node_manifest, "icons": icon_manifest},
    )
    write_json(config.output_dir / "validation_report.json", validation)
    return validation


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = BuildConfig(
        output_dir=args.output_dir.resolve(),
        server=args.server,
        language=args.language,
        offline=args.offline,
        skip_icons=args.skip_icons,
    )
    try:
        report = run(config)
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Built crafting data in {config.output_dir}")
    print(
        f"nodes={report['nodeCount']} results={report['resultCount']} "
        f"warnings={report['warningCount']}"
    )
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
