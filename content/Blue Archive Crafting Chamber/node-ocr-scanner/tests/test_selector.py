from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from crafting_ocr.selector import (
    CraftingTable,
    CraftingTableError,
    GiftPrioritySelector,
    SelectionError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED = PROJECT_ROOT / "crafting-data-builder" / "generated"


def result(
    *,
    item_id: int,
    item_type: str,
    probability: float,
    minimum: int = 1,
    maximum: int = 1,
    gift_grade: str | None = None,
) -> dict[str, object]:
    return {
        "itemId": item_id,
        "itemType": item_type,
        "giftGrade": gift_grade,
        "probability": probability,
        "minQuantity": minimum,
        "maxQuantity": maximum,
    }


def table_with(nodes: dict[str, list[dict[str, object]]]) -> CraftingTable:
    return CraftingTable.from_mapping({"1": nodes})


def test_real_candidates_select_shiny_node() -> None:
    table = CraftingTable.from_json(GENERATED / "crafting_table.json")
    selector = GiftPrioritySelector(table)

    decision = selector.select_best_node(1, [7, 1, 3, 5, 11])

    assert decision.recommended_node_id == 3
    assert decision.gift_score == pytest.approx(0.6230290456431535)
    assert decision.furniture_score == pytest.approx(0.06136929460580912)
    assert decision.selection_reason == "highest-gift-score"
    assert [item.node_id for item in decision.evaluations] == [7, 1, 3, 5, 11]


def test_gift_score_uses_grade_weight_and_average_quantity() -> None:
    table = table_with(
        {
            "1": [
                result(
                    item_id=100,
                    item_type="Gift",
                    gift_grade="Normal",
                    probability=0.5,
                    minimum=2,
                    maximum=2,
                ),
                result(
                    item_id=101,
                    item_type="Gift",
                    gift_grade="Advanced",
                    probability=0.25,
                    minimum=2,
                    maximum=4,
                ),
            ]
        }
    )

    decision = GiftPrioritySelector(table).select_best_node(1, [1])

    assert decision.gift_score == pytest.approx(3.25)


def test_furniture_breaks_equal_gift_score() -> None:
    table = table_with(
        {
            "1": [result(item_id=1, item_type="Item", probability=1)],
            "2": [result(item_id=2, item_type="Furniture", probability=1)],
        }
    )

    decision = GiftPrioritySelector(table).select_best_node(1, [1, 2])

    assert decision.recommended_node_id == 2
    assert decision.selection_reason == "highest-furniture-score"


def test_injected_random_choice_handles_full_tie_and_preserves_evaluations() -> None:
    calls: list[tuple[int, ...]] = []

    def choose_last(values: Sequence[int]) -> int:
        calls.append(tuple(values))
        return values[-1]

    table = table_with(
        {
            "1": [result(item_id=1, item_type="Item", probability=1)],
            "2": [result(item_id=2, item_type="Item", probability=1)],
        }
    )
    selector = GiftPrioritySelector(table, random_choice=choose_last)

    decision = selector.select_best_node(1, [1, 1, 2])

    assert calls == [(1, 1, 2)]
    assert decision.recommended_node_id == 2
    assert decision.tied_node_ids == (1, 2)
    assert [item.node_id for item in decision.evaluations] == [1, 1, 2]
    assert decision.selection_reason == "random-tiebreak"


@pytest.mark.parametrize("stage,candidates", [(1, []), (4, [1]), (0, [1])])
def test_invalid_selection_input_is_rejected(stage: int, candidates: list[int]) -> None:
    table = table_with(
        {"1": [result(item_id=1, item_type="Item", probability=1)]}
    )

    with pytest.raises(SelectionError):
        GiftPrioritySelector(table).select_best_node(stage, candidates)


def test_unknown_node_is_rejected() -> None:
    table = table_with(
        {"1": [result(item_id=1, item_type="Item", probability=1)]}
    )

    with pytest.raises(SelectionError, match="Node 99"):
        GiftPrioritySelector(table).select_best_node(1, [99])


def test_unknown_gift_grade_is_rejected() -> None:
    with pytest.raises(CraftingTableError, match="gift grade"):
        table_with(
            {
                "1": [
                    result(
                        item_id=1,
                        item_type="Gift",
                        gift_grade="Legendary",
                        probability=1,
                    )
                ]
            }
        )
