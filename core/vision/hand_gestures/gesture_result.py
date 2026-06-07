from dataclasses import dataclass
from typing import Sequence

from mediapipe.tasks.python.components.containers.category import Category
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark

from core.vision.bbox import BBox
@dataclass(frozen=True)
class GestureDetection:
    gesture_name: str | None
    confidence: float | None
    hand_landmarks: Sequence[NormalizedLandmark]
    raw_gestures: Sequence[Category]
