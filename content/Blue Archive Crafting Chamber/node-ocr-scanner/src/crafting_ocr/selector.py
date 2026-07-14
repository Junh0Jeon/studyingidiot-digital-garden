from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


NORMAL_GIFT_WEIGHT = 1.0
ADVANCED_GIFT_WEIGHT = 3.0
SCORE_EPSILON = 1e-7


class CraftingTableError(ValueError):
    """Raised when crafting data cannot be used safely."""


class SelectionError(ValueError):
    """Raised when candidate nodes cannot be evaluated safely."""


@dataclass(frozen=True)
class CraftingResult:
    item_id: int
    item_type: str
    gift_grade: str | None
    probability: float
    min_quantity: int
    max_quantity: int

    @property
    def expected_quantity(self) -> float:
        return (self.min_quantity + self.max_quantity) / 2.0


@dataclass(frozen=True)
class NodeEvaluation:
    node_id: int
    gift_score: float
    furniture_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeId": self.node_id,
            "giftScore": self.gift_score,
            "furnitureScore": self.furniture_score,
        }


@dataclass(frozen=True)
class NodeDecision:
    recommended_node_id: int
    gift_score: float
    furniture_score: float
    tied_node_ids: tuple[int, ...]
    selection_reason: str
    evaluations: tuple[NodeEvaluation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendedNodeId": self.recommended_node_id,
            "giftScore": self.gift_score,
            "furnitureScore": self.furniture_score,
            "tiedNodeIds": list(self.tied_node_ids),
            "selectionReason": self.selection_reason,
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
        }


class CraftingTable:
    """Validated, read-only crafting results indexed by stage and node ID."""

    def __init__(self, stages: Mapping[int, Mapping[int, tuple[CraftingResult, ...]]]):
        if not stages:
            raise CraftingTableError("Crafting table must contain at least one stage")
        frozen_stages: dict[int, Mapping[int, tuple[CraftingResult, ...]]] = {}
        for stage, nodes in stages.items():
            if stage <= 0 or not nodes:
                raise CraftingTableError(f"Invalid or empty crafting stage: {stage}")
            frozen_stages[stage] = MappingProxyType(dict(nodes))
        self._stages = MappingProxyType(frozen_stages)

    @classmethod
    def from_json(cls, path: Path) -> "CraftingTable":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CraftingTableError(f"Cannot read crafting table {path}: {error}") from error
        if not isinstance(payload, dict):
            raise CraftingTableError("Crafting table root must be an object")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("schemaVersion") != 1:
            raise CraftingTableError("Only crafting table schemaVersion 1 is supported")
        return cls.from_mapping(payload.get("craftingTable"))

    @classmethod
    def from_mapping(cls, raw_table: Any) -> "CraftingTable":
        if not isinstance(raw_table, dict):
            raise CraftingTableError("craftingTable must be an object")
        stages: dict[int, dict[int, tuple[CraftingResult, ...]]] = {}
        for raw_stage, raw_nodes in raw_table.items():
            try:
                stage = int(raw_stage)
            except (TypeError, ValueError) as error:
                raise CraftingTableError(f"Invalid stage key: {raw_stage!r}") from error
            if not isinstance(raw_nodes, dict):
                raise CraftingTableError(f"Stage {stage} must be an object")
            nodes: dict[int, tuple[CraftingResult, ...]] = {}
            for raw_node_id, raw_results in raw_nodes.items():
                try:
                    node_id = int(raw_node_id)
                except (TypeError, ValueError) as error:
                    raise CraftingTableError(
                        f"Invalid node ID at stage {stage}: {raw_node_id!r}"
                    ) from error
                if not isinstance(raw_results, list) or not raw_results:
                    raise CraftingTableError(
                        f"Stage {stage} node {node_id} must have result entries"
                    )
                nodes[node_id] = tuple(
                    cls._parse_result(stage, node_id, index, raw_result)
                    for index, raw_result in enumerate(raw_results)
                )
            stages[stage] = nodes
        return cls(stages)

    @staticmethod
    def _parse_result(
        stage: int, node_id: int, index: int, raw_result: Any
    ) -> CraftingResult:
        label = f"stage {stage} node {node_id} result {index}"
        if not isinstance(raw_result, dict):
            raise CraftingTableError(f"{label} must be an object")
        required = (
            "itemId",
            "itemType",
            "giftGrade",
            "probability",
            "minQuantity",
            "maxQuantity",
        )
        missing = [field for field in required if field not in raw_result]
        if missing:
            raise CraftingTableError(f"{label} is missing: {', '.join(missing)}")
        try:
            result = CraftingResult(
                item_id=int(raw_result["itemId"]),
                item_type=str(raw_result["itemType"]),
                gift_grade=(
                    None
                    if raw_result["giftGrade"] is None
                    else str(raw_result["giftGrade"])
                ),
                probability=float(raw_result["probability"]),
                min_quantity=int(raw_result["minQuantity"]),
                max_quantity=int(raw_result["maxQuantity"]),
            )
        except (TypeError, ValueError) as error:
            raise CraftingTableError(f"{label} contains an invalid value") from error
        if not math.isfinite(result.probability) or not 0 <= result.probability <= 1:
            raise CraftingTableError(f"{label} has an invalid probability")
        if result.min_quantity < 0 or result.min_quantity > result.max_quantity:
            raise CraftingTableError(f"{label} has an invalid quantity range")
        if result.item_type == "Gift":
            if result.gift_grade not in {"Normal", "Advanced"}:
                raise CraftingTableError(f"{label} has an unsupported gift grade")
        elif result.gift_grade is not None:
            raise CraftingTableError(f"{label} has a gift grade on a non-gift result")
        return result

    def has_stage(self, stage: int) -> bool:
        return stage in self._stages

    def results_for(self, stage: int, node_id: int) -> tuple[CraftingResult, ...]:
        nodes = self._stages.get(stage)
        if nodes is None:
            raise SelectionError(f"Crafting stage {stage} does not exist")
        results = nodes.get(node_id)
        if results is None:
            raise SelectionError(f"Node {node_id} does not exist at stage {stage}")
        return results


class GiftPrioritySelector:
    def __init__(
        self,
        crafting_table: CraftingTable,
        random_choice: Callable[[Sequence[int]], int] = random.choice,
    ) -> None:
        self._crafting_table = crafting_table
        self._random_choice = random_choice

    def select_best_node(
        self, stage: int, candidate_node_ids: Sequence[int]
    ) -> NodeDecision:
        if not isinstance(stage, int) or isinstance(stage, bool) or stage <= 0:
            raise SelectionError(f"Invalid crafting stage: {stage!r}")
        if not self._crafting_table.has_stage(stage):
            raise SelectionError(f"Crafting stage {stage} does not exist")
        if not candidate_node_ids:
            raise SelectionError("Candidate node list must not be empty")

        evaluations: list[NodeEvaluation] = []
        for node_id in candidate_node_ids:
            if not isinstance(node_id, int) or isinstance(node_id, bool):
                raise SelectionError(f"Invalid candidate node ID: {node_id!r}")
            evaluations.append(self._evaluate(stage, node_id))

        highest_gift_score = max(evaluation.gift_score for evaluation in evaluations)
        gift_candidates = [
            evaluation
            for evaluation in evaluations
            if self._same_score(evaluation.gift_score, highest_gift_score)
        ]
        if len(gift_candidates) == 1:
            selected = gift_candidates[0]
            reason = "highest-gift-score"
            final_candidates = gift_candidates
        else:
            highest_furniture_score = max(
                evaluation.furniture_score for evaluation in gift_candidates
            )
            final_candidates = [
                evaluation
                for evaluation in gift_candidates
                if self._same_score(
                    evaluation.furniture_score, highest_furniture_score
                )
            ]
            if len(final_candidates) == 1:
                selected = final_candidates[0]
                reason = "highest-furniture-score"
            else:
                choices = tuple(evaluation.node_id for evaluation in final_candidates)
                selected_node_id = self._random_choice(choices)
                if selected_node_id not in choices:
                    raise SelectionError(
                        "Injected random choice returned a node outside the tie candidates"
                    )
                selected = next(
                    evaluation
                    for evaluation in final_candidates
                    if evaluation.node_id == selected_node_id
                )
                reason = "random-tiebreak"

        tied_node_ids = tuple(
            dict.fromkeys(evaluation.node_id for evaluation in final_candidates)
        )
        return NodeDecision(
            recommended_node_id=selected.node_id,
            gift_score=selected.gift_score,
            furniture_score=selected.furniture_score,
            tied_node_ids=tied_node_ids,
            selection_reason=reason,
            evaluations=tuple(evaluations),
        )

    def _evaluate(self, stage: int, node_id: int) -> NodeEvaluation:
        gift_score = 0.0
        furniture_score = 0.0
        for result in self._crafting_table.results_for(stage, node_id):
            if result.item_type == "Gift":
                weight = (
                    ADVANCED_GIFT_WEIGHT
                    if result.gift_grade == "Advanced"
                    else NORMAL_GIFT_WEIGHT
                )
                gift_score += result.probability * result.expected_quantity * weight
            elif result.item_type == "Furniture":
                furniture_score += result.probability * result.expected_quantity
        return NodeEvaluation(node_id, gift_score, furniture_score)

    @staticmethod
    def _same_score(left: float, right: float) -> bool:
        return math.isclose(left, right, rel_tol=0.0, abs_tol=SCORE_EPSILON)
