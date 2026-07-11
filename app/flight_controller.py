from __future__ import annotations

from time import time

from app.commands import AppCommand, CommandType, Direction
from app.follow_controller import FollowController
from app.state import State
from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import TrackedHead


class FlightController:
    """Validate and execute flight commands from any input source."""

    ACTION_COOLDOWN_SECONDS = 0.45
    POST_FLIP_LOCK_SECONDS = 3.0

    FLIGHT_COMMANDS = {
        CommandType.TAKE_OFF,
        CommandType.LAND,
        CommandType.MOVE,
        CommandType.ROTATE,
        CommandType.FLIP,
        CommandType.START_FOLLOW,
        CommandType.STOP_FOLLOW,
    }
    POST_FLIP_BLOCKED_COMMANDS = FLIGHT_COMMANDS - {CommandType.LAND}
    COOLDOWN_EXEMPT_COMMANDS = {
        CommandType.LAND,
        CommandType.STOP_FOLLOW,
    }
    FLIP_DIRECTIONS = {
        Direction.FORWARD: "f",
        Direction.BACK: "b",
        Direction.LEFT: "l",
        Direction.RIGHT: "r",
    }

    def __init__(
        self,
        state: State,
        drone: BaseDrone,
        follow_controller: FollowController | None = None,
        action_cooldown_seconds: float = ACTION_COOLDOWN_SECONDS,
        post_flip_lock_seconds: float = POST_FLIP_LOCK_SECONDS,
    ) -> None:
        if action_cooldown_seconds < 0:
            raise ValueError("action_cooldown_seconds cannot be negative")
        if post_flip_lock_seconds < 0:
            raise ValueError("post_flip_lock_seconds cannot be negative")

        self.state = state
        self.drone = drone
        self.follow_controller = follow_controller or FollowController()
        self.action_cooldown_seconds = action_cooldown_seconds
        self.post_flip_lock_seconds = post_flip_lock_seconds
        self._next_action_allowed_timestamp = float("-inf")
        self._flight_actions_locked_until = float("-inf")
        self.last_rejection_reason: str | None = None

    def handle(
        self,
        command: AppCommand,
        tracked_heads: list[TrackedHead],
        timestamp: float | None = None,
    ) -> bool:
        """Execute a flight command and report whether it was accepted."""

        self.last_rejection_reason = None
        if command.type not in self.FLIGHT_COMMANDS:
            raise ValueError(
                f"{command.type.value} is an application command, not a flight command"
            )

        now = timestamp if timestamp is not None else time()
        if self._is_post_flip_locked(command, now):
            self.last_rejection_reason = "flip recovery in progress"
            return False
        if self._is_action_cooldown_locked(command, now):
            self.last_rejection_reason = "command cooldown"
            return False

        executed = self._dispatch(command, tracked_heads, now)
        if executed:
            self._next_action_allowed_timestamp = (
                now + self.action_cooldown_seconds
            )
        return executed

    def update_follow(
        self,
        tracked_heads: list[TrackedHead],
        frame_width: int,
        frame_height: int,
        timestamp: float | None = None,
    ) -> None:
        if not self.state.is_following():
            return

        now = timestamp if timestamp is not None else time()
        target = self._find_head(self.state.head_target_id, tracked_heads)
        if target is None:
            self.follow_controller.stop(self.drone, now)
            self.state.release_follow()
            return

        self.follow_controller.update(
            self.drone,
            target,
            frame_width,
            frame_height,
            now,
        )

    def _dispatch(
        self,
        command: AppCommand,
        tracked_heads: list[TrackedHead],
        now: float,
    ) -> bool:
        if command.type == CommandType.TAKE_OFF:
            if not self.state.is_idle():
                return self._reject("drone is not idle")
            self.state.start_takeoff()
            self.drone.takeoff()
            self.state.finish_takeoff()
            return True

        if command.type == CommandType.LAND:
            if not (self.state.is_flying() or self.state.is_following()):
                return self._reject("drone is not airborne")
            if self.state.is_following():
                self.follow_controller.stop(self.drone, now)
                self.state.release_follow()
            self.state.start_landing()
            self.drone.land()
            self.state.set_idle()
            return True

        if command.type == CommandType.START_FOLLOW:
            if not self.state.is_flying():
                return self._reject(self._flight_state_rejection())
            target = self._select_follow_target(tracked_heads)
            if target is None:
                return self._reject("no tracked target")
            self.follow_controller.reset()
            self.state.start_follow(target.id)
            return True

        if command.type == CommandType.STOP_FOLLOW:
            if not self.state.is_following():
                return self._reject("drone is not following")
            self.follow_controller.stop(self.drone, now)
            self.state.release_follow()
            return True

        if not self.state.is_flying():
            return self._reject(self._flight_state_rejection())

        if command.type == CommandType.MOVE:
            self.drone.move(command.direction.value, command.amount)
            return True

        if command.type == CommandType.ROTATE:
            angle = command.amount
            if command.direction == Direction.LEFT:
                angle = -angle
            self.drone.rotate(angle)
            return True

        if command.type == CommandType.FLIP:
            self.follow_controller.stop(self.drone, now)
            self.drone.flip(self.FLIP_DIRECTIONS[command.direction])
            self._flight_actions_locked_until = now + self.post_flip_lock_seconds
            return True

        return False

    def _reject(self, reason: str) -> bool:
        self.last_rejection_reason = reason
        return False

    def _flight_state_rejection(self) -> str:
        if self.state.is_idle():
            return "take off first"
        return f"unavailable while {self.state.current_state.value}"

    def _is_post_flip_locked(
        self,
        command: AppCommand,
        now: float,
    ) -> bool:
        return (
            command.type in self.POST_FLIP_BLOCKED_COMMANDS
            and now < self._flight_actions_locked_until
        )

    def _is_action_cooldown_locked(
        self,
        command: AppCommand,
        now: float,
    ) -> bool:
        return (
            command.type not in self.COOLDOWN_EXEMPT_COMMANDS
            and now < self._next_action_allowed_timestamp
        )

    @staticmethod
    def _find_head(
        target_id: int | None,
        tracked_heads: list[TrackedHead],
    ) -> TrackedHead | None:
        return next(
            (head for head in tracked_heads if head.id == target_id),
            None,
        )

    @staticmethod
    def _select_follow_target(
        tracked_heads: list[TrackedHead],
    ) -> TrackedHead | None:
        return next(
            (head for head in tracked_heads if head.contain_gesture),
            tracked_heads[0] if tracked_heads else None,
        )
