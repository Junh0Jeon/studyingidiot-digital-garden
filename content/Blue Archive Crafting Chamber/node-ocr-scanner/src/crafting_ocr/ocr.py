from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .models import OcrReading


def build_preprocessing_variants(image: np.ndarray) -> list[tuple[str, np.ndarray]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enlarged = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(enlarged)
    _, binary = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return [("gray", enlarged), ("clahe", clahe), ("otsu", binary)]


class EasyOcrEngine:
    def __init__(self, gpu: bool = False) -> None:
        try:
            import easyocr
        except ImportError as error:
            raise RuntimeError(
                "EasyOCR is not installed. Install the project dependencies first."
            ) from error
        self._reader = easyocr.Reader(["ko", "en"], gpu=gpu)

    def recognize(self, image: np.ndarray) -> list[OcrReading]:
        readings: list[OcrReading] = []
        for variant, processed in build_preprocessing_variants(image):
            raw_results: list[Any] = self._reader.readtext(
                processed,
                detail=1,
                paragraph=False,
            )
            if not raw_results:
                continue
            ordered = sorted(
                raw_results,
                key=lambda result: (
                    min(point[1] for point in result[0]),
                    min(point[0] for point in result[0]),
                ),
            )
            text = " ".join(str(result[1]) for result in ordered).strip()
            confidence = min(float(result[2]) for result in ordered)
            readings.append(OcrReading(text, confidence, variant))
        return readings
