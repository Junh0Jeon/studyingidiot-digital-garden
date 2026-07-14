from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from .manifest import NodeManifestIndex, NodeNameEntry, normalize_node_name
from .models import (
    CandidateNode,
    CandidateNodeBatch,
    ClickPoint,
    NodeDecisionTarget,
    OcrReading,
    Rectangle,
    ScreenProfile,
)


class ScreenCapture(Protocol):
    def size(self) -> tuple[int, int]: ...
    def capture(self) -> np.ndarray: ...


class InputController(Protocol):
    def click(self, point: ClickPoint) -> None: ...


class OcrEngine(Protocol):
    def recognize(self, image: np.ndarray) -> list[OcrReading]: ...


class ScanError(RuntimeError):
    pass


class ScreenProfileMismatch(ScanError):
    pass


@dataclass(frozen=True)
class RecognitionFailure:
    stage: int
    slot_index: int
    reason: str
    readings: tuple[OcrReading, ...]
    nearest_candidates: tuple[dict[str, object], ...]
    diagnostic_directory: Path | None


class ScanAbortedError(ScanError):
    def __init__(self, failure: RecognitionFailure) -> None:
        super().__init__(
            f"Candidate scan aborted at stage {failure.stage}, slot "
            f"{failure.slot_index}: {failure.reason}"
        )
        self.failure = failure


def crop(image: np.ndarray, rectangle: Rectangle) -> np.ndarray:
    return image[
        rectangle.y : rectangle.y + rectangle.height,
        rectangle.x : rectangle.x + rectangle.width,
    ].copy()


def mean_pixel_difference(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape:
        return float("inf")
    return float(np.mean(cv2.absdiff(left, right)))


def find_first_candidate(
    batch: CandidateNodeBatch, recommended_node_id: int
) -> NodeDecisionTarget:
    for candidate in batch.candidates:
        if candidate.node_id == recommended_node_id:
            return NodeDecisionTarget(
                node_id=candidate.node_id,
                click_point=candidate.click_point,
                slot_index=candidate.slot_index,
            )
    raise ValueError(f"Recommended node {recommended_node_id} is not in the batch")


class CandidateNodeScanner:
    def __init__(
        self,
        profile: ScreenProfile,
        manifest: NodeManifestIndex,
        screen_capture: ScreenCapture,
        input_controller: InputController,
        ocr_engine: OcrEngine,
        diagnostics_root: Path | None = None,
    ) -> None:
        self._profile = profile
        self._manifest = manifest
        self._screen_capture = screen_capture
        self._input_controller = input_controller
        self._ocr_engine = ocr_engine
        self._diagnostics_root = diagnostics_root

    def scan_candidate_nodes(self, stage: int) -> CandidateNodeBatch:
        if stage not in (1, 2, 3):
            raise ValueError(f"Unsupported crafting stage: {stage}")
        actual_size = self._screen_capture.size()
        expected_size = (self._profile.width, self._profile.height)
        if actual_size != expected_size:
            raise ScreenProfileMismatch(
                f"Expected screen {expected_size}, got {actual_size}"
            )

        candidates: list[CandidateNode] = []
        for slot_index, point in enumerate(self._profile.stage_click_points[stage]):
            self._input_controller.click(point)
            time.sleep(self._profile.initial_settle_seconds)
            stable_crop, full_screen = self._wait_for_stable_name_region()
            if stable_crop is None or full_screen is None:
                failure = self._make_failure(
                    stage,
                    slot_index,
                    "node name region did not stabilize",
                    (),
                    None,
                    None,
                )
                raise ScanAbortedError(failure)

            readings = tuple(self._ocr_engine.recognize(stable_crop))
            accepted = sorted(
                (
                    reading
                    for reading in readings
                    if reading.confidence >= self._profile.ocr_confidence_threshold
                    and self._manifest.resolve_exact(stage, reading.text) is not None
                ),
                key=lambda reading: reading.confidence,
                reverse=True,
            )
            recognition_method = "exact"
            if not accepted:
                entry, reading = self._resolve_exact_consensus(stage, readings)
                if entry is not None and reading is not None:
                    recognition_method = "exact-consensus"
                else:
                    entry, reading = self._resolve_relaxed_exact(stage, readings)
                    if entry is not None and reading is not None:
                        recognition_method = "relaxed-exact"
                    else:
                        entry, reading = self._resolve_known_ocr_alias(stage, readings)
                        if entry is not None and reading is not None:
                            recognition_method = "known-ocr-alias"
                        else:
                            entry, reading = self._resolve_fuzzy_consensus(stage, readings)
                if entry is None or reading is None:
                    diagnostic_reading = max(
                        readings,
                        key=lambda item: item.confidence,
                        default=OcrReading("", 0.0, "none"),
                    )
                    failure = self._make_failure(
                        stage,
                        slot_index,
                        "no exact match or safe fuzzy consensus",
                        readings,
                        full_screen,
                        stable_crop,
                        diagnostic_reading.text,
                    )
                    raise ScanAbortedError(failure)
                if recognition_method not in {
                    "exact-consensus",
                    "relaxed-exact",
                    "known-ocr-alias",
                }:
                    recognition_method = "fuzzy-consensus"
            else:
                accepted_node_ids = {
                    entry.node_id
                    for candidate_reading in accepted
                    if (
                        entry := self._manifest.resolve_exact(
                            stage, candidate_reading.text
                        )
                    )
                    is not None
                }
                if len(accepted_node_ids) > 1:
                    diagnostic_reading = accepted[0]
                    failure = self._make_failure(
                        stage,
                        slot_index,
                        "OCR preprocessing variants resolved to multiple node IDs",
                        readings,
                        full_screen,
                        stable_crop,
                        diagnostic_reading.text,
                    )
                    raise ScanAbortedError(failure)

                reading = accepted[0]
                entry = self._manifest.resolve_exact(stage, reading.text)
                assert entry is not None
            candidates.append(
                CandidateNode(
                    slot_index=slot_index,
                    node_id=entry.node_id,
                    click_point=point,
                    recognized_text=reading.text,
                    normalized_text=normalize_node_name(reading.text),
                    ocr_confidence=reading.confidence,
                    recognition_method=recognition_method,
                )
            )
        return CandidateNodeBatch(stage=stage, candidates=tuple(candidates))

    def _resolve_exact_consensus(
        self, stage: int, readings: tuple[OcrReading, ...]
    ) -> tuple[NodeNameEntry | None, OcrReading | None]:
        votes: list[tuple[NodeNameEntry, OcrReading]] = []
        for reading in readings:
            if reading.confidence < self._profile.fuzzy_minimum_confidence:
                continue
            entry = self._manifest.resolve_exact(stage, reading.text)
            if entry is not None:
                votes.append((entry, reading))

        if len(votes) < self._profile.fuzzy_minimum_consensus_count:
            return None, None
        if len({entry.node_id for entry, _ in votes}) != 1:
            return None, None

        entry, representative = max(votes, key=lambda vote: vote[1].confidence)
        return entry, representative

    def _resolve_relaxed_exact(
        self, stage: int, readings: tuple[OcrReading, ...]
    ) -> tuple[NodeNameEntry | None, OcrReading | None]:
        matches: list[tuple[NodeNameEntry, OcrReading]] = []
        for reading in readings:
            if reading.confidence < self._profile.relaxed_exact_confidence_threshold:
                continue
            entry = self._manifest.resolve_exact(stage, reading.text)
            if entry is None:
                continue
            if (
                len(entry.normalized_name_kr)
                < self._profile.relaxed_exact_minimum_name_length
            ):
                continue
            matches.append((entry, reading))

        if not matches:
            return None, None
        if len({entry.node_id for entry, _ in matches}) != 1:
            return None, None
        return max(matches, key=lambda match: match[1].confidence)

    def _resolve_known_ocr_alias(
        self, stage: int, readings: tuple[OcrReading, ...]
    ) -> tuple[NodeNameEntry | None, OcrReading | None]:
        """Resolve narrowly scoped OCR mistakes that are unsafe for generic fuzzy matching."""
        entry = self._manifest.resolve_exact(stage, "영롱함")
        if entry is None:
            return None, None

        matches = [
            reading
            for reading in readings
            if reading.confidence >= self._profile.fuzzy_minimum_confidence
            and len(normalized := normalize_node_name(reading.text)) == 3
            and normalized[0] == "영"
            and normalized[-1] in {"함", "합"}
        ]
        if not matches:
            return None, None
        return entry, max(matches, key=lambda reading: reading.confidence)

    def _resolve_fuzzy_consensus(
        self, stage: int, readings: tuple[OcrReading, ...]
    ) -> tuple[NodeNameEntry | None, OcrReading | None]:
        votes: list[tuple[int, OcrReading, dict[str, object]]] = []
        for reading in readings:
            if reading.confidence < self._profile.fuzzy_minimum_confidence:
                continue
            nearest = self._manifest.nearest(stage, reading.text, limit=2)
            if len(nearest) < 2:
                continue
            best, second = nearest
            normalized_name = str(best["normalizedNameKr"])
            name_length = len(normalized_name)
            if name_length < self._profile.fuzzy_minimum_name_length:
                continue
            maximum_distance = (
                self._profile.fuzzy_long_name_maximum_distance
                if name_length >= self._profile.fuzzy_long_name_minimum_length
                else self._profile.fuzzy_maximum_distance
            )
            if int(best["distance"]) > maximum_distance:
                continue
            if int(best["distance"]) >= int(second["distance"]):
                continue
            votes.append((int(best["nodeId"]), reading, best))

        if len(votes) < self._profile.fuzzy_minimum_consensus_count:
            return None, None
        if len({node_id for node_id, _, _ in votes}) != 1:
            return None, None

        _, representative, nearest = max(
            votes, key=lambda vote: vote[1].confidence
        )
        entry = self._manifest.resolve_exact(stage, str(nearest["nameKr"]))
        return entry, representative

    def _wait_for_stable_name_region(
        self,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        deadline = time.monotonic() + self._profile.stability_timeout_seconds
        previous_crop: np.ndarray | None = None
        while time.monotonic() <= deadline:
            full_screen = self._screen_capture.capture()
            current_crop = crop(full_screen, self._profile.node_name_region)
            if previous_crop is not None:
                difference = mean_pixel_difference(previous_crop, current_crop)
                if difference <= self._profile.stability_mean_difference_threshold:
                    return current_crop, full_screen
            previous_crop = current_crop
            time.sleep(self._profile.stability_poll_seconds)
        return None, None

    def _make_failure(
        self,
        stage: int,
        slot_index: int,
        reason: str,
        readings: tuple[OcrReading, ...],
        full_screen: np.ndarray | None,
        name_crop: np.ndarray | None,
        nearest_text: str | None,
    ) -> RecognitionFailure:
        nearest = tuple(
            self._manifest.nearest(stage, nearest_text or "") if nearest_text else ()
        )
        directory = self._write_diagnostics(
            stage, slot_index, reason, readings, nearest, full_screen, name_crop
        )
        return RecognitionFailure(
            stage=stage,
            slot_index=slot_index,
            reason=reason,
            readings=readings,
            nearest_candidates=nearest,
            diagnostic_directory=directory,
        )

    def _write_diagnostics(
        self,
        stage: int,
        slot_index: int,
        reason: str,
        readings: tuple[OcrReading, ...],
        nearest: tuple[dict[str, object], ...],
        full_screen: np.ndarray | None,
        name_crop: np.ndarray | None,
    ) -> Path | None:
        if self._diagnostics_root is None:
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        directory = self._diagnostics_root / f"{timestamp}-s{stage}-slot{slot_index}"
        directory.mkdir(parents=True, exist_ok=False)
        if full_screen is not None:
            cv2.imwrite(str(directory / "screen.png"), full_screen)
        if name_crop is not None:
            cv2.imwrite(str(directory / "node-name.png"), name_crop)
        report = {
            "stage": stage,
            "slotIndex": slot_index,
            "reason": reason,
            "readings": [
                {
                    "text": reading.text,
                    "normalizedText": normalize_node_name(reading.text),
                    "confidence": reading.confidence,
                    "variant": reading.variant,
                }
                for reading in readings
            ],
            "nearestCandidates": list(nearest),
        }
        (directory / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return directory
