from __future__ import annotations

from dataclasses import dataclass

from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import TrackedHead


@dataclass
class _PID:
    kp: float
    ki: float
    kd: float
    integral: float = 0.0
    previous_error: float = 0.0

    def update(self, error: float, dt: float) -> float:
        safe_dt = max(dt, 1e-3)
        self.integral += error * safe_dt
        derivative = (error - self.previous_error) / safe_dt
        self.previous_error = error
        return (self.kp * error) + (self.ki * self.integral) + (
            self.kd * derivative
        )

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = 0.0


class FollowController:
    """PID-only controller for keeping one tracked head in frame."""

    RC_INTERVAL_SECONDS = 0.05
    RC_DEADBAND = 0
    TARGET_HEAD_HEIGHT_RATIO = 0.22

    def __init__(self) -> None:
        self._yaw_pid = _PID(kp=2.2, ki=0.0, kd=0.02)
        self._forward_pid = _PID(kp=2.6, ki=0.0, kd=0.04)
        self._height_pid = _PID(kp=1.6, ki=0.0, kd=0.02)
        self._last_update_timestamp: float | None = None
        self._last_rc_sent_timestamp = float("-inf")
        self._last_rc_command = (0, 0, 0, 0)

    def update(
        self,
        drone: BaseDrone,
        target: TrackedHead,
        frame_width: int,
        frame_height: int,
        timestamp: float,
    ) -> None:
        dt = (
            0.0
            if self._last_update_timestamp is None
            else timestamp - self._last_update_timestamp
        )
        self._last_update_timestamp = timestamp

        center_x, center_y = target.center
        error_x = (frame_width / 2) - center_x
        error_y = (frame_height / 2) - center_y
        head_height_ratio = target.bbox.height / max(frame_height, 1)
        distance_error = self.TARGET_HEAD_HEIGHT_RATIO - head_height_ratio

        yaw = int(
            self._yaw_pid.update(error_x / max(frame_width, 1), dt) * 100
        )
        forward = int(self._forward_pid.update(distance_error, dt) * 100)
        up = int(
            self._height_pid.update(error_y / max(frame_height, 1), dt) * 100
        )

        self._send_rc_control(
            drone,
            left_right=0,
            forward_backward=self._clamp(forward),
            up_down=self._clamp(up),
            yaw=self._clamp(-yaw),
            timestamp=timestamp,
        )

    def stop(
        self,
        drone: BaseDrone,
        timestamp: float,
        *,
        force: bool = True,
    ) -> None:
        self._send_rc_control(
            drone,
            left_right=0,
            forward_backward=0,
            up_down=0,
            yaw=0,
            timestamp=timestamp,
            force=force,
        )
        self.reset()

    def reset(self) -> None:
        self._yaw_pid.reset()
        self._forward_pid.reset()
        self._height_pid.reset()
        self._last_update_timestamp = None

    def _send_rc_control(
        self,
        drone: BaseDrone,
        left_right: int,
        forward_backward: int,
        up_down: int,
        yaw: int,
        timestamp: float,
        *,
        force: bool = False,
    ) -> None:
        command = tuple(
            self._apply_deadband(value)
            for value in (left_right, forward_backward, up_down, yaw)
        )

        if not force:
            elapsed = timestamp - self._last_rc_sent_timestamp
            if elapsed < self.RC_INTERVAL_SECONDS:
                return
            if command == self._last_rc_command == (0, 0, 0, 0):
                return

        self._last_rc_command = command
        self._last_rc_sent_timestamp = timestamp
        drone.send_rc_control(*command)

    def _apply_deadband(self, value: int) -> int:
        return 0 if abs(value) < self.RC_DEADBAND else value

    @staticmethod
    def _clamp(value: int) -> int:
        return max(-100, min(100, value))

