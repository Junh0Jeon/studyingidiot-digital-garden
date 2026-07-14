from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from crafting_ocr.adapters import PyAutoGuiInputController
from crafting_ocr.automation import (
    AutomationAbortedError,
    AutomationProfile,
    AutomationProfileError,
    AutomationWaits,
    CraftingAutomationRunner,
)
from crafting_ocr.models import (
    CandidateNode,
    CandidateNodeBatch,
    ClickPoint,
    Rectangle,
    ScreenProfile,
)
from crafting_ocr.selector import NodeDecision, NodeEvaluation


def make_screen() -> ScreenProfile:
    node_points = tuple(ClickPoint(index + 10, 10) for index in range(5))
    return ScreenProfile(
        width=200,
        height=200,
        stage_click_points={1: node_points, 2: node_points, 3: node_points},
        node_name_region=Rectangle(20, 20, 20, 10),
    )


def make_waits() -> AutomationWaits:
    return AutomationWaits(*([0.0] * 9), 4.0, *([0.0] * 11))


def make_profile() -> AutomationProfile:
    point = ClickPoint(50, 50)
    return AutomationProfile(
        screen=make_screen(),
        crafting_start_points=(ClickPoint(1, 1), ClickPoint(2, 2), ClickPoint(3, 3)),
        primary_material_point=ClickPoint(4, 4),
        primary_unlock_point=ClickPoint(5, 5),
        candidate_ready_points={
            1: ClickPoint(6, 6),
            2: ClickPoint(16, 6),
            3: ClickPoint(17, 6),
        },
        node_confirm_points={1: ClickPoint(7, 7), 2: ClickPoint(8, 8), 3: ClickPoint(9, 9)},
        add_material_point=ClickPoint(10, 10),
        additional_material_point=ClickPoint(11, 11),
        unlock_points={2: ClickPoint(12, 12), 3: ClickPoint(13, 13)},
        begin_crafting_point=ClickPoint(14, 14),
        confirm_crafting_point=ClickPoint(15, 15),
        crafting_animation_skip_point=ClickPoint(19, 19),
        collect_all_point=ClickPoint(16, 16),
        collect_confirm_point=ClickPoint(17, 17),
        result_collect_all_point=ClickPoint(18, 18),
        result_dismiss_point=point,
        waits=make_waits(),
    )


class FakeInput:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events

    def click(self, point: ClickPoint) -> None:
        self.events.append(("click", point))

    def hold(self, point: ClickPoint, duration_seconds: float) -> None:
        self.events.append(("hold", point, duration_seconds))


class FakeScanner:
    def __init__(self, events: list[tuple], fail_stage: int | None = None) -> None:
        self.events = events
        self.fail_stage = fail_stage

    def scan_candidate_nodes(self, stage: int) -> CandidateNodeBatch:
        self.events.append(("scan", stage))
        if stage == self.fail_stage:
            raise RuntimeError(f"scan failed at stage {stage}")
        candidate = CandidateNode(
            slot_index=0,
            node_id=stage,
            click_point=ClickPoint(100 + stage, 100 + stage),
            recognized_text=str(stage),
            normalized_text=str(stage),
            ocr_confidence=1.0,
            recognition_method="exact",
        )
        return CandidateNodeBatch(stage, (candidate,))


class FakeSelector:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events

    def select_best_node(self, stage: int, candidate_node_ids: tuple[int, ...]) -> NodeDecision:
        self.events.append(("select", stage, candidate_node_ids))
        evaluation = NodeEvaluation(stage, float(stage), 0.0)
        return NodeDecision(stage, float(stage), 0.0, (stage,), "test", (evaluation,))


def make_runner(events: list[tuple], fail_stage: int | None = None) -> CraftingAutomationRunner:
    return CraftingAutomationRunner(
        profile=make_profile(),
        scanner=FakeScanner(events, fail_stage),
        selector=FakeSelector(events),
        input_controller=FakeInput(events),
        sleep=lambda seconds: events.append(("sleep", seconds)),
    )


def test_single_craft_runs_three_stages_in_order() -> None:
    events: list[tuple] = []
    result = make_runner(events).run_single(0, execute=True)

    assert [event[1] for event in events if event[0] == "scan"] == [1, 2, 3]
    assert [event[1] for event in events if event[0] == "select"] == [1, 2, 3]
    assert [event for event in events if event[0] == "hold"] == [
        ("hold", ClickPoint(11, 11), 4.0),
        ("hold", ClickPoint(11, 11), 4.0),
    ]
    assert result.completed_state == "slot-1:completed"
    assert len(result.crafts[0].stages) == 3


def test_recommended_node_is_clicked_before_stage_confirmation() -> None:
    events: list[tuple] = []
    make_runner(events).run_single(0, execute=True)

    recommended_clicks = [
        index
        for index, event in enumerate(events)
        if event == ("click", ClickPoint(101, 101))
    ]
    confirm = events.index(("click", ClickPoint(7, 7)))
    assert len(recommended_clicks) == 2
    assert recommended_clicks[0] < confirm < recommended_clicks[1]


def test_candidate_ready_point_is_clicked_before_every_stage_scan() -> None:
    events: list[tuple] = []
    make_runner(events).run_single(0, execute=True)

    ready_points = {
        1: ClickPoint(6, 6),
        2: ClickPoint(16, 6),
        3: ClickPoint(17, 6),
    }
    for stage, ready_point in ready_points.items():
        assert events.index(("click", ready_point)) < events.index(("scan", stage))


def test_crafting_animation_is_skipped_after_confirmation() -> None:
    events: list[tuple] = []
    make_runner(events).run_single(0, execute=True)

    confirm = events.index(("click", ClickPoint(15, 15)))
    skip = events.index(("click", ClickPoint(19, 19)))
    assert confirm < skip


def test_run_all_completes_three_crafts_and_collection() -> None:
    events: list[tuple] = []
    result = make_runner(events).run_all(execute=True)

    assert [event[1] for event in events if event[0] == "scan"] == [1, 2, 3] * 3
    assert len(result.crafts) == 3
    assert result.collected is True
    assert result.completed_state == "collection-completed"
    assert ("click", ClickPoint(16, 16)) in events
    assert events[-1] == ("click", ClickPoint(50, 50))


def test_dry_run_never_calls_dependencies() -> None:
    events: list[tuple] = []
    result = make_runner(events).run_all(execute=False)

    assert events == []
    assert result.executed is False
    assert result.completed_state == "dry-run"
    assert "collect-all" in result.action_log


def test_failure_stops_before_later_stage_and_wraps_state() -> None:
    events: list[tuple] = []

    with pytest.raises(AutomationAbortedError) as raised:
        make_runner(events, fail_stage=2).run_all(execute=True)

    assert ("scan", 3) not in events
    assert ("click", ClickPoint(14, 14)) not in events
    assert "stage-2:scanning" in raised.value.completed_state


def test_profile_rejects_placeholder_coordinates() -> None:
    raw = {
        "craftingStartPoints": [{"x": 0, "y": 0}] * 3,
    }
    with pytest.raises(AutomationProfileError, match="placeholder"):
        AutomationProfile.from_mapping(make_screen(), raw)


def test_hold_releases_mouse_when_wait_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []
    fake_pyautogui = SimpleNamespace(
        PAUSE=0.0,
        FAILSAFE=False,
        moveTo=lambda x, y: calls.append(("move", x, y)),
        mouseDown=lambda: calls.append(("down",)),
        mouseUp=lambda: calls.append(("up",)),
        click=lambda x, y: calls.append(("click", x, y)),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    def fail_sleep(seconds: float) -> None:
        raise RuntimeError("interrupted")

    controller = PyAutoGuiInputController(sleep=fail_sleep)
    with pytest.raises(RuntimeError, match="interrupted"):
        controller.hold(ClickPoint(20, 30), 4.0)

    assert calls == [("move", 20, 30), ("down",), ("up",)]
