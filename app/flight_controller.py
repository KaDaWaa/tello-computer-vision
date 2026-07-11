from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from time import time
from typing import Callable

from app.commands import AppCommand, CommandType, Direction
from app.follow_controller import FollowController
from app.state import State
from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import TrackedHead


class FlightController:
    """Validate and execute flight commands from any input source."""

    ACTION_COOLDOWN_SECONDS = 0.45
    POST_FLIP_LOCK_SECONDS = 1.25

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
        self._action_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="flight-action",
        )
        self._pending_action: Future[None] | None = None
        self._pending_command: CommandType | None = None
        self._closed = False
        self.last_rejection_reason: str | None = None
        self.last_action_error: str | None = None

    @property
    def has_pending_action(self) -> bool:
        return self._pending_action is not None

    def update(self, timestamp: float | None = None) -> None:
        """Apply a completed blocking flight action on the main thread."""
        if self._pending_action is None or not self._pending_action.done():
            return
        self._finish_pending_action(timestamp)

    def wait_for_pending_action(self, timestamp: float | None = None) -> None:
        """Wait for an in-flight SDK command and apply its state transition."""
        if self._pending_action is None:
            return
        self._finish_pending_action(timestamp)

    def close(self) -> None:
        if self._closed:
            return
        self.wait_for_pending_action()
        self._action_executor.shutdown(wait=True, cancel_futures=False)
        self._closed = True

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
        if self.has_pending_action and command.type != CommandType.LAND:
            return self._reject("flight action in progress")

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
            self._submit_action(command.type, self.drone.takeoff)
            return True

        if command.type == CommandType.LAND:
            if not (self.state.is_flying() or self.state.is_following()):
                return self._reject("drone is not airborne")
            if self.state.is_following():
                self.follow_controller.stop(self.drone, now)
                self.state.release_follow()
            self.state.start_landing()
            self._submit_action(command.type, self.drone.land)
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
            self._submit_action(
                command.type,
                lambda: self.drone.move(
                    command.direction.value,
                    command.amount,
                ),
            )
            return True

        if command.type == CommandType.ROTATE:
            angle = command.amount
            if command.direction == Direction.LEFT:
                angle = -angle
            self._submit_action(
                command.type,
                lambda: self.drone.rotate(angle),
            )
            return True

        if command.type == CommandType.FLIP:
            self.follow_controller.stop(self.drone, now)
            sdk_direction = self.FLIP_DIRECTIONS[command.direction]
            self._submit_action(
                command.type,
                lambda: self.drone.flip(sdk_direction),
            )
            return True

        return False

    def _submit_action(
        self,
        command: CommandType,
        action: Callable[[], None],
    ) -> None:
        self.last_action_error = None
        self._pending_command = command
        self._pending_action = self._action_executor.submit(action)

    def _finish_pending_action(self, timestamp: float | None = None) -> None:
        future = self._pending_action
        command = self._pending_command
        if future is None or command is None:
            return

        try:
            future.result()
        except Exception as exc:
            self._complete_failed_action(command, exc)
        else:
            completed_at = timestamp if timestamp is not None else time()
            self._complete_successful_action(command, completed_at)

        self._pending_action = None
        self._pending_command = None

    def _complete_successful_action(
        self,
        command: CommandType,
        completed_at: float,
    ) -> None:
        if command == CommandType.TAKE_OFF:
            self.state.finish_takeoff()
        elif command == CommandType.LAND:
            self.state.set_idle()
        elif command == CommandType.FLIP:
            self._flight_actions_locked_until = (
                completed_at + self.post_flip_lock_seconds
            )

    def _complete_failed_action(
        self,
        command: CommandType,
        error: Exception,
    ) -> None:
        self.last_action_error = str(error)
        if command == CommandType.TAKE_OFF:
            self.state.cancel_takeoff()
        elif command == CommandType.LAND:
            # Conservatively assume the drone may still be airborne.
            self.state.set_flying()

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
