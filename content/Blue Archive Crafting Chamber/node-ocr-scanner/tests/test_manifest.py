from pathlib import Path

from crafting_ocr.manifest import NodeManifestIndex, normalize_node_name


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED = PROJECT_ROOT / "crafting-data-builder" / "generated"


def load_index() -> NodeManifestIndex:
    return NodeManifestIndex.from_files(
        GENERATED / "node_manifest.json",
        GENERATED / "crafting_table.json",
    )


def test_normalize_node_name_removes_spaces_and_decoration() -> None:
    assert normalize_node_name("  반짝임!\n") == "반짝임"


def test_stage_one_rarity_nodes_resolve_to_distinct_ids() -> None:
    index = load_index()
    assert index.resolve_exact(1, "은은함").node_id == 1
    assert index.resolve_exact(1, "영롱함").node_id == 2
    assert index.resolve_exact(1, "반짝임").node_id == 3


def test_same_name_resolves_by_stage() -> None:
    index = load_index()
    assert index.resolve_exact(1, "반짝임").node_id == 3
    assert index.resolve_exact(2, "반짝임").node_id == 23
    assert index.resolve_exact(3, "반짝임").node_id == 3000
