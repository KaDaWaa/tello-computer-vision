import time
from typing import Iterable

import cv2

from core.vision.head_detection.head_box import HeadBox


def draw_bboxes(frame, boxes: Iterable[HeadBox], color=(0, 255, 0), thickness=2, label_prefix="Head"):
    """Draw bounding boxes for HeadBox objects on the frame in-place.

    Returns the modified frame.
    """
    for i, b in enumerate(boxes):
        x1, y1 = int(b.x), int(b.y)
        x2, y2 = int(b.x + b.w), int(b.y + b.h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        label = f"{label_prefix} {i+1}"
        draw_text(frame, label, (x1, max(12, y1 - 6)), bg_color=color)
    return frame


def draw_text(frame, text: str, org=(10, 30), font_scale=0.6, color=(255, 255, 255), thickness=1, bg_color=None):
    """Draw text with optional background rectangle to improve readability."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (w, h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = org
    if bg_color is not None:
        pad = 4
        cv2.rectangle(frame, (x - pad, y - h - pad), (x + w + pad, y + pad), bg_color, -1)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return frame


class FPSCounter:
    """Simple FPS counter. Call `tick()` each loop and `fps` property to read value."""

    def __init__(self, smoothing: float = 0.9):
        self._last = None
        self._fps = 0.0
        self._smoothing = smoothing

    def tick(self):
        now = time.time()
        if self._last is None:
            self._last = now
            return self._fps
        dt = now - self._last
        self._last = now
        if dt <= 0:
            return self._fps
        inst = 1.0 / dt
        # exponential smoothing
        self._fps = (self._smoothing * self._fps) + ((1.0 - self._smoothing) * inst)
        return self._fps


def draw_fps(frame, fps: float, org=(10, 20), color=(0, 255, 255)):
    text = f"FPS: {fps:.1f}"
    return draw_text(frame, text, org=org, font_scale=0.6, color=color, thickness=1, bg_color=(0, 0, 0))
