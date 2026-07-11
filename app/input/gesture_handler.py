from __future__ import annotations

from app.commands import AppCommand, Direction
from app.state import control_mode


class GestureHandler:
    """Translate stable gesture labels into input-independent commands.

    This class deliberately has no access to drone hardware, application
    state, tracked-head selection, or MediaPipe result types. The vision
    pipeline supplies one recognized label at a time and the handler emits
    at most one command for a continuous gesture.
    """

    REQUIRED_STABLE_FRAMES = 3

    COMMANDS_BY_GESTURE = {
        "like": AppCommand.move(Direction.UP, 30),
        "dislike": AppCommand.move(Direction.DOWN, 30),
        "fist": AppCommand.start_follow(),
        "stop": AppCommand.stop_follow(),
        "ok": AppCommand.land(),
        "grip": AppCommand.take_photo(delay_seconds=3),
        "one": AppCommand.move(Direction.LEFT, 30),
        "peace": AppCommand.move(Direction.RIGHT, 30),
        "three2": AppCommand.rotate(Direction.LEFT, 90),
        "four": AppCommand.rotate(Direction.RIGHT, 90),
        "call": AppCommand.set_control_mode(control_mode.VOICE_COMMANDS),
        "rock": AppCommand.flip(Direction.FORWARD),
    }

    def __init__(
        self,
        required_stable_frames: int = REQUIRED_STABLE_FRAMES,
    ) -> None:
        if required_stable_frames < 1:
            raise ValueError("required_stable_frames must be at least 1")

        self.required_stable_frames = required_stable_frames
        self._stable_gesture_name = ""
        self._stable_gesture_frames = 0
        self._consumed_gesture_name = ""

    def handle(
        self,
        gesture_name: str | None,
    ) -> AppCommand | None:
        """Return a command once a recognized gesture is stable.

        A held gesture is consumed after emitting its command and cannot
        repeat until the gesture disappears or changes. Command timing and
        safety locks are intentionally owned by the flight controller.
        """

        normalized_name = self.normalize_gesture_name(gesture_name)

        if normalized_name not in self.COMMANDS_BY_GESTURE:
            self._clear_observation()
            return None

        if normalized_name == self._stable_gesture_name:
            self._stable_gesture_frames += 1
        else:
            self._stable_gesture_name = normalized_name
            self._stable_gesture_frames = 1
            self._consumed_gesture_name = ""

        if self._stable_gesture_frames < self.required_stable_frames:
            return None

        if normalized_name == self._consumed_gesture_name:
            return None

        self._consumed_gesture_name = normalized_name
        return self.COMMANDS_BY_GESTURE[normalized_name]

    def reset(self) -> None:
        """Forget gesture stability when gesture control is deactivated."""

        self._clear_observation()

    @staticmethod
    def normalize_gesture_name(name: str | None) -> str:
        if not name:
            return ""
        return name.strip().lower().replace(" ", "_")

    def _clear_observation(self) -> None:
        self._stable_gesture_name = ""
        self._stable_gesture_frames = 0
        self._consumed_gesture_name = ""
