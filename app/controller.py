from __future__ import annotations

from dataclasses import dataclass
from time import time

from app.state import State, states
from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import TrackedHead
from core.vision.hand_gestures.gesture_result import GestureDetection


def _normalized_gesture_name(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().lower().replace(" ", "_")


@dataclass
class _PID:
    kp: float
    ki: float
    kd: float
    integral: float = 0.0
    previous_error: float = 0.0

    def update(self, error: float, dt: float) -> float:
        if dt <= 0:
            dt = 1e-3
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt
        self.previous_error = error
        return (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)


class FollowController:
    CLOSED_FIST_GESTURES = {"closed_fist", "closedfist", "fist"}
    OPEN_HAND_GESTURES = {"open_palm", "open_hand", "openhand", "palm"}
    FLIP_GESTURES: set[str] = set()
    LAND_GESTURES = {"victory", "peace", "v_sign", "v_sign_hand", "v_sign_gesture"}
    MOVE_GESTURES = {
        "thumb_up": ("up", 30),
        "thumbs_up": ("up", 30),
        "thumb_down": ("down", 30),
        "thumbs_down": ("down", 30),
        "pointing_up": ("forward", 30),
        "point_up": ("forward", 30),
        "pointing_down": ("back", 30),
        "point_down": ("back", 30),
        "pointing_left": ("left", 30),
        "point_left": ("left", 30),
        "pointing_right": ("right", 30),
        "point_right": ("right", 30),
    }
    TRANSITION_COOLDOWN_SECONDS = 0.45
    REQUIRED_STABLE_FRAMES = 3
    FOLLOW_RC_INTERVAL_SECONDS = 0.05
    RC_DEADBAND = 0
    TARGET_HEAD_HEIGHT_RATIO = 0.18
    ONE_SHOT_MOVE_LOCK_SECONDS = 1.2
    ONE_SHOT_FLIP_LOCK_SECONDS = 5

    def __init__(self, state: State | None = None):
        self.state = state or State()
        self._yaw_pid = _PID(kp=1.6, ki=0.0, kd=0.02)
        self._forward_pid = _PID(kp=1.6, ki=0.0, kd=0.02)
        self._height_pid = _PID(kp=1.6, ki=0.0, kd=0.02)
        self._last_timestamp = None
        self._last_transition_timestamp = 0.0
        self._stable_gesture_name = ""
        self._stable_gesture_frames = 0
        self._consumed_stable_gesture_name = ""
        self._last_rc_sent_timestamp = 0.0
        self._last_rc_command = (0, 0, 0, 0)
        self._one_shot_action_locked_until = 0.0

    def update(
        self,
        drone: BaseDrone,
        tracked_heads: list[TrackedHead],
        gesture_detections: list[GestureDetection],
        frame_width: int,
        frame_height: int,
        timestamp: float | None = None,
    ) -> State:
        now = timestamp if timestamp is not None else time()
        dt = 0.0 if self._last_timestamp is None else now - self._last_timestamp
        self._last_timestamp = now

        target_head = self._get_target_head(tracked_heads)
        if self.state.is_following() and target_head is None:
            self.state.release_follow()
            self._register_transition(now)
            self._send_rc_control(drone, 0, 0, 0, 0, now, force=True)
            return self.state

        gesture_name = self._gesture_name_in_target_zone(target_head, gesture_detections)
        if gesture_name == self._stable_gesture_name and gesture_name:
            self._stable_gesture_frames += 1
        else:
            self._stable_gesture_name = gesture_name
            self._stable_gesture_frames = 1 if gesture_name else 0

        if self._transition_locked(now):
            if self.state.is_following() and target_head is not None:
                self._follow_target(drone, target_head, frame_width, frame_height, dt, now)
            return self.state

        if self.state.current_state == states.FLYING and self._one_shot_action_locked(now):
            return self.state

        if self.state.current_state in (states.FLYING, states.FOLLOWING):
            if self._gesture_ready(self.LAND_GESTURES, gesture_name):
                self.state.release_follow()
                self._register_transition(now)
                self._send_rc_control(drone, 0, 0, 0, 0, now, force=True)
                self.state.start_landing()
                return self.state

            if self._gesture_ready(self.OPEN_HAND_GESTURES, gesture_name):
                self.state.release_follow()
                self._register_transition(now)
                self._send_rc_control(drone, 0, 0, 0, 0, now, force=True)
                return self.state

            if target_head is not None and self.state.is_following():
                self._follow_target(drone, target_head, frame_width, frame_height, dt, now)
                return self.state

        if target_head is not None and self._gesture_ready(self.CLOSED_FIST_GESTURES, gesture_name) and self.state.current_state == states.FLYING:
            self.state.start_follow(target_head.id)
            self._register_transition(now)
            return self.state

        if target_head is not None and self.state.current_state == states.FLYING:
            if self._gesture_ready(set(self.MOVE_GESTURES.keys()), gesture_name) and not self._gesture_consumed(gesture_name):
                direction, distance = self.MOVE_GESTURES[gesture_name]
                drone.move(direction, distance)
                self._consume_gesture(gesture_name)
                self._register_transition(now)
                self._lock_one_shot_action(now, self.ONE_SHOT_MOVE_LOCK_SECONDS)
                return self.state

            if self._gesture_ready(self.FLIP_GESTURES, gesture_name) and not self._gesture_consumed(gesture_name):
                drone.flip("f")
                self._consume_gesture(gesture_name)
                self._register_transition(now)
                self._lock_one_shot_action(now, self.ONE_SHOT_FLIP_LOCK_SECONDS)
                return self.state

        return self.state

    def _get_target_head(self, tracked_heads: list[TrackedHead]) -> TrackedHead | None:
        if self.state.head_target_id is not None:
            for head in tracked_heads:
                if head.id == self.state.head_target_id:
                    return head

        for head in tracked_heads:
            if head.contain_gesture:
                return head

        return None

    def _gesture_name_in_target_zone(
        self,
        target_head: TrackedHead | None,
        gesture_detections: list[GestureDetection],
    ) -> str:
        if target_head is None or not target_head.contain_gesture:
            return ""

        for detection in gesture_detections:
            normalized = _normalized_gesture_name(detection.gesture_name)
            if normalized in self.LAND_GESTURES | self.CLOSED_FIST_GESTURES | self.OPEN_HAND_GESTURES | set(self.MOVE_GESTURES.keys()) | self.FLIP_GESTURES:
                return normalized

        return ""

    def _gesture_ready(self, accepted_gestures: set[str], gesture_name: str) -> bool:
        return gesture_name in accepted_gestures and self._stable_gesture_frames >= self.REQUIRED_STABLE_FRAMES

    def _transition_locked(self, now: float) -> bool:
        return (now - self._last_transition_timestamp) < self.TRANSITION_COOLDOWN_SECONDS

    def _register_transition(self, now: float) -> None:
        self._last_transition_timestamp = now
        self._stable_gesture_name = ""
        self._stable_gesture_frames = 0
        self._consumed_stable_gesture_name = ""

    def _gesture_consumed(self, gesture_name: str) -> bool:
        return gesture_name == self._consumed_stable_gesture_name

    def _consume_gesture(self, gesture_name: str) -> None:
        self._consumed_stable_gesture_name = gesture_name

    def _one_shot_action_locked(self, now: float) -> bool:
        return now < self._one_shot_action_locked_until

    def _lock_one_shot_action(self, now: float, duration: float) -> None:
        self._one_shot_action_locked_until = max(self._one_shot_action_locked_until, now + duration)

    def _follow_target(self, drone: BaseDrone, target_head: TrackedHead, frame_width: int, frame_height: int, dt: float, now: float):
        center_x, center_y = target_head.center
        error_x = (frame_width / 2) - center_x
        error_y = (frame_height / 2) - center_y
        head_height_ratio = target_head.bbox.height / max(frame_height, 1)
        distance_error = self.TARGET_HEAD_HEIGHT_RATIO - head_height_ratio

        yaw_command = int(self._yaw_pid.update(error_x / max(frame_width, 1), dt) * 100)
        forward_command = int(self._forward_pid.update(distance_error, dt) * 100)
        height_command = int(self._height_pid.update(error_y / max(frame_height, 1), dt) * 100)

        yaw_command = max(-100, min(100, -yaw_command))  # Negate for correct rotation direction
        forward_command = max(-100, min(100, forward_command))
        height_command = max(-100, min(100, height_command))

        self._send_rc_control(drone, 0, forward_command, height_command, yaw_command, now)

    def _send_rc_control(self, drone: BaseDrone, left_right: int, forward_backward: int, up_down: int, yaw: int, now: float, force: bool = False) -> None:
        command = (
            self._apply_deadband(left_right),
            self._apply_deadband(forward_backward),
            self._apply_deadband(up_down),
            self._apply_deadband(yaw),
        )

        if not force:
            if command == self._last_rc_command and (now - self._last_rc_sent_timestamp) < self.FOLLOW_RC_INTERVAL_SECONDS:
                return

            if command == self._last_rc_command and command == (0, 0, 0, 0):
                return

            if (now - self._last_rc_sent_timestamp) < self.FOLLOW_RC_INTERVAL_SECONDS:
                return

        self._last_rc_command = command
        self._last_rc_sent_timestamp = now
        drone.send_rc_control(*command)

    def _apply_deadband(self, value: int) -> int:
        return 0 if abs(value) < self.RC_DEADBAND else value