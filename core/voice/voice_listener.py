"""Vosk-based real-time voice recognition running in a background thread.

Streams microphone audio into Vosk with a restricted grammar so only
valid drone commands are recognized.  Results are pushed into a
thread-safe queue that the main loop can poll every frame.
"""

from __future__ import annotations

import json
import queue
import threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from pathlib import Path

from core.voice.phrases import VOICE_PHRASES

MODEL_PATH = Path("core/voice/models/vosk-model-small-en-us-0.15")


class VoiceListener:
    """
    Streams microphone audio and pushes recognized commands into a queue.
    Initialized lazily (model loaded once, mic starts on toggle)
    """

    BLOCK_SIZE = 4000
    GRAMMAR = json.dumps([*VOICE_PHRASES, "[unk]"])

    def __init__(self, sample_rate: int = 16000):
        self._model = Model(str(MODEL_PATH))
        self._recognizer = KaldiRecognizer(self._model, sample_rate, self.GRAMMAR)
        self._sample_rate = sample_rate
        self._command_queue: queue.Queue[str] = queue.Queue()
        self._listening = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_listening(self) -> bool:
        return self._listening

    def start(self) -> None:
        """Start listening in a background thread."""
        if self._listening:
            return
        self._stop_event.clear()
        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._listening = False
        self._stop_event.set()

    def poll_command(self) -> str | None:
        """Non-blocking poll for the next recognized command.

        Returns the command string or ``None`` if nothing is available.
        """
        try:
            return self._command_queue.get_nowait()
        except queue.Empty:
            return None

    def drain(self) -> None:
        """Discard any queued commands (useful when toggling mode off)."""
        while not self._command_queue.empty():
            try:
                self._command_queue.get_nowait()
            except queue.Empty:
                break

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _listen_loop(self) -> None:
        try:
            with sd.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=self.BLOCK_SIZE,
                dtype="int16",
                channels=1,
            ) as stream:
                while self._listening:
                    data, _ = stream.read(self.BLOCK_SIZE)
                    if self._recognizer.AcceptWaveform(bytes(data)):
                        result = json.loads(self._recognizer.Result())
                        text = result.get("text", "").strip()
                        if text and text != "[unk]":
                            self._command_queue.put(text)
        except Exception as exc:
            # If the audio device fails don't crash the whole app
            print(f"[VoiceListener] audio error: {exc}")
        finally:
            self._listening = False
