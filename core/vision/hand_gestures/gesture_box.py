from core.vision.head_detection.head_box import HeadBox
from dataclasses import dataclass

@dataclass(frozen=True)
class GestureBox:
    x: int
    y: int
    w: int
    h: int
    
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    
    @classmethod
    def from_head_box(cls, head_box: "HeadBox", x_margin: int = 20, y_margin: int = 20, top_shift: int = 10) -> "GestureBox":
        expanded = head_box.shift(x_margin=x_margin, y_margin=y_margin, top_shift=top_shift)
        return cls(x=expanded.x, y=expanded.y, w=expanded.w, h=expanded.h)

    def __repr__(self):
        return f"GestureBox(x={self.x}, y={self.y}, w={self.w}, h={self.h})"