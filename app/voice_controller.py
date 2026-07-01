"""Voice command controller — translates recognized voice commands into drone actions.

Works alongside the existing FollowController.  When voice mode is active,
the main loop polls VoiceListener for commands and feeds them here.
"""

from __future__ import annotations

from time import time

from app.state import State, states
from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import TrackedHead


class VoiceController:
    """Maps voice command strings to drone API calls."""

    COMMAND_COOLDOWN_SECONDS = 1.0  # prevent rapid-fire duplicate commands

    # Mapping of voice command → (method_name, *args)
    # Keeps a clean separation between parsing and execution.
    MOVE_COMMANDS = {
        "go up":       ("up", 30),
        "go down":     ("down", 30),
        "go left":     ("left", 30),
        "go right":    ("right", 30),
        "go forward":  ("forward", 30),
        "go back":     ("back", 30),
        "come closer": ("forward", 50),
        "go away":     ("back", 50),
    }

    def __init__(self, state: State):
        self.state = state
        self._last_command_time: float = 0.0
        self._last_command: str = ""

    def handle(
        self,
        command: str,
        drone: BaseDrone,
        tracked_heads: list[TrackedHead],
        timestamp: float | None = None,
    ) -> None:
        """Process a single recognized voice command.

        Parameters
        ----------
        command:
            The normalized text from Vosk (e.g. ``"go left"``).
        drone:
            The drone interface.
        tracked_heads:
            Current tracked heads (needed for ``follow me``).
        timestamp:
            Current time — defaults to ``time()`` if not provided.
        """
        now = timestamp if timestamp is not None else time()

        # Cooldown — ignore if same command repeated too fast
        if command == self._last_command and (now - self._last_command_time) < self.COMMAND_COOLDOWN_SECONDS:
            return

        self._last_command = command
        self._last_command_time = now
        self.state.last_voice_command = command

        # ------------------------------------------------------------------
        # Command dispatch
        # ------------------------------------------------------------------

        if command == "take off":
            self._handle_takeoff(drone)

        elif command == "land":
            self._handle_land(drone)

        elif command == "follow me":
            self._handle_follow(tracked_heads)

        elif command in ("stop following", "stop"):
            self._handle_stop_follow(drone)

        elif command == "flip":
            self._handle_flip(drone)

        elif command in self.MOVE_COMMANDS:
            direction, distance = self.MOVE_COMMANDS[command]
            self._handle_move(drone, direction, distance)

    # ------------------------------------------------------------------
    # Individual command handlers
    # ------------------------------------------------------------------

    def _handle_takeoff(self, drone: BaseDrone) -> None:
        if self.state.current_state == states.IDLE:
            self.state.start_takeoff()
            drone.takeoff()
            self.state.finish_takeoff()

    def _handle_land(self, drone: BaseDrone) -> None:
        if self.state.current_state in (states.FLYING, states.FOLLOWING):
            self.state.release_follow()
            self.state.start_landing()

    def _handle_follow(self, tracked_heads: list[TrackedHead]) -> None:
        if self.state.current_state != states.FLYING:
            return
        # Pick the first head that has a gesture, or just the first head
        target = None
        for head in tracked_heads:
            if head.contain_gesture:
                target = head
                break
        if target is None and tracked_heads:
            target = tracked_heads[0]
        if target is not None:
            self.state.start_follow(target.id)

    def _handle_stop_follow(self, drone: BaseDrone) -> None:
        if self.state.is_following():
            self.state.release_follow()
            drone.send_rc_control(0, 0, 0, 0)

    def _handle_flip(self, drone: BaseDrone) -> None:
        if self.state.current_state == states.FLYING:
            drone.flip("f")

    def _handle_move(self, drone: BaseDrone, direction: str, distance: int) -> None:
        if self.state.current_state == states.FLYING:
            drone.move(direction, distance)
