from dataclasses import dataclass, field
import math

from core.vision.bbox import BBox
from core.vision.hand_gestures.gesture_result import GestureDetection
from mediapipe.tasks.python.vision.drawing_utils import _normalized_to_pixel_coordinates

from typing import Iterable

def build_gesture_zone(head_bbox: BBox) -> BBox:
    return head_bbox.shift(x_shift=-(head_bbox.width + 30)).expanded(20, 20)

@dataclass
class TrackedHead:
    id: int
    bbox: BBox
    center: tuple[int, int]
    last_seen: float
    gesture_zone: BBox
    contain_gesture: bool = False
    age: int = 0
    ema_alpha: float = 0.8  # EMA smoothing factor (0=no smoothing, 1=only new)
    
    def smooth_bbox(self, new_bbox: BBox) -> BBox:
        """Apply exponential moving average to smooth bbox across frames"""
        smoothed_x = int(self.bbox.x * (1 - self.ema_alpha) + new_bbox.x * self.ema_alpha)
        smoothed_y = int(self.bbox.y * (1 - self.ema_alpha) + new_bbox.y * self.ema_alpha)
        smoothed_w = int(self.bbox.width * (1 - self.ema_alpha) + new_bbox.width * self.ema_alpha)
        smoothed_h = int(self.bbox.height * (1 - self.ema_alpha) + new_bbox.height * self.ema_alpha)
        return BBox(x=smoothed_x, y=smoothed_y, width=smoothed_w, height=smoothed_h)
    
    def contains_gesture(self, gestures: Iterable["GestureDetection"], image_width: int, image_height: int):
        visible_gestures = []
        for gesture in gestures:
            visible_landmarks: list[tuple[int, int]] = []
            for landmark in gesture.hand_landmarks:
                if (
                        landmark.visibility is not None
                    and landmark.visibility < 0.5
                        ) or (
                    landmark.presence is not None
                    and landmark.presence < 0.5
                ):
                    continue
                landmark_px = _normalized_to_pixel_coordinates(landmark.x, landmark.y, image_width, image_height)
                if landmark_px is None:
                    continue
                visible_landmarks.append(landmark_px)
            
            if visible_landmarks: visible_gestures.append(visible_landmarks)

        if not visible_gestures:
            self.contain_gesture = False

        self.contain_gesture = any(all(self.gesture_zone.contains_point(x, y) for x, y in visible_landmarks) for visible_landmarks in visible_gestures)

    def refresh_gesture_zone(self) -> None:
        self.gesture_zone = build_gesture_zone(self.bbox)


@dataclass
class HeadTracker:
    tracked_heads: list[TrackedHead] = field(default_factory=list)
    current_id: int = 0
    max_distance: float = 200.0  # Increased from 100 to handle jitter from MediaPipe detector
    max_missing_time: float = 1.0

    def update(
        self,
        raw_heads: list[BBox],
        timestamp: float
    ) -> list[TrackedHead]:

        # First frame
        if not self.tracked_heads:
            for raw_head in raw_heads:
                tracked_head = TrackedHead(
                    id=self.current_id,
                    bbox=raw_head,
                    center=raw_head.get_center(),
                    last_seen=timestamp,
                    gesture_zone=build_gesture_zone(raw_head),
                )
                self.tracked_heads.append(tracked_head)
                self.current_id += 1

            return self.tracked_heads

        # Detections that have not yet been assigned
        unused_raw_heads = raw_heads.copy()

        # Update existing tracked heads
        for tracked_head in self.tracked_heads:

            closest_raw_head = None
            min_distance = float("inf")

            for raw_head in unused_raw_heads:

                raw_center = raw_head.get_center()

                distance = math.hypot(
                    tracked_head.center[0] - raw_center[0],
                    tracked_head.center[1] - raw_center[1]
                )

                if distance < min_distance:
                    min_distance = distance
                    closest_raw_head = raw_head

            # Match found
            if (
                closest_raw_head is not None
                and min_distance <= self.max_distance
            ):
                # Apply EMA smoothing to reduce jitter
                tracked_head.bbox = tracked_head.smooth_bbox(closest_raw_head)
                tracked_head.center = tracked_head.bbox.get_center()
                tracked_head.last_seen = timestamp
                tracked_head.age += 1
                tracked_head.refresh_gesture_zone()

                unused_raw_heads.remove(closest_raw_head)

        # Remove stale tracks
        self.tracked_heads = [
            tracked_head
            for tracked_head in self.tracked_heads
            if timestamp - tracked_head.last_seen <= self.max_missing_time
        ]

        # Create new tracks for unmatched detections
        for raw_head in unused_raw_heads:
            tracked_head = TrackedHead(
                id=self.current_id,
                bbox=raw_head,
                center=raw_head.get_center(),
                last_seen=timestamp,
                gesture_zone=build_gesture_zone(raw_head),
            )

            self.tracked_heads.append(tracked_head)

            self.current_id += 1

        return self.tracked_heads