from collections import deque
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from app.application import ApplicationCoordinator
from app.commands import AppCommand, CommandType, Direction
from app.state import State, control_mode


class FakeVoiceListener:
    def __init__(self, commands=()) -> None:
        self.commands = deque(commands)
        self.started = False
        self.stopped = False

    @property
    def is_listening(self) -> bool:
        return self.started and not self.stopped

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def poll_command(self):
        return self.commands.popleft() if self.commands else None


class FakeVisionPipeline:
    def __init__(self, control_gesture_name=None) -> None:
        self.control_gesture_name = control_gesture_name
        self.closed = False

    def process(self, frame, timestamp):
        return SimpleNamespace(
            frame=frame,
            timestamp=timestamp,
            tracked_heads=[],
            gestures=[],
            width=frame.shape[1],
            height=frame.shape[0],
            control_gesture_name=self.control_gesture_name,
        )

    def close(self) -> None:
        self.closed = True


class FakeFlightController:
    def __init__(self) -> None:
        self.handled = []
        self.follow_updates = []
        self.update_calls = 0
        self.closed = False

    def update(self) -> None:
        self.update_calls += 1

    def close(self) -> None:
        self.closed = True

    def handle(self, command, tracked_heads, timestamp):
        self.handled.append((command, tracked_heads, timestamp))
        return True

    def update_follow(
        self,
        tracked_heads,
        frame_width,
        frame_height,
        timestamp,
    ) -> None:
        self.follow_updates.append(
            (tracked_heads, frame_width, frame_height, timestamp)
        )


class FakePhotoCapture:
    def __init__(self) -> None:
        self.captures = []
        self.closed = False

    def capture(self, frame, captured_at):
        self.captures.append((frame.copy(), captured_at))
        return Path("photo.jpg")

    def close(self) -> None:
        self.closed = True


def make_application(*, voice_commands=(), gesture=None):
    state = State()
    voice = FakeVoiceListener(voice_commands)
    vision = FakeVisionPipeline(gesture)
    flight = FakeFlightController()
    photos = FakePhotoCapture()
    app = ApplicationCoordinator(
        state,
        flight,
        vision_pipeline=vision,
        voice_listener=voice,
        photo_capture=photos,
    )
    return app, state, voice, vision, flight, photos


def frame(value: int = 0):
    return np.full((4, 6, 3), value, dtype=np.uint8)


def test_application_starts_idle_in_voice_mode_with_microphone_active() -> None:
    app, state, voice, _, _, _ = make_application()

    app.start()

    assert state.is_idle()
    assert state.control_mode == control_mode.VOICE_COMMANDS
    assert state.voice_listening
    assert voice.started
    app.close()


def test_highest_priority_voice_command_executes_first() -> None:
    app, _, _, _, flight, _ = make_application(
        voice_commands=("go left", "land")
    )
    app.start()

    result = app.process_frame(frame(), timestamp=10.0)

    assert result.executed_command == AppCommand.land()
    assert [call[0] for call in flight.handled] == [AppCommand.land()]
    app.close()


def test_invalid_high_priority_command_falls_through_to_next_command() -> None:
    app, _, _, _, flight, _ = make_application(
        voice_commands=("land", "take off")
    )
    flight.handle = lambda command, tracked_heads, timestamp: (
        flight.handled.append((command, tracked_heads, timestamp))
        or command.type == CommandType.TAKE_OFF
    )
    app.start()

    result = app.process_frame(frame(), timestamp=10.0)

    assert result.executed_command == AppCommand.take_off()
    assert [call[0].type for call in flight.handled] == [
        CommandType.LAND,
        CommandType.TAKE_OFF,
    ]
    app.close()


def test_gesture_mode_ignores_voice_flight_commands_but_accepts_voice_mode() -> None:
    app, state, voice, _, flight, _ = make_application()
    app.start()
    state.set_control_mode(control_mode.GESTURES)
    voice.commands.extend(("go left", "voice mode"))

    result = app.process_frame(frame(), timestamp=10.0)

    assert result.executed_command == AppCommand.set_control_mode(
        control_mode.VOICE_COMMANDS
    )
    assert state.control_mode == control_mode.VOICE_COMMANDS
    assert flight.handled == []
    app.close()


def test_land_remains_available_by_voice_in_gesture_mode() -> None:
    app, state, voice, _, flight, _ = make_application()
    app.start()
    state.set_control_mode(control_mode.GESTURES)
    voice.commands.extend(("go right", "land"))

    app.process_frame(frame(), timestamp=10.0)

    assert [call[0] for call in flight.handled] == [AppCommand.land()]
    app.close()


def test_stable_gesture_reaches_flight_controller() -> None:
    app, state, _, _, flight, _ = make_application(gesture="fist")
    app.start()
    state.set_control_mode(control_mode.GESTURES)

    app.process_frame(frame(), timestamp=10.0)
    app.process_frame(frame(), timestamp=10.1)
    result = app.process_frame(frame(), timestamp=10.2)

    assert result.executed_command == AppCommand.start_follow()
    assert [call[0] for call in flight.handled] == [AppCommand.start_follow()]
    app.close()


def test_photo_countdown_does_not_block_flight_commands() -> None:
    app, _, voice, _, flight, photos = make_application(
        voice_commands=("take photo", "go left")
    )
    app.start()

    first = app.process_frame(frame(1), timestamp=10.0)
    before_due = app.process_frame(frame(2), timestamp=12.99)
    due = app.process_frame(frame(3), timestamp=13.0)

    assert first.photo_scheduled
    assert first.photo_seconds_remaining == 3.0
    assert first.executed_command == AppCommand.move(Direction.LEFT, 30)
    assert before_due.photo_path is None
    assert due.photo_path == Path("photo.jpg")
    assert due.photo_saved
    assert photos.captures[0][1] == 13.0
    assert np.all(photos.captures[0][0] == 3)
    assert [call[0] for call in flight.handled] == [
        AppCommand.move(Direction.LEFT, 30)
    ]
    app.close()


def test_only_one_photo_countdown_can_be_pending() -> None:
    app, _, voice, _, _, photos = make_application(
        voice_commands=("take photo", "take a photo")
    )
    app.start()

    result = app.process_frame(frame(), timestamp=10.0)
    app.process_frame(frame(), timestamp=13.0)

    assert result.photo_scheduled
    assert len(photos.captures) == 1
    app.close()


def test_follow_control_updates_every_frame() -> None:
    app, _, _, _, flight, _ = make_application()
    app.start()

    app.process_frame(frame(), timestamp=10.0)

    assert flight.follow_updates == [([], 6, 4, 10.0)]
    app.close()


def test_close_releases_input_vision_and_photo_resources() -> None:
    app, state, voice, vision, _, photos = make_application()
    app.start()

    app.close()
    app.close()

    assert voice.stopped
    assert vision.closed
    assert photos.closed
    assert not state.voice_listening


def test_blocked_command_feedback_explains_rejection() -> None:
    app, _, _, _, flight, _ = make_application(voice_commands=("go left",))
    flight.handle = lambda command, tracked_heads, timestamp: False
    flight.last_rejection_reason = "take off first"
    app.start()

    result = app.process_frame(frame(), timestamp=10.0)

    assert result.executed_command is None
    assert result.detected_input == "go left"
    assert result.command_feedback.status == "blocked"
    assert result.command_feedback.detail == "take off first"
    assert result.command_feedback.command.description == "MOVE LEFT 30 cm"
    app.close()


def test_command_feedback_remains_visible_for_two_seconds() -> None:
    app, _, _, _, _, _ = make_application(voice_commands=("take off",))
    app.start()

    first = app.process_frame(frame(), timestamp=10.0)
    visible = app.process_frame(frame(), timestamp=11.99)
    expired = app.process_frame(frame(), timestamp=12.0)

    assert first.command_feedback.status == "executed"
    assert visible.command_feedback == first.command_feedback
    assert expired.command_feedback is None
    app.close()
