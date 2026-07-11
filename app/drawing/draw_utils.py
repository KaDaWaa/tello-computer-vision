import time
from typing import Iterable

import cv2
import numpy as np

from core.tracking.head_tracker import TrackedHead
from core.vision.bbox import BBox
from core.vision.hand_gestures.gesture_result import GestureDetection
from mediapipe.tasks.python.vision import HandLandmarksConnections
from mediapipe.tasks.python.vision.drawing_utils import (
    DrawingSpec,
    draw_landmarks,
)


WHITE = (245, 245, 245)
MUTED = (175, 175, 175)
CYAN = (255, 215, 80)
GREEN = (80, 230, 90)
AMBER = (0, 190, 255)
RED = (70, 70, 240)
SIDEBAR_WIDTH = 290
SIDEBAR_BACKGROUND = (18, 20, 23)


def draw_bbox(
    frame,
    bbox: BBox,
    color=(0, 255, 0),
    thickness=2,
    label_prefix=None,
):
    x1, y1 = int(bbox.x), int(bbox.y)
    x2, y2 = int(bbox.x + bbox.width), int(bbox.y + bbox.height)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    if label_prefix:
        draw_text(
            frame,
            label_prefix,
            (x1, max(14, y1 - 7)),
            font_scale=0.48,
            bg_color=color,
        )
    return frame


def draw_text(
    frame,
    text: str,
    org=(10, 30),
    font_scale=0.6,
    color=WHITE,
    thickness=1,
    bg_color=None,
):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (width, height), _ = cv2.getTextSize(
        text,
        font,
        font_scale,
        thickness,
    )
    x, y = org
    if bg_color is not None:
        pad = 4
        cv2.rectangle(
            frame,
            (x - pad, y - height - pad),
            (x + width + pad, y + pad),
            bg_color,
            -1,
        )
    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )
    return frame


def draw_gestures(frame, detections: Iterable[GestureDetection]):
    for detection in detections:
        draw_landmarks(
            frame,
            detection.hand_landmarks,
            HandLandmarksConnections.HAND_CONNECTIONS,
            landmark_drawing_spec=DrawingSpec(
                color=GREEN,
                thickness=2,
                circle_radius=2,
            ),
            connection_drawing_spec=DrawingSpec(
                color=WHITE,
                thickness=1,
                circle_radius=1,
            ),
        )


class FPSCounter:
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
        instantaneous = 1.0 / dt
        self._fps = (self._smoothing * self._fps) + (
            (1.0 - self._smoothing) * instantaneous
        )
        return self._fps


def draw_fps(frame, fps: float, org=(10, 20), color=CYAN):
    return draw_text(frame, f"FPS: {fps:.1f}", org=org, color=color)


def draw_battery(frame, battery: int, org=(10, 50), color=GREEN):
    return draw_text(frame, f"Battery: {battery}%", org=org, color=color)


def _draw_sidebar(
    canvas,
    video_width: int,
    current_state: str,
    battery: int | None,
    fps: float | None,
    control_mode: str,
    voice_listening: bool,
    detected_input: str | None,
    command_text: str | None,
    command_status: str | None,
    command_detail: str | None,
    photo_seconds_remaining: float | None,
    photo_saved: bool,
) -> None:
    frame_height, frame_width = canvas.shape[:2]
    left = video_width + 18
    right = frame_width - 18
    y = 34
    is_voice = control_mode == "voice commands"
    mode_label = "VOICE" if is_voice else "GESTURE"

    cv2.line(
        canvas,
        (video_width, 0),
        (video_width, frame_height),
        (90, 95, 100),
        1,
    )

    draw_text(
        canvas,
        current_state.upper(),
        (left, y),
        font_scale=0.65,
        color=CYAN,
        thickness=2,
    )
    y += 27
    draw_text(canvas, mode_label, (left, y), font_scale=0.57, color=CYAN)
    y += 14
    cv2.line(canvas, (left, y), (right, y), (75, 80, 85), 1)

    y += 24
    battery_text = f"{battery}%" if battery is not None else "n/a"
    fps_text = f"{fps:.1f}" if fps is not None else "n/a"
    draw_text(canvas, f"Battery  {battery_text}", (left, y), 0.48, GREEN)
    y += 22
    draw_text(canvas, f"FPS      {fps_text}", (left, y), 0.48, WHITE)
    y += 22
    mic_label = "LISTENING" if voice_listening else "OFF"
    mic_color = GREEN if voice_listening else RED
    draw_text(canvas, f"Mic      {mic_label}", (left, y), 0.48, mic_color)

    y += 14
    cv2.line(canvas, (left, y), (right, y), (75, 80, 85), 1)
    y += 24
    draw_text(
        canvas,
        f"Detected: {detected_input or '-'}",
        (left, y),
        0.44,
        WHITE,
    )
    y += 23
    draw_text(
        canvas,
        f"Command: {command_text or '-'}",
        (left, y),
        0.43,
        WHITE,
    )

    if command_status:
        y += 25
        status_colors = {
            "executed": GREEN,
            "scheduled": CYAN,
            "blocked": AMBER,
            "error": RED,
        }
        status_color = status_colors.get(command_status, MUTED)
        status_text = command_status.upper()
        if command_detail:
            status_text = f"{status_text}: {command_detail}"
        draw_text(canvas, status_text, (left, y), 0.44, status_color, 1)

    if photo_seconds_remaining is not None or photo_saved:
        photo_text = (
            f"Photo in {photo_seconds_remaining:.1f}s"
            if photo_seconds_remaining is not None
            else "Photo saved"
        )
        card_y2 = frame_height - 18
        card_y1 = max(y + 18, card_y2 - 62)
        cv2.rectangle(
            canvas,
            (left - 6, card_y1),
            (right + 6, card_y2),
            (29, 32, 36),
            -1,
        )
        cv2.rectangle(
            canvas,
            (left - 6, card_y1),
            (right + 6, card_y2),
            (85, 90, 95),
            1,
        )
        draw_text(
            canvas,
            photo_text,
            (left + 8, card_y1 + 38),
            0.58,
            GREEN if photo_saved else WHITE,
            1,
        )


def _draw_tracking_overlays(
    frame,
    tracked_heads: list[TrackedHead],
    gesture_detections: list[GestureDetection],
    active_target_id: int | None,
    show_debug: bool,
) -> None:
    frame_height, frame_width = frame.shape[:2]
    frame_center = (frame_width // 2, frame_height // 2)

    if show_debug:
        cv2.drawMarker(
            frame,
            frame_center,
            WHITE,
            cv2.MARKER_CROSS,
            24,
            1,
        )

    for head in tracked_heads:
        is_target = head.id == active_target_id
        if not show_debug and not is_target:
            continue

        head_center = tuple(map(int, head.bbox.get_center()))
        color = GREEN if is_target else AMBER if head.contain_gesture else RED
        label = f"TARGET {head.id}" if is_target else f"ID {head.id}"
        draw_bbox(frame, head.bbox, color=color, label_prefix=label)

        if is_target:
            cv2.line(frame, frame_center, head_center, GREEN, 2)
        if show_debug:
            cv2.circle(frame, head_center, 4, color, -1)
            zone_color = GREEN if head.contain_gesture else RED
            draw_bbox(frame, head.gesture_zone, color=zone_color, thickness=1)

    if show_debug:
        draw_gestures(frame, gesture_detections)


def render(
    frame,
    tracked_heads: Iterable[TrackedHead],
    gesture_detections: Iterable[GestureDetection],
    active_target_id: int | None = None,
    current_state: str = "unknown",
    battery: int | None = None,
    fps: float | None = None,
    control_mode: str = "gestures",
    voice_listening: bool = False,
    last_voice_cmd: str = "",
    *,
    detected_input: str | None = None,
    command_text: str | None = None,
    command_status: str | None = None,
    command_detail: str | None = None,
    photo_seconds_remaining: float | None = None,
    photo_saved: bool = False,
    show_debug: bool = True,
):
    heads = list(tracked_heads)
    gestures = list(gesture_detections)
    video_frame = frame.copy()
    _draw_tracking_overlays(
        video_frame,
        heads,
        gestures,
        active_target_id,
        show_debug,
    )
    frame_height, frame_width = video_frame.shape[:2]
    canvas = np.full(
        (frame_height, frame_width + SIDEBAR_WIDTH, 3),
        SIDEBAR_BACKGROUND,
        dtype=video_frame.dtype,
    )
    canvas[:, :frame_width] = video_frame
    _draw_sidebar(
        canvas,
        frame_width,
        current_state,
        battery,
        fps,
        control_mode,
        voice_listening,
        detected_input or last_voice_cmd,
        command_text,
        command_status,
        command_detail,
        photo_seconds_remaining,
        photo_saved,
    )
    return canvas
