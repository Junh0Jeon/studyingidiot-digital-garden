from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ClickPoint:
    x: int
    y: int


@dataclass(frozen=True)
class Rectangle:
    x: int
    y: int
    width: int
    height: int

    def validate(self, screen_width: int, screen_height: int) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Rectangle width and height must be positive")
        if self.x < 0 or self.y < 0:
            raise ValueError("Rectangle origin must be non-negative")
        if self.x + self.width > screen_width or self.y + self.height > screen_height:
            raise ValueError("Rectangle is outside the configured screen")


@dataclass(frozen=True)
class ScreenProfile:
    width: int
    height: int
    stage_click_points: dict[int, tuple[ClickPoint, ...]]
    node_name_region: Rectangle
    ocr_confidence_threshold: float = 0.8
    relaxed_exact_confidence_threshold: float = 0.22
    relaxed_exact_minimum_name_length: int = 3
    initial_settle_seconds: float = 0.15
    stability_poll_seconds: float = 0.05
    stability_timeout_seconds: float = 1.5
    stability_mean_difference_threshold: float = 2.0
    fuzzy_minimum_confidence: float = 0.18
    fuzzy_maximum_distance: int = 2
    fuzzy_long_name_minimum_length: int = 5
    fuzzy_long_name_maximum_distance: int = 3
    fuzzy_minimum_name_length: int = 3
    fuzzy_minimum_consensus_count: int = 2

    @classmethod
    def from_json(cls, path: Path) -> "ScreenProfile":
        payload = json.loads(path.read_text(encoding="utf-8"))
        points = {
            int(stage): tuple(
                ClickPoint(x=int(point["x"]), y=int(point["y"]))
                for point in stage_points
            )
            for stage, stage_points in payload["stageClickPoints"].items()
        }
        region = payload["nodeNameRegion"]
        profile = cls(
            width=int(payload["width"]),
            height=int(payload["height"]),
            stage_click_points=points,
            node_name_region=Rectangle(
                x=int(region["x"]),
                y=int(region["y"]),
                width=int(region["width"]),
                height=int(region["height"]),
            ),
            ocr_confidence_threshold=float(payload.get("ocrConfidenceThreshold", 0.8)),
            relaxed_exact_confidence_threshold=float(
                payload.get("relaxedExactConfidenceThreshold", 0.22)
            ),
            relaxed_exact_minimum_name_length=int(
                payload.get("relaxedExactMinimumNameLength", 3)
            ),
            initial_settle_seconds=float(payload.get("initialSettleSeconds", 0.15)),
            stability_poll_seconds=float(payload.get("stabilityPollSeconds", 0.05)),
            stability_timeout_seconds=float(payload.get("stabilityTimeoutSeconds", 1.5)),
            stability_mean_difference_threshold=float(
                payload.get("stabilityMeanDifferenceThreshold", 2.0)
            ),
            fuzzy_minimum_confidence=float(payload.get("fuzzyMinimumConfidence", 0.18)),
            fuzzy_maximum_distance=int(payload.get("fuzzyMaximumDistance", 2)),
            fuzzy_long_name_minimum_length=int(
                payload.get("fuzzyLongNameMinimumLength", 5)
            ),
            fuzzy_long_name_maximum_distance=int(
                payload.get("fuzzyLongNameMaximumDistance", 3)
            ),
            fuzzy_minimum_name_length=int(payload.get("fuzzyMinimumNameLength", 3)),
            fuzzy_minimum_consensus_count=int(payload.get("fuzzyMinimumConsensusCount", 2)),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Screen width and height must be positive")
        if not 0 <= self.ocr_confidence_threshold <= 1:
            raise ValueError("OCR confidence threshold must be between 0 and 1")
        if not 0 <= self.relaxed_exact_confidence_threshold <= 1:
            raise ValueError("Relaxed exact confidence threshold must be between 0 and 1")
        if self.relaxed_exact_confidence_threshold > self.ocr_confidence_threshold:
            raise ValueError("Relaxed exact threshold must not exceed OCR threshold")
        if self.relaxed_exact_minimum_name_length < 1:
            raise ValueError("Relaxed exact minimum name length must be positive")
        if not 0 <= self.fuzzy_minimum_confidence <= 1:
            raise ValueError("Fuzzy confidence threshold must be between 0 and 1")
        if min(
            self.fuzzy_maximum_distance,
            self.fuzzy_long_name_minimum_length,
            self.fuzzy_long_name_maximum_distance,
            self.fuzzy_minimum_name_length,
            self.fuzzy_minimum_consensus_count,
        ) < 1:
            raise ValueError("Fuzzy matching limits must be positive")
        if min(
            self.initial_settle_seconds,
            self.stability_poll_seconds,
            self.stability_timeout_seconds,
            self.stability_mean_difference_threshold,
        ) < 0:
            raise ValueError("Timing and stability values must be non-negative")
        self.node_name_region.validate(self.width, self.height)
        for stage in (1, 2, 3):
            stage_points = self.stage_click_points.get(stage)
            if stage_points is None or len(stage_points) != 5:
                raise ValueError(f"Stage {stage} must contain exactly five click points")
            for point in stage_points:
                if not (0 <= point.x < self.width and 0 <= point.y < self.height):
                    raise ValueError(f"Stage {stage} click point is outside the screen: {point}")


@dataclass(frozen=True)
class OcrReading:
    text: str
    confidence: float
    variant: str


@dataclass(frozen=True)
class CandidateNode:
    slot_index: int
    node_id: int
    click_point: ClickPoint
    recognized_text: str
    normalized_text: str
    ocr_confidence: float
    recognition_method: str


@dataclass(frozen=True)
class CandidateNodeBatch:
    stage: int
    candidates: tuple[CandidateNode, ...]

    @property
    def candidate_node_ids(self) -> tuple[int, ...]:
        return tuple(candidate.node_id for candidate in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "candidateNodeIds": list(self.candidate_node_ids),
            "candidates": [
                {
                    "slotIndex": node.slot_index,
                    "nodeId": node.node_id,
                    "clickPoint": {"x": node.click_point.x, "y": node.click_point.y},
                    "recognizedText": node.recognized_text,
                    "normalizedText": node.normalized_text,
                    "ocrConfidence": node.ocr_confidence,
                    "recognitionMethod": node.recognition_method,
                }
                for node in self.candidates
            ],
        }


@dataclass(frozen=True)
class NodeDecisionTarget:
    node_id: int
    click_point: ClickPoint
    slot_index: int
