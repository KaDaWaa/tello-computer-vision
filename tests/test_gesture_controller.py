from app.controller import FollowController
from app.state import State

from tests.fakes import RecordingDrone, make_gesture, make_head


FRAME_WIDTH = 640
FRAME_HEIGHT = 480


def update_three_frames(
    controller: FollowController,
    drone: RecordingDrone,
    head,
    gesture_name: str,
    start: float = 10.0,
) -> None:
    for offset in (0.0, 0.1, 0.2):
        controller.update(
            drone,
            [head],
            [make_gesture(gesture_name)],
            FRAME_WIDTH,
            FRAME_HEIGHT,
            timestamp=start + offset,
        )


def flying_controller() -> tuple[State, FollowController, RecordingDrone]:
    state = State()
    state.set_flying()
    return state, FollowController(state), RecordingDrone()


def test_gesture_requires_three_stable_frames() -> None:
    state, controller, drone = flying_controller()
    head = make_head()

    for timestamp in (10.0, 10.1):
        controller.update(
            drone,
            [head],
            [make_gesture("fist")],
            FRAME_WIDTH,
            FRAME_HEIGHT,
            timestamp=timestamp,
        )

    assert state.is_flying()

    controller.update(
        drone,
        [head],
        [make_gesture("fist")],
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.2,
    )
    assert state.is_following()
    assert state.head_target_id == head.id


def test_stop_gesture_releases_follow_and_stops_rc() -> None:
    state, controller, drone = flying_controller()
    head = make_head()
    state.start_follow(head.id)

    update_three_frames(controller, drone, head, "stop")

    assert state.is_flying()
    assert state.head_target_id is None
    assert drone.rc_commands[-1] == (0, 0, 0, 0)


def test_land_gesture_enters_landing_state() -> None:
    state, controller, drone = flying_controller()

    update_three_frames(controller, drone, make_head(), "call")

    assert state.is_landing()
    assert drone.rc_commands[-1] == (0, 0, 0, 0)


def test_move_gesture_executes_once_during_action_lock() -> None:
    _, controller, drone = flying_controller()
    head = make_head()

    update_three_frames(controller, drone, head, "like")
    update_three_frames(controller, drone, head, "like", start=10.4)

    assert drone.moves == [("up", 30)]


def test_flip_gesture_executes_forward_flip() -> None:
    _, controller, drone = flying_controller()

    update_three_frames(controller, drone, make_head(), "grip")

    assert drone.flips == ["f"]


def test_losing_follow_target_releases_follow_and_stops_rc() -> None:
    state, controller, drone = flying_controller()
    state.start_follow(4)

    controller.update(
        drone,
        [],
        [],
        FRAME_WIDTH,
        FRAME_HEIGHT,
        timestamp=10.0,
    )

    assert state.is_flying()
    assert state.head_target_id is None
    assert drone.rc_commands == [(0, 0, 0, 0)]

