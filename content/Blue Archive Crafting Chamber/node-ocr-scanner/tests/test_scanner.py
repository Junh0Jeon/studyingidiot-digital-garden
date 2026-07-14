from pathlib import Path

import numpy as np
import pytest

from crafting_ocr.manifest import NodeManifestIndex
from crafting_ocr.models import ClickPoint, OcrReading, Rectangle, ScreenProfile
from crafting_ocr.scanner import (
    CandidateNodeScanner,
    ScanAbortedError,
    ScreenProfileMismatch,
    find_first_candidate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED = PROJECT_ROOT / "crafting-data-builder" / "generated"


class FakeCapture:
    def __init__(self, width: int = 20, height: int = 20) -> None:
        self._size = (width, height)
        self._image = np.zeros((height, width, 3), dtype=np.uint8)

    def size(self) -> tuple[int, int]:
        return self._size

    def capture(self) -> np.ndarray:
        return self._image.copy()


class FakeInput:
    def __init__(self) -> None:
        self.clicked: list[ClickPoint] = []

    def click(self, point: ClickPoint) -> None:
        self.clicked.append(point)


class QueuedOcr:
    def __init__(self, texts: list[tuple[str, float]]) -> None:
        self._texts = iter(texts)

    def recognize(self, image: np.ndarray) -> list[OcrReading]:
        text, confidence = next(self._texts)
        return [OcrReading(text, confidence, "fake")]


def make_profile() -> ScreenProfile:
    points = tuple(ClickPoint(index + 1, index + 1) for index in range(5))
    return ScreenProfile(
        width=20,
        height=20,
        stage_click_points={1: points, 2: points, 3: points},
        node_name_region=Rectangle(0, 0, 10, 5),
        ocr_confidence_threshold=0.8,
        initial_settle_seconds=0,
        stability_poll_seconds=0,
        stability_timeout_seconds=0.1,
        stability_mean_difference_threshold=0,
    )


def make_manifest() -> NodeManifestIndex:
    return NodeManifestIndex.from_files(
        GENERATED / "node_manifest.json",
        GENERATED / "crafting_table.json",
    )


def test_scan_preserves_slot_order_and_node_ids() -> None:
    input_controller = FakeInput()
    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=input_controller,
        ocr_engine=QueuedOcr(
            [("은은함", 0.99), ("영롱함", 0.98), ("반짝임", 0.97), ("금속", 0.96), ("꽃", 0.95)]
        ),
    )

    batch = scanner.scan_candidate_nodes(1)

    assert batch.candidate_node_ids == (1, 2, 3, 5, 10)
    assert [candidate.slot_index for candidate in batch.candidates] == list(range(5))
    assert input_controller.clicked == list(make_profile().stage_click_points[1])
    target = find_first_candidate(batch, 3)
    assert target.slot_index == 2
    assert target.click_point == ClickPoint(3, 3)


def test_scan_aborts_on_ocr_typo_without_fuzzy_acceptance(tmp_path: Path) -> None:
    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=QueuedOcr([("반짝밈", 0.99)]),
        diagnostics_root=tmp_path,
    )

    with pytest.raises(ScanAbortedError) as raised:
        scanner.scan_candidate_nodes(1)

    failure = raised.value.failure
    assert failure.slot_index == 0
    assert failure.nearest_candidates[0]["nameKr"] == "반짝임"
    assert failure.diagnostic_directory is not None
    assert (failure.diagnostic_directory / "report.json").exists()


def test_scan_aborts_on_low_confidence() -> None:
    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=QueuedOcr([("꽃", 0.79)]),
    )

    with pytest.raises(ScanAbortedError):
        scanner.scan_candidate_nodes(1)


def test_relaxed_exact_accepts_single_three_character_match() -> None:
    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=QueuedOcr([("찬란함", 0.2438)] * 5),
    )

    batch = scanner.scan_candidate_nodes(3)

    assert batch.candidate_node_ids == (3001, 3001, 3001, 3001, 3001)
    assert all(
        node.recognition_method == "relaxed-exact" for node in batch.candidates
    )


def test_scan_aborts_when_preprocessing_variants_disagree() -> None:
    class AmbiguousOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("은은함", 0.95, "gray"),
                OcrReading("반짝임", 0.94, "otsu"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=AmbiguousOcr(),
    )

    with pytest.raises(ScanAbortedError) as raised:
        scanner.scan_candidate_nodes(1)

    assert "multiple node IDs" in raised.value.failure.reason


def test_scan_accepts_safe_fuzzy_consensus() -> None:
    class FuzzyConsensusOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("영령합", 0.28, "gray"),
                OcrReading("영령합", 0.31, "clahe"),
                OcrReading("영통함", 0.25, "otsu"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=FuzzyConsensusOcr(),
    )

    batch = scanner.scan_candidate_nodes(1)

    assert batch.candidate_node_ids == (2, 2, 2, 2, 2)
    assert all(
        node.recognition_method == "known-ocr-alias" for node in batch.candidates
    )


def test_low_confidence_exact_consensus_accepts_short_manifest_name() -> None:
    class ShortExactConsensusOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("목련", 0.32, "gray"),
                OcrReading("목련", 0.25, "clahe"),
                OcrReading("목련", 0.36, "otsu"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=ShortExactConsensusOcr(),
    )

    batch = scanner.scan_candidate_nodes(2)

    assert batch.candidate_node_ids == (115, 115, 115, 115, 115)
    assert all(
        node.recognition_method == "exact-consensus" for node in batch.candidates
    )


def test_known_ocr_alias_accepts_young_wildcard_ham_or_hap() -> None:
    class YoungRongAliasOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("영령합", 0.26, "gray"),
                OcrReading("영통함", 0.30, "otsu"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=YoungRongAliasOcr(),
    )

    batch = scanner.scan_candidate_nodes(1)

    assert batch.candidate_node_ids == (2, 2, 2, 2, 2)
    assert all(node.recognized_text == "영통함" for node in batch.candidates)
    assert all(
        node.recognition_method == "known-ocr-alias" for node in batch.candidates
    )


def test_fuzzy_consensus_never_accepts_short_names() -> None:
    class ShortNameOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("급", 0.4, "gray"),
                OcrReading("급", 0.4, "clahe"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=ShortNameOcr(),
    )

    with pytest.raises(ScanAbortedError):
        scanner.scan_candidate_nodes(1)


def test_long_name_accepts_distance_three_with_consensus() -> None:
    class LongNameOcr:
        def recognize(self, image: np.ndarray) -> list[OcrReading]:
            return [
                OcrReading("할로원 편권 카페 세트", 0.58, "gray"),
                OcrReading("할로원 편권 카페 세트", 0.57, "clahe"),
                OcrReading("할로원 평권 카페 세트", 0.44, "otsu"),
            ]

    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(),
        input_controller=FakeInput(),
        ocr_engine=LongNameOcr(),
    )

    batch = scanner.scan_candidate_nodes(2)

    assert batch.candidate_node_ids == (134, 134, 134, 134, 134)
    assert all(
        node.recognition_method == "fuzzy-consensus" for node in batch.candidates
    )


def test_scan_rejects_wrong_screen_size() -> None:
    scanner = CandidateNodeScanner(
        profile=make_profile(),
        manifest=make_manifest(),
        screen_capture=FakeCapture(width=21),
        input_controller=FakeInput(),
        ocr_engine=QueuedOcr([]),
    )

    with pytest.raises(ScreenProfileMismatch):
        scanner.scan_candidate_nodes(1)
