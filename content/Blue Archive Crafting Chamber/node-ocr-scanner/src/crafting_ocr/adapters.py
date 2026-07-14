from __future__ import annotations

import time
from typing import Callable

import numpy as np

from .models import ClickPoint


class MssScreenCapture:
    def __init__(self, monitor_number: int = 1) -> None:
        try:
            import mss
        except ImportError as error:
            raise RuntimeError("mss is not installed") from error
        self._mss = mss.mss()
        try:
            self._monitor = self._mss.monitors[monitor_number]
        except IndexError as error:
            raise ValueError(f"Monitor {monitor_number} does not exist") from error

    def size(self) -> tuple[int, int]:
        return int(self._monitor["width"]), int(self._monitor["height"])

    def capture(self) -> np.ndarray:
        bgra = np.asarray(self._mss.grab(self._monitor))
        return np.ascontiguousarray(bgra[:, :, :3])


class PyAutoGuiInputController:
    def __init__(
        self,
        pause_seconds: float = 0.05,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        try:
            import pyautogui
        except ImportError as error:
            raise RuntimeError("pyautogui is not installed") from error
        pyautogui.PAUSE = pause_seconds
        pyautogui.FAILSAFE = True
        self._pyautogui = pyautogui
        self._sleep = sleep

    def click(self, point: ClickPoint) -> None:
        self._pyautogui.click(point.x, point.y)

    def hold(self, point: ClickPoint, duration_seconds: float) -> None:
        if duration_seconds <= 0:
            raise ValueError("Hold duration must be positive")
        self._pyautogui.moveTo(point.x, point.y)
        self._pyautogui.mouseDown()
        try:
            self._sleep(duration_seconds)
        finally:
            self._pyautogui.mouseUp()
