import pytest

from app.commands import AppCommand, Direction
from app.input.gesture_handler import GestureHandler
from app.state import control_mode


def recognize(handler: GestureHandler, name: str):
    results = [handler.handle(name) for _ in range(3)]
    assert results[:2] == [None, None]
    return results[2]


@pytest.mark.parametrize(
    ("gesture_name", "expected_command"),
    [
        ("like", AppCommand.move(Direction.UP, 30)),
        ("dislike", AppCommand.move(Direction.DOWN, 30)),
        ("fist", AppCommand.start_follow()),
        ("stop", AppCommand.stop_follow()),
        ("ok", AppCommand.land()),
        ("grip", AppCommand.take_photo(3)),
        ("one", AppCommand.move(Direction.LEFT, 30)),
        ("peace", AppCommand.move(Direction.RIGHT, 30)),
        ("three2", AppCommand.rotate(Direction.LEFT, 90)),
        ("four", AppCommand.rotate(Direction.RIGHT, 90)),
        (
            "call",
            AppCommand.set_control_mode(control_mode.VOICE_COMMANDS),
        ),
        ("rock", AppCommand.flip(Direction.FORWARD)),
    ],
)
def test_custom_model_gesture_mapping(gesture_name, expected_command) -> None:
    assert recognize(GestureHandler(), gesture_name) == expected_command


def test_gesture_must_be_stable_for_three_frames() -> None:
    handler = GestureHandler()

    assert handler.handle("fist") is None
    assert handler.handle("fist") is None
    assert handler.handle("fist") == AppCommand.start_follow()


def test_held_gesture_only_emits_once() -> None:
    handler = GestureHandler()

    assert recognize(handler, "like") == AppCommand.move(Direction.UP, 30)
    assert handler.handle("like") is None
    assert handler.handle("like") is None


def test_gesture_can_emit_again_after_it_disappears() -> None:
    handler = GestureHandler()
    assert recognize(handler, "grip") == AppCommand.take_photo(3)

    assert handler.handle(None) is None

    assert recognize(handler, "grip") == AppCommand.take_photo(3)


def test_unknown_gesture_resets_stability() -> None:
    handler = GestureHandler()

    assert handler.handle("fist") is None
    assert handler.handle("unknown") is None
    assert handler.handle("fist") is None
    assert handler.handle("fist") is None
    assert handler.handle("fist") == AppCommand.start_follow()


def test_different_stable_gestures_have_no_handler_action_cooldown() -> None:
    handler = GestureHandler()
    assert recognize(handler, "like") == AppCommand.move(Direction.UP, 30)
    assert recognize(handler, "dislike") == AppCommand.move(
        Direction.DOWN, 30
    )


def test_flip_can_emit_again_after_gesture_is_released() -> None:
    handler = GestureHandler()
    assert recognize(handler, "rock") == AppCommand.flip(Direction.FORWARD)

    handler.handle(None)

    assert recognize(handler, "rock") == AppCommand.flip(Direction.FORWARD)


def test_normalization_accepts_model_label_format_variations() -> None:
    handler = GestureHandler()

    assert recognize(handler, "  THREE2  ") == AppCommand.rotate(
        Direction.LEFT, 90
    )


def test_reset_discards_partial_stability() -> None:
    handler = GestureHandler()
    handler.handle("call")
    handler.handle("call")

    handler.reset()

    assert handler.handle("call") is None


def test_invalid_handler_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        GestureHandler(required_stable_frames=0)
