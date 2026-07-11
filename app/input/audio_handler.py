from __future__ import annotations

from app.commands import AppCommand, Direction
from app.state import control_mode


class AudioHandler:
    """Translate finalized speech-recognition text into application commands.

    Recognition, command priority, application state, and execution timing are
    intentionally outside this class. Repeated phrases therefore produce
    repeated commands; the coordinator and flight controller decide what can
    execute.
    """

    COMMANDS_BY_PHRASE = {
        "take off": AppCommand.take_off(),
        "land": AppCommand.land(),
        "follow me": AppCommand.start_follow(),
        "stop": AppCommand.stop_follow(),
        "stop following": AppCommand.stop_follow(),
        "go up": AppCommand.move(Direction.UP, 30),
        "go down": AppCommand.move(Direction.DOWN, 30),
        "go left": AppCommand.move(Direction.LEFT, 30),
        "go right": AppCommand.move(Direction.RIGHT, 30),
        "go forward": AppCommand.move(Direction.FORWARD, 30),
        "go back": AppCommand.move(Direction.BACK, 30),
        "come closer": AppCommand.move(Direction.FORWARD, 50),
        "go away": AppCommand.move(Direction.BACK, 50),
        "rotate left": AppCommand.rotate(Direction.LEFT, 90),
        "rotate right": AppCommand.rotate(Direction.RIGHT, 90),
        "flip": AppCommand.flip(Direction.FORWARD),
        "flip forward": AppCommand.flip(Direction.FORWARD),
        "flip back": AppCommand.flip(Direction.BACK),
        "flip left": AppCommand.flip(Direction.LEFT),
        "flip right": AppCommand.flip(Direction.RIGHT),
        "take photo": AppCommand.take_photo(delay_seconds=3),
        "take a photo": AppCommand.take_photo(delay_seconds=3),
        "gesture mode": AppCommand.set_control_mode(control_mode.GESTURES),
        "voice mode": AppCommand.set_control_mode(control_mode.VOICE_COMMANDS),
    }

    def handle(self, recognized_text: str | None) -> AppCommand | None:
        normalized_text = self.normalize_text(recognized_text)
        return self.COMMANDS_BY_PHRASE.get(normalized_text)

    @classmethod
    def supported_phrases(cls) -> tuple[str, ...]:
        return tuple(cls.COMMANDS_BY_PHRASE)

    @staticmethod
    def normalize_text(text: str | None) -> str:
        if not text:
            return ""
        return " ".join(text.strip().lower().split())

