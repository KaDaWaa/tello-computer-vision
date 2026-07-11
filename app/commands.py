from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from app.state import control_mode


class CommandType(StrEnum):
    TAKE_OFF = "take_off"
    LAND = "land"
    MOVE = "move"
    ROTATE = "rotate"
    FLIP = "flip"
    START_FOLLOW = "start_follow"
    STOP_FOLLOW = "stop_follow"
    SET_CONTROL_MODE = "set_control_mode"
    TAKE_PHOTO = "take_photo"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    FORWARD = "forward"
    BACK = "back"


class CommandPriority(IntEnum):
    BACKGROUND = 10
    FLIGHT_ACTION = 50
    FOLLOW = 60
    TAKE_OFF = 70
    MODE_CHANGE = 80
    STOP_FOLLOW = 90
    LAND = 100


_PAYLOAD_FREE_COMMANDS = {
    CommandType.TAKE_OFF,
    CommandType.LAND,
    CommandType.START_FOLLOW,
    CommandType.STOP_FOLLOW,
}


@dataclass(frozen=True, slots=True)
class AppCommand:
    """Input-independent request for the application to perform an action.

    Audio and gesture handlers create these commands. The application
    coordinator will handle application-level commands and forward flight
    commands to the flight controller.
    """

    type: CommandType
    direction: Direction | None = None
    amount: int | None = None
    mode: control_mode | None = None
    delay_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.type in _PAYLOAD_FREE_COMMANDS:
            self._require_no_payload()
            return

        if self.type == CommandType.MOVE:
            if not isinstance(self.direction, Direction):
                raise ValueError("MOVE requires a valid direction")
            self._require_positive_amount("MOVE")
            self._require_absent(mode=True, delay=True)
            return

        if self.type == CommandType.ROTATE:
            if self.direction not in (Direction.LEFT, Direction.RIGHT):
                raise ValueError("ROTATE direction must be left or right")
            self._require_positive_amount("ROTATE")
            self._require_absent(mode=True, delay=True)
            return

        if self.type == CommandType.FLIP:
            if self.direction not in (
                Direction.FORWARD,
                Direction.BACK,
                Direction.LEFT,
                Direction.RIGHT,
            ):
                raise ValueError("FLIP requires a flight direction")
            self._require_absent(amount=True, mode=True, delay=True)
            return

        if self.type == CommandType.SET_CONTROL_MODE:
            if not isinstance(self.mode, control_mode):
                raise ValueError("SET_CONTROL_MODE requires a mode")
            self._require_absent(direction=True, amount=True, delay=True)
            return

        if self.type == CommandType.TAKE_PHOTO:
            if self.delay_seconds is None or self.delay_seconds < 0:
                raise ValueError("TAKE_PHOTO requires a non-negative delay")
            self._require_absent(direction=True, amount=True, mode=True)
            return

        raise ValueError(f"Unsupported command type: {self.type}")

    @property
    def priority(self) -> CommandPriority:
        return {
            CommandType.LAND: CommandPriority.LAND,
            CommandType.STOP_FOLLOW: CommandPriority.STOP_FOLLOW,
            CommandType.SET_CONTROL_MODE: CommandPriority.MODE_CHANGE,
            CommandType.TAKE_OFF: CommandPriority.TAKE_OFF,
            CommandType.START_FOLLOW: CommandPriority.FOLLOW,
            CommandType.MOVE: CommandPriority.FLIGHT_ACTION,
            CommandType.ROTATE: CommandPriority.FLIGHT_ACTION,
            CommandType.FLIP: CommandPriority.FLIGHT_ACTION,
            CommandType.TAKE_PHOTO: CommandPriority.BACKGROUND,
        }[self.type]

    @property
    def description(self) -> str:
        if self.type == CommandType.MOVE:
            return f"MOVE {self.direction.value.upper()} {self.amount} cm"
        if self.type == CommandType.ROTATE:
            return f"ROTATE {self.direction.value.upper()} {self.amount} deg"
        if self.type == CommandType.FLIP:
            return f"FLIP {self.direction.value.upper()}"
        if self.type == CommandType.SET_CONTROL_MODE:
            mode = (
                "VOICE"
                if self.mode == control_mode.VOICE_COMMANDS
                else "GESTURE"
            )
            return f"SWITCH TO {mode} MODE"
        if self.type == CommandType.TAKE_PHOTO:
            return f"TAKE PHOTO IN {self.delay_seconds:g}s"
        return {
            CommandType.TAKE_OFF: "TAKE OFF",
            CommandType.LAND: "LAND",
            CommandType.START_FOLLOW: "START FOLLOW",
            CommandType.STOP_FOLLOW: "STOP FOLLOW",
        }[self.type]

    @classmethod
    def take_off(cls) -> AppCommand:
        return cls(CommandType.TAKE_OFF)

    @classmethod
    def land(cls) -> AppCommand:
        return cls(CommandType.LAND)

    @classmethod
    def move(cls, direction: Direction, distance_cm: int = 30) -> AppCommand:
        return cls(CommandType.MOVE, direction=direction, amount=distance_cm)

    @classmethod
    def rotate(cls, direction: Direction, degrees: int = 90) -> AppCommand:
        return cls(CommandType.ROTATE, direction=direction, amount=degrees)

    @classmethod
    def flip(cls, direction: Direction = Direction.FORWARD) -> AppCommand:
        return cls(CommandType.FLIP, direction=direction)

    @classmethod
    def start_follow(cls) -> AppCommand:
        return cls(CommandType.START_FOLLOW)

    @classmethod
    def stop_follow(cls) -> AppCommand:
        return cls(CommandType.STOP_FOLLOW)

    @classmethod
    def set_control_mode(cls, mode: control_mode) -> AppCommand:
        return cls(CommandType.SET_CONTROL_MODE, mode=mode)

    @classmethod
    def take_photo(cls, delay_seconds: float = 3.0) -> AppCommand:
        return cls(CommandType.TAKE_PHOTO, delay_seconds=delay_seconds)

    def _require_positive_amount(self, command_name: str) -> None:
        if self.amount is None or self.amount <= 0:
            raise ValueError(f"{command_name} requires a positive amount")

    def _require_no_payload(self) -> None:
        self._require_absent(direction=True, amount=True, mode=True, delay=True)

    def _require_absent(
        self,
        *,
        direction: bool = False,
        amount: bool = False,
        mode: bool = False,
        delay: bool = False,
    ) -> None:
        unexpected = []
        if direction and self.direction is not None:
            unexpected.append("direction")
        if amount and self.amount is not None:
            unexpected.append("amount")
        if mode and self.mode is not None:
            unexpected.append("mode")
        if delay and self.delay_seconds is not None:
            unexpected.append("delay_seconds")
        if unexpected:
            fields = ", ".join(unexpected)
            raise ValueError(f"{self.type.value} received unexpected payload: {fields}")
