import pytest

from app.commands import AppCommand, Direction
from app.input.audio_handler import AudioHandler
from app.state import control_mode
from core.voice.phrases import VOICE_PHRASES


@pytest.mark.parametrize(
    ("phrase", "expected_command"),
    [
        ("take off", AppCommand.take_off()),
        ("land", AppCommand.land()),
        ("follow me", AppCommand.start_follow()),
        ("stop", AppCommand.stop_follow()),
        ("stop following", AppCommand.stop_follow()),
        ("go up", AppCommand.move(Direction.UP, 30)),
        ("go down", AppCommand.move(Direction.DOWN, 30)),
        ("go left", AppCommand.move(Direction.LEFT, 30)),
        ("go right", AppCommand.move(Direction.RIGHT, 30)),
        ("go forward", AppCommand.move(Direction.FORWARD, 30)),
        ("go back", AppCommand.move(Direction.BACK, 30)),
        ("come closer", AppCommand.move(Direction.FORWARD, 50)),
        ("go away", AppCommand.move(Direction.BACK, 50)),
        ("rotate left", AppCommand.rotate(Direction.LEFT, 90)),
        ("rotate right", AppCommand.rotate(Direction.RIGHT, 90)),
        ("flip", AppCommand.flip(Direction.FORWARD)),
        ("flip forward", AppCommand.flip(Direction.FORWARD)),
        ("flip back", AppCommand.flip(Direction.BACK)),
        ("flip left", AppCommand.flip(Direction.LEFT)),
        ("flip right", AppCommand.flip(Direction.RIGHT)),
        ("take photo", AppCommand.take_photo(3)),
        ("take a photo", AppCommand.take_photo(3)),
        (
            "gesture mode",
            AppCommand.set_control_mode(control_mode.GESTURES),
        ),
        (
            "voice mode",
            AppCommand.set_control_mode(control_mode.VOICE_COMMANDS),
        ),
    ],
)
def test_voice_phrase_mapping(phrase: str, expected_command: AppCommand) -> None:
    assert AudioHandler().handle(phrase) == expected_command


def test_text_normalization_handles_case_and_extra_whitespace() -> None:
    assert AudioHandler().handle("  FLIP   LEFT ") == AppCommand.flip(
        Direction.LEFT
    )


@pytest.mark.parametrize("text", [None, "", "unknown command", "[unk]"])
def test_unrecognized_text_emits_no_command(text: str | None) -> None:
    assert AudioHandler().handle(text) is None


def test_repeated_phrase_is_not_suppressed_by_audio_handler() -> None:
    handler = AudioHandler()

    first = handler.handle("go left")
    second = handler.handle("go left")

    assert first == AppCommand.move(Direction.LEFT, 30)
    assert second == first


def test_vosk_grammar_phrases_match_handler_vocabulary() -> None:
    assert set(VOICE_PHRASES) == set(AudioHandler.supported_phrases())
