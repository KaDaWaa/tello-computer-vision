import time
from typing import Iterable

import cv2

from core.tracking.head_tracker import TrackedHead
from core.vision.hand_gestures.gesture_result import GestureDetection
from mediapipe.tasks.python.vision import HandLandmarksConnections
from core.vision.bbox import BBox
from mediapipe.tasks.python.vision.drawing_utils import DrawingSpec, RED_COLOR, draw_landmarks


def draw_bbox(frame, bbox: BBox, color=(0, 255, 0), thickness=2, label_prefix=None):
    """Draw bounding boxes for HeadBox objects on the frame in-place.

    Returns the modified frame.
    """
    x1, y1 = int(bbox.x), int(bbox.y)
    x2, y2 = int(bbox.x + bbox.width), int(bbox.y + bbox.height)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    label = label_prefix
    draw_text(frame, label if label else "", (x1, max(12, y1 - 6)), bg_color=color)
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

def draw_gestures(frame, detections: Iterable[GestureDetection]):
    """Draw MediaPipe-style landmarks and optional connections on the frame."""
    for detection in detections:
        draw_landmarks(
            frame,
            detection.hand_landmarks,
            HandLandmarksConnections.HAND_CONNECTIONS,
            landmark_drawing_spec=DrawingSpec(color=RED_COLOR, thickness=2, circle_radius=2))
    
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

def draw_battery(frame, battery: int, org=(10, 50), color=(255, 255, 0)):
    text = f"Battery: {battery}%"
    return draw_text(frame, text, org=org, font_scale=0.6, color=color, thickness=1, bg_color=(0, 0, 0))


def _format_gestures(gesture_detections: Iterable[GestureDetection]) -> str:
    names = []
    for detection in gesture_detections:
        if detection.gesture_name:
            names.append(detection.gesture_name.replace("_", " "))
    unique_names = []
    for name in names:
        if name not in unique_names:
            unique_names.append(name)
    return ", ".join(unique_names) if unique_names else "none"


def _draw_status_panel(frame, current_state: str, gesture_text: str, battery_text: str, fps_text: str):
    frame_height, frame_width = frame.shape[:2]
    panel_width = max(190, int(frame_width * 0.18))
    panel_height = 118
    x1 = frame_width - panel_width - 10
    y1 = 10
    x2 = frame_width - 10
    y2 = y1 + panel_height
    cv2.rectangle(frame, (x1, y1), (x2, y2), (18, 18, 18), -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 1)

    y = y1 + 22
    draw_text(frame, "STATUS", org=(x1 + 12, y), font_scale=0.55, color=(255, 255, 255), bg_color=(40, 40, 40))
    y += 23
    draw_text(frame, f"State: {current_state}", org=(x1 + 12, y), font_scale=0.48, color=(255, 220, 120), bg_color=(35, 35, 35))
    y += 20
    draw_text(frame, f"Gesture: {gesture_text}", org=(x1 + 12, y), font_scale=0.48, color=(120, 220, 255), bg_color=(35, 35, 35))
    y += 20
    draw_text(frame, f"Battery: {battery_text}", org=(x1 + 12, y), font_scale=0.48, color=(120, 255, 140), bg_color=(35, 35, 35))
    y += 20
    draw_text(frame, f"FPS: {fps_text}", org=(x1 + 12, y), font_scale=0.48, color=(255, 190, 120), bg_color=(35, 35, 35))

def render(
    frame,
    tracked_heads: Iterable["TrackedHead"],
    gesture_detections: Iterable[GestureDetection],
    active_target_id: int | None = None,
    current_state: str = "unknown",
    battery: int | None = None,
    fps: float | None = None,
):
    """Example render function to visualize tracked heads and detected gestures."""
    frame_height, frame_width = frame.shape[:2]
    frame_center = (frame_width // 2, frame_height // 2)
    cv2.circle(frame, frame_center, 5, (255, 255, 255), -1)
    for head in tracked_heads:
        head_center_x, head_center_y = head.bbox.get_center()
        head_center = (int(head_center_x), int(head_center_y))
        line_color = (0, 255, 0) if head.id == active_target_id else (255, 180, 0) if head.contain_gesture else (0, 0, 255)
        if head.id == active_target_id:
            cv2.line(frame, frame_center, head_center, line_color, 2)
        cv2.circle(frame, head_center, 4, line_color, -1)
        draw_bbox(frame, head.bbox, label_prefix=f"ID {head.id}")
        gesture_zone_color = (
            (0, 255, 0)
            if head.contain_gesture
            else (0, 0, 255)
        )
        draw_bbox(frame, head.gesture_zone, color=gesture_zone_color, thickness=1)
        # Optionally draw gesture zones or other info related to the head

    draw_gestures(frame, gesture_detections)

    gesture_text = _format_gestures(gesture_detections)
    battery_text = f"{battery}%" if battery is not None else "n/a"
    fps_text = f"{fps:.1f}" if fps is not None else "n/a"
    _draw_status_panel(frame, current_state, gesture_text, battery_text, fps_text)