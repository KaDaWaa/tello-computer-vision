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
class ApplicationFrame:
    vision: VisionFrame
    executed_command: AppCommand | None
    photo_scheduled: bool
    photo_path: Path | None


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
        self._started = False
        self._closed = False

        if not self.state.set_control_mode(control_mode.VOICE_COMMANDS):
            raise ValueError("Application must be initialized in a stable state")

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
        vision = self.vision_pipeline.process(frame, now)
        commands = self._collect_commands(vision)

        photo_scheduled = False
        for command in commands:
            if command.type == CommandType.TAKE_PHOTO:
                photo_scheduled = self._schedule_photo(command, now) or photo_scheduled

        executed_command = self._execute_highest_priority_command(
            commands,
            vision,
            now,
        )
        self.flight_controller.update_follow(
            vision.tracked_heads,
            vision.width,
            vision.height,
            now,
        )
        photo_path = self._capture_photo_if_due(vision.frame, now)
        self.state.voice_listening = self.voice_listener.is_listening

        return ApplicationFrame(
            vision=vision,
            executed_command=executed_command,
            photo_scheduled=photo_scheduled,
            photo_path=photo_path,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.voice_listener.stop()
        self.state.voice_listening = False
        self.vision_pipeline.close()
        self.photo_capture.close()

    def _collect_commands(self, vision: VisionFrame) -> list[AppCommand]:
        commands = self._collect_voice_commands()

        if self.state.control_mode == control_mode.GESTURES:
            gesture_command = self.gesture_handler.handle(
                vision.control_gesture_name
            )
            if gesture_command is not None:
                commands.append(gesture_command)

        return commands

    def _collect_voice_commands(self) -> list[AppCommand]:
        commands = []
        while True:
            recognized_text = self.voice_listener.poll_command()
            if recognized_text is None:
                return commands

            normalized_text = self.audio_handler.normalize_text(recognized_text)
            if normalized_text:
                self.state.last_voice_command = normalized_text

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
    ) -> AppCommand | None:
        foreground_commands = sorted(
            (
                command
                for command in commands
                if command.type != CommandType.TAKE_PHOTO
            ),
            key=lambda command: command.priority,
            reverse=True,
        )

        for command in foreground_commands:
            if command.type == CommandType.SET_CONTROL_MODE:
                if self._set_control_mode(command.mode):
                    return command
                continue
            if self.flight_controller.handle(
                command,
                vision.tracked_heads,
                now,
            ):
                return command
        return None

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

