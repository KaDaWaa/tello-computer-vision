from core.vision.head_detection.head_box import HeadBox
from dataclasses import dataclass

@dataclass(frozen=True)
class GestureBox:
    x: int
    y: int
    w: int
    h: int
    
    @classmethod
    def from_head_box(cls, head_box: "HeadBox") -> "GestureBox":
        gesture_zone = head_box.shift(x_shift= -(head_box.w + 20)).expanded(20, 20)
        return cls(x=gesture_zone.x, y=gesture_zone.y, w=gesture_zone.w, h=gesture_zone.h)

    def __repr__(self):
        return f"GestureBox(x={self.x}, y={self.y}, w={self.w}, h={self.h})"