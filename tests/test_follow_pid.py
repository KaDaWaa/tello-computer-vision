from app.controller import FollowController
from app.state import State

from tests.fakes import RecordingDrone, make_head


FRAME_WIDTH = 640
FRAME_HEIGHT = 480


def following_controller(head_id: int = 1):
    state = State()
    state.set_flying()
    state.start_follow(head_id)
    return FollowController(state), RecordingDrone()


def test_follow_pid_corrects_all_three_axes() -> None:
    controller, drone = following_controller()
    target = make_head(
        center=(100, 100),
        height=48,
        contains_gesture=False,
    )

    controller.update(
        drone,
        [target],
        [],
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.0,
    )

    left_right, forward, up, yaw = drone.rc_commands[-1]
    assert left_right == 0
    assert forward > 0
    assert up > 0
    assert yaw < 0


def test_follow_pid_clamps_commands_to_drone_limits() -> None:
    controller, drone = following_controller()
    target = make_head(
        center=(-10_000, -10_000),
        height=1,
        contains_gesture=False,
    )

    controller.update(
        drone,
        [target],
        [],
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.0,
    )

    assert all(-100 <= value <= 100 for value in drone.rc_commands[-1])


def test_follow_pid_respects_rc_send_interval() -> None:
    controller, drone = following_controller()
    first_target = make_head(center=(100, 240), contains_gesture=False)
    second_target = make_head(center=(500, 240), contains_gesture=False)

    controller.update(
        drone, [first_target], [], FRAME_WIDTH, FRAME_HEIGHT, timestamp=10.0
    )
    controller.update(
        drone, [second_target], [], FRAME_WIDTH, FRAME_HEIGHT, timestamp=10.01
    )
    assert len(drone.rc_commands) == 1

    controller.update(
        drone, [second_target], [], FRAME_WIDTH, FRAME_HEIGHT, timestamp=10.06
    )
    assert len(drone.rc_commands) == 2

