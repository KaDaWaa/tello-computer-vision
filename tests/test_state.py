from app.state import State, control_mode, states


def test_takeoff_lifecycle_reaches_flying() -> None:
    state = State()

    state.start_takeoff()
    assert state.current_state == states.TAKING_OFF

    state.finish_takeoff()
    assert state.current_state == states.FLYING


def test_takeoff_is_ignored_when_not_idle() -> None:
    state = State()
    state.set_flying()

    state.start_takeoff()

    assert state.current_state == states.FLYING


def test_follow_can_only_start_while_flying() -> None:
    state = State()

    state.start_follow(7)
    assert state.is_idle()
    assert state.head_target_id is None

    state.set_flying()
    state.start_follow(7)
    assert state.is_following()
    assert state.head_target_id == 7


def test_releasing_follow_returns_to_flying_and_clears_target() -> None:
    state = State()
    state.set_flying()
    state.start_follow(7)

    state.release_follow()

    assert state.is_flying()
    assert state.head_target_id is None


def test_landing_lifecycle_clears_follow_target() -> None:
    state = State()
    state.set_flying()
    state.start_follow(7)

    state.start_landing()
    assert state.is_landing()
    assert state.head_target_id is None

    state.set_idle()
    assert state.is_idle()


def test_control_mode_can_change_while_following() -> None:
    state = State()

    state.toggle_mode()
    assert state.control_mode == control_mode.VOICE_COMMANDS

    state.set_flying()
    state.start_follow(1)
    state.toggle_mode()
    assert state.control_mode == control_mode.GESTURES

    state.toggle_mode()
    assert state.control_mode == control_mode.VOICE_COMMANDS


def test_control_mode_cannot_change_during_takeoff_or_landing() -> None:
    state = State()
    state.start_takeoff()

    assert not state.set_control_mode(control_mode.VOICE_COMMANDS)
    assert state.control_mode == control_mode.GESTURES

    state.finish_takeoff()
    state.start_landing()
    assert not state.set_control_mode(control_mode.VOICE_COMMANDS)
