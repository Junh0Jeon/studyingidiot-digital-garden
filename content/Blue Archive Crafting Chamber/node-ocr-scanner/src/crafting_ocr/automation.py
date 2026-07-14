from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .models import (
    CandidateNodeBatch,
    ClickPoint,
    NodeDecisionTarget,
    ScreenProfile,
)
from .scanner import find_first_candidate
from .selector import NodeDecision


class AutomationProfileError(ValueError):
    pass


class AutomationAbortedError(RuntimeError):
    def __init__(
        self,
        completed_state: str,
        action_log: Sequence[str],
        cause: Exception,
    ) -> None:
        super().__init__(f"Automation aborted after {completed_state}: {cause}")
        self.completed_state = completed_state
        self.action_log = tuple(action_log)
        self.cause = cause


@dataclass(frozen=True)
class AutomationWaits:
    startup_seconds: float
    after_crafting_slot_seconds: float
    after_primary_material_seconds: float
    after_primary_unlock_seconds: float
    after_candidate_ready_seconds: float
    after_recommended_node_seconds: float
    after_node_confirm_before_repeat_seconds: float
    after_node_confirm_seconds: float
    after_add_material_seconds: float
    material_hold_seconds: float
    after_material_hold_seconds: float
    after_node_unlock_seconds: float
    after_crafting_start_seconds: float
    after_crafting_confirm_before_skip_seconds: float
    after_crafting_confirm_seconds: float
    between_crafts_seconds: float
    after_collect_all_seconds: float
    after_collect_confirm_seconds: float
    after_result_collect_all_seconds: float
    result_display_seconds: float
    after_result_dismiss_seconds: float

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if value < 0:
                raise AutomationProfileError(f"Wait {name} must not be negative")
        if self.material_hold_seconds <= 0:
            raise AutomationProfileError("materialHoldSeconds must be positive")


@dataclass(frozen=True)
class AutomationProfile:
    screen: ScreenProfile
    crafting_start_points: tuple[ClickPoint, ...]
    primary_material_point: ClickPoint
    primary_unlock_point: ClickPoint
    candidate_ready_points: dict[int, ClickPoint]
    node_confirm_points: dict[int, ClickPoint]
    add_material_point: ClickPoint
    additional_material_point: ClickPoint
    unlock_points: dict[int, ClickPoint]
    begin_crafting_point: ClickPoint
    confirm_crafting_point: ClickPoint
    crafting_animation_skip_point: ClickPoint
    collect_all_point: ClickPoint
    collect_confirm_point: ClickPoint
    result_collect_all_point: ClickPoint
    result_dismiss_point: ClickPoint
    waits: AutomationWaits

    @classmethod
    def from_json(cls, path: Path) -> "AutomationProfile":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AutomationProfileError(f"Cannot read automation profile: {error}") from error
        if not isinstance(payload, dict):
            raise AutomationProfileError("Automation profile root must be an object")
        screen = ScreenProfile.from_json(path)
        return cls.from_mapping(screen, payload.get("automation"))

    @classmethod
    def from_mapping(cls, screen: ScreenProfile, raw: Any) -> "AutomationProfile":
        if not isinstance(raw, dict):
            raise AutomationProfileError("Profile has no automation object")

        def point(name: str) -> ClickPoint:
            value = raw.get(name)
            if not isinstance(value, dict):
                raise AutomationProfileError(f"automation.{name} must be an object")
            try:
                result = ClickPoint(int(value["x"]), int(value["y"]))
            except (KeyError, TypeError, ValueError) as error:
                raise AutomationProfileError(f"automation.{name} is invalid") from error
            cls._validate_point(screen, result, name)
            return result

        def point_map(name: str, required_stages: tuple[int, ...]) -> dict[int, ClickPoint]:
            value = raw.get(name)
            if not isinstance(value, dict):
                raise AutomationProfileError(f"automation.{name} must be an object")
            result: dict[int, ClickPoint] = {}
            for stage in required_stages:
                stage_value = value.get(str(stage))
                if not isinstance(stage_value, dict):
                    raise AutomationProfileError(
                        f"automation.{name}.{stage} must be an object"
                    )
                try:
                    stage_point = ClickPoint(
                        int(stage_value["x"]), int(stage_value["y"])
                    )
                except (KeyError, TypeError, ValueError) as error:
                    raise AutomationProfileError(
                        f"automation.{name}.{stage} is invalid"
                    ) from error
                cls._validate_point(screen, stage_point, f"{name}.{stage}")
                result[stage] = stage_point
            return result

        raw_starts = raw.get("craftingStartPoints")
        if not isinstance(raw_starts, list) or len(raw_starts) != 3:
            raise AutomationProfileError(
                "automation.craftingStartPoints must contain exactly three points"
            )
        starts: list[ClickPoint] = []
        for index, value in enumerate(raw_starts):
            if not isinstance(value, dict):
                raise AutomationProfileError(
                    f"automation.craftingStartPoints[{index}] must be an object"
                )
            try:
                start = ClickPoint(int(value["x"]), int(value["y"]))
            except (KeyError, TypeError, ValueError) as error:
                raise AutomationProfileError(
                    f"automation.craftingStartPoints[{index}] is invalid"
                ) from error
            cls._validate_point(screen, start, f"craftingStartPoints[{index}]")
            starts.append(start)

        waits = cls._parse_waits(raw.get("waits"))
        profile = cls(
            screen=screen,
            crafting_start_points=tuple(starts),
            primary_material_point=point("primaryMaterialPoint"),
            primary_unlock_point=point("primaryUnlockPoint"),
            candidate_ready_points=point_map("candidateReadyPoints", (1, 2, 3)),
            node_confirm_points=point_map("nodeConfirmPoints", (1, 2, 3)),
            add_material_point=point("addMaterialPoint"),
            additional_material_point=point("additionalMaterialPoint"),
            unlock_points=point_map("unlockPoints", (2, 3)),
            begin_crafting_point=point("beginCraftingPoint"),
            confirm_crafting_point=point("confirmCraftingPoint"),
            crafting_animation_skip_point=point("craftingAnimationSkipPoint"),
            collect_all_point=point("collectAllPoint"),
            collect_confirm_point=point("collectConfirmPoint"),
            result_collect_all_point=point("resultCollectAllPoint"),
            result_dismiss_point=point("resultDismissPoint"),
            waits=waits,
        )
        return profile

    @staticmethod
    def _validate_point(screen: ScreenProfile, point: ClickPoint, name: str) -> None:
        if not (0 <= point.x < screen.width and 0 <= point.y < screen.height):
            raise AutomationProfileError(f"automation.{name} is outside the screen")
        if point.x == 0 and point.y == 0:
            raise AutomationProfileError(
                f"automation.{name} is still the (0, 0) placeholder"
            )

    @staticmethod
    def _parse_waits(raw: Any) -> AutomationWaits:
        if not isinstance(raw, dict):
            raise AutomationProfileError("automation.waits must be an object")

        def number(name: str, default: float) -> float:
            try:
                return float(raw.get(name, default))
            except (TypeError, ValueError) as error:
                raise AutomationProfileError(f"automation.waits.{name} is invalid") from error

        waits = AutomationWaits(
            startup_seconds=number("startupSeconds", 5.0),
            after_crafting_slot_seconds=number("afterCraftingSlotSeconds", 1.0),
            after_primary_material_seconds=number("afterPrimaryMaterialSeconds", 0.3),
            after_primary_unlock_seconds=number("afterPrimaryUnlockSeconds", 1.0),
            after_candidate_ready_seconds=number("afterCandidateReadySeconds", 0.5),
            after_recommended_node_seconds=number("afterRecommendedNodeSeconds", 0.2),
            after_node_confirm_before_repeat_seconds=number(
                "afterNodeConfirmBeforeRepeatSeconds", 0.5
            ),
            after_node_confirm_seconds=number("afterNodeConfirmSeconds", 1.0),
            after_add_material_seconds=number("afterAddMaterialSeconds", 0.5),
            material_hold_seconds=number("materialHoldSeconds", 4.0),
            after_material_hold_seconds=number("afterMaterialHoldSeconds", 0.3),
            after_node_unlock_seconds=number("afterNodeUnlockSeconds", 1.0),
            after_crafting_start_seconds=number("afterCraftingStartSeconds", 1.0),
            after_crafting_confirm_before_skip_seconds=number(
                "afterCraftingConfirmBeforeSkipSeconds", 0.5
            ),
            after_crafting_confirm_seconds=number("afterCraftingConfirmSeconds", 2.0),
            between_crafts_seconds=number("betweenCraftsSeconds", 1.0),
            after_collect_all_seconds=number("afterCollectAllSeconds", 1.0),
            after_collect_confirm_seconds=number("afterCollectConfirmSeconds", 1.0),
            after_result_collect_all_seconds=number("afterResultCollectAllSeconds", 0.0),
            result_display_seconds=number("resultDisplaySeconds", 2.0),
            after_result_dismiss_seconds=number("afterResultDismissSeconds", 1.0),
        )
        waits.validate()
        return waits


@dataclass(frozen=True)
class StageSelectionResult:
    stage: int
    batch: CandidateNodeBatch
    decision: NodeDecision
    target: NodeDecisionTarget

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "candidates": self.batch.to_dict(),
            "decision": self.decision.to_dict(),
            "target": {
                "nodeId": self.target.node_id,
                "slotIndex": self.target.slot_index,
                "clickPoint": {
                    "x": self.target.click_point.x,
                    "y": self.target.click_point.y,
                },
            },
        }


@dataclass(frozen=True)
class CraftExecutionResult:
    slot_index: int
    stages: tuple[StageSelectionResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "craftSlot": self.slot_index + 1,
            "slotIndex": self.slot_index,
            "stages": [stage.to_dict() for stage in self.stages],
        }


@dataclass(frozen=True)
class AutomationResult:
    executed: bool
    scope: str
    completed_state: str
    crafts: tuple[CraftExecutionResult, ...]
    collected: bool
    action_log: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": True,
            "executed": self.executed,
            "scope": self.scope,
            "completedState": self.completed_state,
            "collected": self.collected,
            "crafts": [craft.to_dict() for craft in self.crafts],
            "actionLog": list(self.action_log),
        }


class Scanner(Protocol):
    def scan_candidate_nodes(self, stage: int) -> CandidateNodeBatch: ...


class Selector(Protocol):
    def select_best_node(
        self, stage: int, candidate_node_ids: Sequence[int]
    ) -> NodeDecision: ...


class AutomationInput(Protocol):
    def click(self, point: ClickPoint) -> None: ...
    def hold(self, point: ClickPoint, duration_seconds: float) -> None: ...


def build_action_plan(slots: Sequence[int], collect: bool) -> tuple[str, ...]:
    actions: list[str] = []
    for slot_index in slots:
        actions.extend(
            [
                f"slot-{slot_index + 1}:open",
                f"slot-{slot_index + 1}:primary-material",
                f"slot-{slot_index + 1}:primary-unlock",
                f"slot-{slot_index + 1}:candidate-ready",
                f"slot-{slot_index + 1}:stage-1:scan-select-confirm",
                f"slot-{slot_index + 1}:stage-2:material-unlock-candidate-ready-scan-select-confirm",
                f"slot-{slot_index + 1}:stage-3:material-unlock-candidate-ready-scan-select-confirm",
                f"slot-{slot_index + 1}:start-confirm",
            ]
        )
    if collect:
        actions.extend(
            ["collect-all", "collect-confirm", "result-collect-all", "result-dismiss"]
        )
    return tuple(actions)


class CraftingAutomationRunner:
    def __init__(
        self,
        profile: AutomationProfile,
        scanner: Scanner,
        selector: Selector,
        input_controller: AutomationInput,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._profile = profile
        self._scanner = scanner
        self._selector = selector
        self._input = input_controller
        self._sleep = sleep
        self._state = "initialized"
        self._actions: list[str] = []

    def run_single(self, slot_index: int, execute: bool = False) -> AutomationResult:
        self._validate_slot(slot_index)
        if not execute:
            return AutomationResult(
                executed=False,
                scope=f"slot-{slot_index + 1}",
                completed_state="dry-run",
                crafts=(),
                collected=False,
                action_log=build_action_plan((slot_index,), False),
            )
        self._reset()
        try:
            self._wait("startup", self._profile.waits.startup_seconds)
            craft = self._execute_single(slot_index)
            return AutomationResult(
                executed=True,
                scope=f"slot-{slot_index + 1}",
                completed_state=self._state,
                crafts=(craft,),
                collected=False,
                action_log=tuple(self._actions),
            )
        except Exception as error:
            if isinstance(error, AutomationAbortedError):
                raise
            raise AutomationAbortedError(self._state, self._actions, error) from error

    def run_all(self, execute: bool = False) -> AutomationResult:
        if not execute:
            return AutomationResult(
                executed=False,
                scope="all",
                completed_state="dry-run",
                crafts=(),
                collected=False,
                action_log=build_action_plan((0, 1, 2), True),
            )
        self._reset()
        crafts: list[CraftExecutionResult] = []
        try:
            self._wait("startup", self._profile.waits.startup_seconds)
            for slot_index in range(3):
                crafts.append(self._execute_single(slot_index))
                if slot_index < 2:
                    self._wait(
                        f"slot-{slot_index + 1}:between-crafts",
                        self._profile.waits.between_crafts_seconds,
                    )
            self._collect_all()
            return AutomationResult(
                executed=True,
                scope="all",
                completed_state=self._state,
                crafts=tuple(crafts),
                collected=True,
                action_log=tuple(self._actions),
            )
        except Exception as error:
            if isinstance(error, AutomationAbortedError):
                raise
            raise AutomationAbortedError(self._state, self._actions, error) from error

    def _execute_single(self, slot_index: int) -> CraftExecutionResult:
        self._click(
            f"slot-{slot_index + 1}:open",
            self._profile.crafting_start_points[slot_index],
            self._profile.waits.after_crafting_slot_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:primary-material",
            self._profile.primary_material_point,
            self._profile.waits.after_primary_material_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:primary-unlock",
            self._profile.primary_unlock_point,
            self._profile.waits.after_primary_unlock_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:candidate-ready",
            self._profile.candidate_ready_points[1],
            self._profile.waits.after_candidate_ready_seconds,
        )

        stages = [self._scan_select_confirm(slot_index, 1)]
        for stage in (2, 3):
            self._click(
                f"slot-{slot_index + 1}:stage-{stage}:add-material",
                self._profile.add_material_point,
                self._profile.waits.after_add_material_seconds,
            )
            self._hold(
                f"slot-{slot_index + 1}:stage-{stage}:hold-material",
                self._profile.additional_material_point,
                self._profile.waits.material_hold_seconds,
                self._profile.waits.after_material_hold_seconds,
            )
            self._click(
                f"slot-{slot_index + 1}:stage-{stage}:unlock",
                self._profile.unlock_points[stage],
                self._profile.waits.after_node_unlock_seconds,
            )
            self._click(
                f"slot-{slot_index + 1}:stage-{stage}:candidate-ready",
                self._profile.candidate_ready_points[stage],
                self._profile.waits.after_candidate_ready_seconds,
            )
            stages.append(self._scan_select_confirm(slot_index, stage))

        self._click(
            f"slot-{slot_index + 1}:begin-crafting",
            self._profile.begin_crafting_point,
            self._profile.waits.after_crafting_start_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:confirm-crafting",
            self._profile.confirm_crafting_point,
            self._profile.waits.after_crafting_confirm_before_skip_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:skip-crafting-animation",
            self._profile.crafting_animation_skip_point,
            self._profile.waits.after_crafting_confirm_seconds,
        )
        self._state = f"slot-{slot_index + 1}:completed"
        return CraftExecutionResult(slot_index, tuple(stages))

    def _scan_select_confirm(
        self, slot_index: int, stage: int
    ) -> StageSelectionResult:
        self._state = f"slot-{slot_index + 1}:stage-{stage}:scanning"
        batch = self._scanner.scan_candidate_nodes(stage)
        self._actions.append(f"slot-{slot_index + 1}:stage-{stage}:scanned")
        decision = self._selector.select_best_node(stage, batch.candidate_node_ids)
        target = find_first_candidate(batch, decision.recommended_node_id)
        self._click(
            f"slot-{slot_index + 1}:stage-{stage}:recommended-node-{target.node_id}",
            target.click_point,
            self._profile.waits.after_recommended_node_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:stage-{stage}:confirm-node",
            self._profile.node_confirm_points[stage],
            self._profile.waits.after_node_confirm_before_repeat_seconds,
        )
        self._click(
            f"slot-{slot_index + 1}:stage-{stage}:recommended-node-{target.node_id}:repeat",
            target.click_point,
            self._profile.waits.after_node_confirm_seconds,
        )
        return StageSelectionResult(stage, batch, decision, target)

    def _collect_all(self) -> None:
        self._click(
            "collect-all",
            self._profile.collect_all_point,
            self._profile.waits.after_collect_all_seconds,
        )
        self._click(
            "collect-confirm",
            self._profile.collect_confirm_point,
            self._profile.waits.after_collect_confirm_seconds,
        )
        self._click(
            "result-collect-all",
            self._profile.result_collect_all_point,
            self._profile.waits.after_result_collect_all_seconds,
        )
        self._wait("result-display", self._profile.waits.result_display_seconds)
        self._click(
            "result-dismiss",
            self._profile.result_dismiss_point,
            self._profile.waits.after_result_dismiss_seconds,
        )
        self._state = "collection-completed"

    def _click(self, name: str, point: ClickPoint, wait_seconds: float) -> None:
        self._input.click(point)
        self._actions.append(f"click:{name}@{point.x},{point.y}")
        self._state = name
        self._wait(f"after:{name}", wait_seconds)

    def _hold(
        self,
        name: str,
        point: ClickPoint,
        duration_seconds: float,
        wait_seconds: float,
    ) -> None:
        self._input.hold(point, duration_seconds)
        self._actions.append(
            f"hold:{name}@{point.x},{point.y}:{duration_seconds:.3f}s"
        )
        self._state = name
        self._wait(f"after:{name}", wait_seconds)

    def _wait(self, name: str, seconds: float) -> None:
        if seconds > 0:
            self._sleep(seconds)
        self._actions.append(f"wait:{name}:{seconds:.3f}s")

    def _reset(self) -> None:
        self._state = "initialized"
        self._actions = []

    @staticmethod
    def _validate_slot(slot_index: int) -> None:
        if slot_index not in (0, 1, 2):
            raise ValueError("slot_index must be 0, 1, or 2")
