import pytest

from app.commands import AppCommand, Direction
from app.flight_controller import FlightController
from app.state import State

from tests.fakes import RecordingDrone, make_head


def make_controller(*, flying: bool = False):
    state = State()
    if flying:
        state.set_flying()
    drone = RecordingDrone()
    controller = FlightController(state, drone)
    return state, drone, controller


def test_takeoff_executes_only_from_idle() -> None:
    state, drone, controller = make_controller()

    assert controller.handle(AppCommand.take_off(), [], timestamp=10.0)
    assert state.is_flying()
    assert drone.takeoff_calls == 1
    assert not controller.handle(AppCommand.take_off(), [], timestamp=11.0)


def test_move_executes_only_while_flying() -> None:
    _, drone, controller = make_controller()
    command = AppCommand.move(Direction.LEFT, 30)

    assert not controller.handle(command, [], timestamp=10.0)
    assert drone.moves == []
    assert controller.last_rejection_reason == "take off first"

    controller.state.set_flying()
    assert controller.handle(command, [], timestamp=11.0)
    assert drone.moves == [("left", 30)]


@pytest.mark.parametrize(
    ("direction", "expected_angle"),
    [(Direction.LEFT, -90), (Direction.RIGHT, 90)],
)
def test_rotation_converts_direction_to_signed_angle(
    direction: Direction,
    expected_angle: int,
) -> None:
    _, drone, controller = make_controller(flying=True)

    assert controller.handle(
        AppCommand.rotate(direction, 90), [], timestamp=10.0
    )
    assert drone.rotations == [expected_angle]


@pytest.mark.parametrize(
    ("direction", "sdk_direction"),
    [
        (Direction.FORWARD, "f"),
        (Direction.BACK, "b"),
        (Direction.LEFT, "l"),
        (Direction.RIGHT, "r"),
    ],
)
def test_flip_converts_direction_to_tello_sdk_code(
    direction: Direction,
    sdk_direction: str,
) -> None:
    _, drone, controller = make_controller(flying=True)

    assert controller.handle(AppCommand.flip(direction), [], timestamp=10.0)
    assert drone.flips == [sdk_direction]


def test_post_flip_lock_blocks_flight_actions_for_three_seconds() -> None:
    _, drone, controller = make_controller(flying=True)
    move = AppCommand.move(Direction.UP, 30)

    assert controller.handle(AppCommand.flip(), [], timestamp=10.0)
    assert not controller.handle(move, [], timestamp=12.99)
    assert drone.moves == []
    assert controller.last_rejection_reason == "flip recovery in progress"

    assert controller.handle(move, [], timestamp=13.0)
    assert drone.moves == [("up", 30)]


def test_land_bypasses_post_flip_lock() -> None:
    state, drone, controller = make_controller(flying=True)

    assert controller.handle(AppCommand.flip(), [], timestamp=10.0)
    assert controller.handle(AppCommand.land(), [], timestamp=10.1)

    assert state.is_idle()
    assert drone.land_calls == 1


def test_action_cooldown_is_centralized_in_flight_controller() -> None:
    _, drone, controller = make_controller(flying=True)

    assert controller.handle(
        AppCommand.move(Direction.LEFT), [], timestamp=10.0
    )
    assert not controller.handle(
        AppCommand.move(Direction.RIGHT), [], timestamp=10.2
    )
    assert controller.handle(
        AppCommand.move(Direction.RIGHT), [], timestamp=10.45
    )
    assert drone.moves == [("left", 30), ("right", 30)]


def test_follow_target_selection_is_owned_by_flight_controller() -> None:
    state, _, controller = make_controller(flying=True)
    heads = [
        make_head(1, contains_gesture=False),
        make_head(2, contains_gesture=True),
    ]

    assert controller.handle(AppCommand.start_follow(), heads, timestamp=10.0)
    assert state.is_following()
    assert state.head_target_id == 2


def test_follow_updates_pid_regardless_of_input_source() -> None:
    state, drone, controller = make_controller(flying=True)
    target = make_head(1, center=(100, 100), height=48)
    controller.handle(AppCommand.start_follow(), [target], timestamp=10.0)

    controller.update_follow(
        [target],
        frame_width=640,
        frame_height=480,
        timestamp=10.1,
    )

    assert state.is_following()
    assert drone.rc_commands[-1] != (0, 0, 0, 0)


def test_losing_follow_target_stops_rc_and_returns_to_flying() -> None:
    state, drone, controller = make_controller(flying=True)
    target = make_head(1)
    controller.handle(AppCommand.start_follow(), [target], timestamp=10.0)

    controller.update_follow([], 640, 480, timestamp=10.1)

    assert state.is_flying()
    assert state.head_target_id is None
    assert drone.rc_commands[-1] == (0, 0, 0, 0)


def test_stop_following_zeroes_rc() -> None:
    state, drone, controller = make_controller(flying=True)
    target = make_head(1)
    controller.handle(AppCommand.start_follow(), [target], timestamp=10.0)

    assert controller.handle(
        AppCommand.stop_follow(), [target], timestamp=10.1
    )
    assert state.is_flying()
    assert drone.rc_commands[-1] == (0, 0, 0, 0)


def test_application_commands_are_rejected_by_flight_controller() -> None:
    _, _, controller = make_controller(flying=True)

    with pytest.raises(ValueError):
        controller.handle(AppCommand.take_photo(), [], timestamp=10.0)
