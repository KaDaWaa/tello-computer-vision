from types import SimpleNamespace

from core.drone.base_drone import BaseDrone
from core.vision.bbox import BBox


class RecordingDrone(BaseDrone):
    """In-memory drone used to verify controller decisions."""

    def __init__(self) -> None:
        self.connected = False
        self.is_flying = False
        self.takeoff_calls = 0
        self.land_calls = 0
        self.moves: list[tuple[str, int]] = []
        self.rotations: list[int] = []
        self.flips: list[str] = []
        self.rc_commands: list[tuple[int, int, int, int]] = []

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def takeoff(self) -> None:
        self.takeoff_calls += 1
        self.is_flying = True

    def land(self) -> None:
        self.land_calls += 1
        self.is_flying = False

    def move(self, direction: str, distance: int) -> None:
        self.moves.append((direction, distance))

    def rotate(self, angle: int) -> None:
        self.rotations.append(angle)

    def flip(self, direction: str) -> None:
        self.flips.append(direction)

    def send_rc_control(
        self,
        left_right_velocity: int,
        forward_backward_velocity: int,
        up_down_velocity: int,
        yaw_velocity: int,
    ) -> None:
        self.rc_commands.append(
            (
                left_right_velocity,
                forward_backward_velocity,
                up_down_velocity,
                yaw_velocity,
            )
        )

    def get_battery(self) -> int:
        return 100

    def get_sdk_drone(self):
        return None


def make_head(
    head_id: int = 1,
    *,
    center: tuple[int, int] = (320, 240),
    height: int = 86,
    contains_gesture: bool = True,
):
    width = max(1, height)
    x = center[0] - width // 2
    y = center[1] - height // 2
    return SimpleNamespace(
        id=head_id,
        center=center,
        bbox=BBox(x=x, y=y, width=width, height=height),
        contain_gesture=contains_gesture,
    )


def make_gesture(name: str):
    return SimpleNamespace(gesture_name=name)

