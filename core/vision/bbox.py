from dataclasses import dataclass, field

@dataclass(frozen=True)
class BBox:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_detection(cls, detection) -> "BBox":
        return cls(
            x=int(detection.bounding_box.origin_x),
            y=int(detection.bounding_box.origin_y),
            width=int(detection.bounding_box.width),
            height=int(detection.bounding_box.height)
        )

    def contains_point(self, x: int, y: int) -> bool:
            return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def expanded(self, x_margin: int, y_margin: int, top_shift: int = 0) -> "BBox":
        new_x = self.x - x_margin
        new_y = self.y - y_margin - top_shift
        new_w = self.width + (x_margin * 2)
        new_h = self.height + (y_margin * 2) + top_shift
        return BBox(x=max(0, new_x), y=max(0, new_y), width=max(1, new_w), height=max(1, new_h))

    def shift(self, x_shift: int = 0, y_shift: int = 0) -> "BBox":
        return BBox(x=self.x + x_shift, y=self.y + y_shift, width=self.width, height=self.height)

    def get_center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)