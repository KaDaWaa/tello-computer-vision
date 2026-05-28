from dataclasses import dataclass

@dataclass(frozen=True)
class HeadBox:
    x: int
    y: int
    w: int
    h: int

    def contains_point(self, x: int, y: int) -> bool:
        return self.x <= x <= self.x + self.w and self.y <= y <= self.y + self.h

    def expanded(self, x_margin: int, y_margin: int, top_shift: int = 0) -> "HeadBox":
        new_x = self.x - x_margin
        new_y = self.y - y_margin - top_shift
        new_w = self.w + (x_margin * 2)
        new_h = self.h + (y_margin * 2) + top_shift
        return HeadBox(x=max(0, new_x), y=max(0, new_y), w=max(1, new_w), h=max(1, new_h))

    def shift(self, x_shift: int = 0, y_shift: int = 0) -> "HeadBox":
        return HeadBox(x=self.x + x_shift, y=self.y + y_shift, w=self.w, h=self.h)