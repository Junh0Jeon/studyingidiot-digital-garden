from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    pass


def normalize_node_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character)[0] in {"L", "N"}
    )


def levenshtein_distance(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1]
                    + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class NodeNameEntry:
    stage: int
    node_id: int
    name_kr: str
    normalized_name_kr: str


class NodeManifestIndex:
    def __init__(self, entries: list[NodeNameEntry]) -> None:
        self._by_stage_and_name: dict[tuple[int, str], NodeNameEntry] = {}
        self._by_stage: dict[int, list[NodeNameEntry]] = {}
        for entry in entries:
            key = (entry.stage, entry.normalized_name_kr)
            if key in self._by_stage_and_name:
                other = self._by_stage_and_name[key]
                raise ManifestError(
                    "Duplicate normalized Korean node name: "
                    f"stage={entry.stage}, name={entry.name_kr!r}, "
                    f"nodeIds={other.node_id},{entry.node_id}"
                )
            self._by_stage_and_name[key] = entry
            self._by_stage.setdefault(entry.stage, []).append(entry)

    @classmethod
    def from_files(cls, manifest_path: Path, crafting_table_path: Path) -> "NodeManifestIndex":
        manifest = cls._read_json(manifest_path)
        crafting_table = cls._read_json(crafting_table_path).get("craftingTable")
        if not isinstance(crafting_table, dict):
            raise ManifestError("crafting_table.json has no craftingTable object")

        raw_nodes = manifest.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ManifestError("node_manifest.json has no nodes array")

        entries: list[NodeNameEntry] = []
        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                raise ManifestError("Manifest node must be an object")
            try:
                stage = int(raw_node["stage"])
                node_id = int(raw_node["nodeId"])
                name_kr = str(raw_node["nameKr"])
            except (KeyError, TypeError, ValueError) as error:
                raise ManifestError(f"Invalid manifest node: {raw_node!r}") from error
            if str(node_id) not in crafting_table.get(str(stage), {}):
                raise ManifestError(
                    f"Node {node_id} at stage {stage} is absent from crafting_table.json"
                )
            normalized = normalize_node_name(name_kr)
            if not normalized:
                raise ManifestError(f"Node {node_id} has an empty normalized Korean name")
            entries.append(NodeNameEntry(stage, node_id, name_kr, normalized))
        return cls(entries)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManifestError(f"Cannot read JSON {path}: {error}") from error
        if not isinstance(value, dict):
            raise ManifestError(f"Expected a JSON object in {path}")
        return value

    def resolve_exact(self, stage: int, text: str) -> NodeNameEntry | None:
        return self._by_stage_and_name.get((stage, normalize_node_name(text)))

    def nearest(self, stage: int, text: str, limit: int = 3) -> list[dict[str, Any]]:
        normalized = normalize_node_name(text)
        ranked = sorted(
            self._by_stage.get(stage, ()),
            key=lambda entry: (
                levenshtein_distance(normalized, entry.normalized_name_kr),
                entry.node_id,
            ),
        )
        return [
            {
                "nodeId": entry.node_id,
                "nameKr": entry.name_kr,
                "normalizedNameKr": entry.normalized_name_kr,
                "distance": levenshtein_distance(normalized, entry.normalized_name_kr),
            }
            for entry in ranked[:limit]
        ]
