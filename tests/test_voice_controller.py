from app.state import State
from app.voice_controller import VoiceController

from tests.fakes import RecordingDrone, make_head


def test_takeoff_command_runs_complete_takeoff_transition() -> None:
    state = State()
    drone = RecordingDrone()

    VoiceController(state).handle("take off", drone, [], timestamp=10.0)

    assert state.is_flying()
    assert drone.takeoff_calls == 1


def test_move_command_maps_phrase_to_direction_and_distance() -> None:
    state = State()
    state.set_flying()
    drone = RecordingDrone()

    VoiceController(state).handle("come closer", drone, [], timestamp=10.0)

    assert drone.moves == [("forward", 50)]
    assert state.last_voice_command == "come closer"


def test_repeated_voice_command_is_suppressed_during_cooldown() -> None:
    state = State()
    state.set_flying()
    drone = RecordingDrone()
    controller = VoiceController(state)

    controller.handle("go left", drone, [], timestamp=10.0)
    controller.handle("go left", drone, [], timestamp=10.5)

    assert drone.moves == [("left", 30)]


def test_follow_me_prefers_head_associated_with_gesture() -> None:
    state = State()
    state.set_flying()
    heads = [
        make_head(1, contains_gesture=False),
        make_head(2, contains_gesture=True),
    ]

    VoiceController(state).handle(
        "follow me", RecordingDrone(), heads, timestamp=10.0
    )

    assert state.is_following()
    assert state.head_target_id == 2


def test_stop_following_releases_target_and_zeroes_rc() -> None:
    state = State()
    state.set_flying()
    state.start_follow(3)
    drone = RecordingDrone()

    VoiceController(state).handle(
        "stop following", drone, [], timestamp=10.0
    )

    assert state.is_flying()
    assert state.head_target_id is None
    assert drone.rc_commands == [(0, 0, 0, 0)]


def test_land_command_enters_landing_without_landing_immediately() -> None:
    state = State()
    state.set_flying()
    drone = RecordingDrone()

    VoiceController(state).handle("land", drone, [], timestamp=10.0)

    assert state.is_landing()
    assert drone.land_calls == 0


def test_movement_is_ignored_while_idle() -> None:
    state = State()
    drone = RecordingDrone()

    VoiceController(state).handle("go right", drone, [], timestamp=10.0)

    assert drone.moves == []

