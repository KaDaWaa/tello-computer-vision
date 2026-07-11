from app.follow_controller import FollowController

from tests.fakes import RecordingDrone, make_head


FRAME_WIDTH = 640
FRAME_HEIGHT = 480


def test_pid_corrects_all_three_axes() -> None:
    controller = FollowController()
    drone = RecordingDrone()
    target = make_head(
        center=(100, 100),
        height=48,
        contains_gesture=False,
    )

    controller.update(drone, target, FRAME_WIDTH, FRAME_HEIGHT, timestamp=10.0)

    left_right, forward, up, yaw = drone.rc_commands[-1]
    assert left_right == 0
    assert forward > 0
    assert up > 0
    assert yaw < 0


def test_pid_clamps_commands_to_drone_limits() -> None:
    controller = FollowController()
    drone = RecordingDrone()
    target = make_head(
        center=(-10_000, -10_000),
        height=1,
        contains_gesture=False,
    )

    controller.update(drone, target, FRAME_WIDTH, FRAME_HEIGHT, timestamp=10.0)

    assert all(-100 <= value <= 100 for value in drone.rc_commands[-1])


def test_pid_respects_rc_send_interval() -> None:
    controller = FollowController()
    drone = RecordingDrone()

    controller.update(
        drone,
        make_head(center=(100, 240)),
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.0,
    )
    controller.update(
        drone,
        make_head(center=(500, 240)),
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.01,
    )
    assert len(drone.rc_commands) == 1

    controller.update(
        drone,
        make_head(center=(500, 240)),
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.06,
    )
    assert len(drone.rc_commands) == 2


def test_stop_sends_zero_rc_and_resets_pid() -> None:
    controller = FollowController()
    drone = RecordingDrone()

    controller.update(
        drone,
        make_head(center=(100, 100)),
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.0,
    )
    controller.stop(drone, timestamp=10.1)

    assert drone.rc_commands[-1] == (0, 0, 0, 0)

