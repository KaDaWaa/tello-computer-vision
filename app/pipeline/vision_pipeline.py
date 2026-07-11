from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from time import time

import cv2
import numpy as np

from core.tracking.head_tracker import HeadTracker, TrackedHead
from core.vision.hand_gestures.gesture_detector import GestureDetector
from core.vision.hand_gestures.gesture_result import GestureDetection
from core.vision.head_detection.head_detector import HeadDetector


@dataclass(frozen=True, slots=True)
class VisionFrame:
    """Vision results and the original BGR frame for one application tick."""

    frame: np.ndarray
    timestamp: float
    tracked_heads: list[TrackedHead]
    gestures: list[GestureDetection]

    @property
    def width(self) -> int:
        return int(self.frame.shape[1])

    @property
    def height(self) -> int:
        return int(self.frame.shape[0])

    @property
    def control_gesture_name(self) -> str | None:
        """Return the recognized gesture only when it is in a head zone."""

        if not any(head.contain_gesture for head in self.tracked_heads):
            return None
        return next(
            (
                gesture.gesture_name
                for gesture in self.gestures
                if gesture.gesture_name
            ),
            None,
        )


class VisionPipeline:
    """Run detection, tracking, and gesture-zone association for each frame."""

    def __init__(
        self,
        head_detector: HeadDetector | None = None,
        gesture_detector: GestureDetector | None = None,
        head_tracker: HeadTracker | None = None,
        executor: Executor | None = None,
    ) -> None:
        self.head_detector = head_detector or HeadDetector()
        self.gesture_detector = gesture_detector or GestureDetector()
        self.head_tracker = head_tracker or HeadTracker()
        self._executor = executor or ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="VisionWorker",
        )
        self._owns_executor = executor is None
        self._closed = False

    def process(
        self,
        frame: np.ndarray,
        timestamp: float | None = None,
    ) -> VisionFrame:
        if self._closed:
            raise RuntimeError("VisionPipeline is closed")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("VisionPipeline expects a three-channel BGR frame")

        now = timestamp if timestamp is not None else time()
        frame_height, frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        heads_future = self._executor.submit(
            self.head_detector.detect,
            rgb_frame,
        )
        gestures_future = self._executor.submit(
            self.gesture_detector.detect,
            rgb_frame,
        )

        raw_heads = heads_future.result()
        gestures = list(gestures_future.result())
        tracked_heads = list(self.head_tracker.update(raw_heads, now))

        for head in tracked_heads:
            head.contains_gesture(gestures, frame_width, frame_height)

        return VisionFrame(
            frame=frame,
            timestamp=now,
            tracked_heads=tracked_heads,
            gestures=gestures,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self._owns_executor:
            self._executor.shutdown(wait=True, cancel_futures=True)

        for detector in (self.head_detector, self.gesture_detector):
            close = getattr(detector, "close", None)
            if callable(close):
                close()

    def __enter__(self) -> VisionPipeline:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

