from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Protocol

import numpy as np

from app.commands import AppCommand, CommandType
from app.flight_controller import FlightController
from app.input.audio_handler import AudioHandler
from app.input.gesture_handler import GestureHandler
from app.photo_capture import PhotoCapture
from app.pipeline.vision_pipeline import VisionFrame, VisionPipeline
from app.state import State, control_mode


class VoiceInput(Protocol):
    @property
    def is_listening(self) -> bool: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def poll_command(self) -> str | None: ...


class PhotoOutput(Protocol):
    def capture(self, frame: np.ndarray, captured_at: float) -> Path: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CommandFeedback:
    command: AppCommand
    status: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ApplicationFrame:
    vision: VisionFrame
    executed_command: AppCommand | None
    photo_scheduled: bool
    photo_path: Path | None
    detected_input: str | None
    command_feedback: CommandFeedback | None
    photo_seconds_remaining: float | None
    photo_saved: bool


class ApplicationCoordinator:
    """Connect vision and input handlers to application and flight actions."""

    def __init__(
        self,
        state: State,
        flight_controller: FlightController,
        vision_pipeline: VisionPipeline | None = None,
        voice_listener: VoiceInput | None = None,
        audio_handler: AudioHandler | None = None,
        gesture_handler: GestureHandler | None = None,
        photo_capture: PhotoOutput | None = None,
    ) -> None:
        if voice_listener is None:
            from core.voice.voice_listener import VoiceListener

            voice_listener = VoiceListener()

        self.state = state
        self.flight_controller = flight_controller
        self.vision_pipeline = vision_pipeline or VisionPipeline()
        self.voice_listener = voice_listener
        self.audio_handler = audio_handler or AudioHandler()
        self.gesture_handler = gesture_handler or GestureHandler()
        self.photo_capture = photo_capture or PhotoCapture()
        self._photo_due_at: float | None = None
        self._photo_saved_until = float("-inf")
        self._last_feedback: CommandFeedback | None = None
        self._feedback_expires_at = float("-inf")
        self._started = False
        self._closed = False


    def start(self) -> None:
        if self._closed:
            raise RuntimeError("ApplicationCoordinator is closed")
        if self._started:
            return
        self.voice_listener.start()
        self.state.voice_listening = self.voice_listener.is_listening
        self._started = True

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float | None = None,
    ) -> ApplicationFrame:
        if self._closed:
            raise RuntimeError("ApplicationCoordinator is closed")

        now = timestamp if timestamp is not None else time()
        self.flight_controller.update(now)
        vision = self.vision_pipeline.process(frame, now)
        commands, detected_input = self._collect_commands(vision)

        photo_scheduled = False
        for command in commands:
            if command.type == CommandType.TAKE_PHOTO:
                photo_scheduled = self._schedule_photo(command, now) or photo_scheduled

        executed_command, attempted_command, rejection_reason = (
            self._execute_highest_priority_command(
            commands,
            vision,
            now,
        )
        )
        self._update_feedback(
            executed_command,
            attempted_command,
            rejection_reason,
            photo_scheduled,
            now,
        )
        self.flight_controller.update_follow(
            vision.tracked_heads,
            vision.width,
            vision.height,
            now,
        )
        photo_path = self._capture_photo_if_due(vision.frame, now)
        if photo_path is not None:
            self._photo_saved_until = now + 2.0
        self.state.voice_listening = self.voice_listener.is_listening

        return ApplicationFrame(
            vision=vision,
            executed_command=executed_command,
            photo_scheduled=photo_scheduled,
            photo_path=photo_path,
            detected_input=detected_input,
            command_feedback=(
                self._last_feedback if now < self._feedback_expires_at else None
            ),
            photo_seconds_remaining=self._photo_seconds_remaining(now),
            photo_saved=now < self._photo_saved_until,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.voice_listener.stop()
        self.state.voice_listening = False
        self.vision_pipeline.close()
        self.photo_capture.close()
        self.flight_controller.close()

    def _collect_commands(
        self,
        vision: VisionFrame,
    ) -> tuple[list[AppCommand], str | None]:
        commands, detected_input = self._collect_voice_commands()

        if self.state.control_mode == control_mode.GESTURES:
            if vision.control_gesture_name:
                detected_input = vision.control_gesture_name
            gesture_command = self.gesture_handler.handle(
                vision.control_gesture_name
            )
            if gesture_command is not None:
                commands.append(gesture_command)

        return commands, detected_input

    def _collect_voice_commands(
        self,
    ) -> tuple[list[AppCommand], str | None]:
        commands = []
        detected_input = None
        while True:
            recognized_text = self.voice_listener.poll_command()
            if recognized_text is None:
                return commands, detected_input

            normalized_text = self.audio_handler.normalize_text(recognized_text)
            if normalized_text:
                self.state.last_voice_command = normalized_text
                detected_input = normalized_text

            command = self.audio_handler.handle(recognized_text)
            if command is not None and self._voice_command_is_allowed(command):
                commands.append(command)

    def _voice_command_is_allowed(self, command: AppCommand) -> bool:
        if self.state.control_mode == control_mode.VOICE_COMMANDS:
            return True
        if command.type == CommandType.LAND:
            return True
        return (
            command.type == CommandType.SET_CONTROL_MODE
            and command.mode == control_mode.VOICE_COMMANDS
        )

    def _execute_highest_priority_command(
        self,
        commands: list[AppCommand],
        vision: VisionFrame,
        now: float,
    ) -> tuple[AppCommand | None, AppCommand | None, str | None]:
        foreground_commands = sorted(
            (
                command
                for command in commands
                if command.type != CommandType.TAKE_PHOTO
            ),
            key=lambda command: command.priority,
            reverse=True,
        )

        first_rejected_command = None
        first_rejection_reason = None
        for command in foreground_commands:
            if command.type == CommandType.SET_CONTROL_MODE:
                if self._set_control_mode(command.mode):
                    return command, command, None
                if first_rejected_command is None:
                    first_rejected_command = command
                    first_rejection_reason = "mode change unavailable"
                continue
            if self.flight_controller.handle(
                command,
                vision.tracked_heads,
                now,
            ):
                return command, command, None
            if first_rejected_command is None:
                first_rejected_command = command
                first_rejection_reason = getattr(
                    self.flight_controller,
                    "last_rejection_reason",
                    None,
                ) or "command blocked"
        return None, first_rejected_command, first_rejection_reason

    def _set_control_mode(self, mode: control_mode | None) -> bool:
        if mode is None or not self.state.set_control_mode(mode):
            return False
        self.gesture_handler.reset()
        return True

    def _schedule_photo(self, command: AppCommand, now: float) -> bool:
        if self._photo_due_at is not None:
            return False
        self._photo_due_at = now + command.delay_seconds
        return True

    def _capture_photo_if_due(
        self,
        frame: np.ndarray,
        now: float,
    ) -> Path | None:
        if self._photo_due_at is None or now < self._photo_due_at:
            return None
        self._photo_due_at = None
        return self.photo_capture.capture(frame, now)

    def _update_feedback(
        self,
        executed: AppCommand | None,
        attempted: AppCommand | None,
        rejection_reason: str | None,
        photo_scheduled: bool,
        now: float,
    ) -> None:
        feedback = None
        if executed is not None:
            feedback = CommandFeedback(executed, "executed")
        elif attempted is not None:
            feedback = CommandFeedback(
                attempted,
                "blocked",
                rejection_reason or "command blocked",
            )
        elif photo_scheduled:
            feedback = CommandFeedback(AppCommand.take_photo(), "scheduled")

        if feedback is not None:
            self._last_feedback = feedback
            self._feedback_expires_at = now + 2.0

    def _photo_seconds_remaining(self, now: float) -> float | None:
        if self._photo_due_at is None:
            return None
        return max(0.0, self._photo_due_at - now)

