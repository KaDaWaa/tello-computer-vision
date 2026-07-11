from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


class PhotoCapture:
    """Write captured BGR frames on a background thread."""

    def __init__(self, output_directory: str | Path = "photos") -> None:
        self.output_directory = Path(output_directory).resolve()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="PhotoWriter",
        )
        self._pending_writes: list[Future] = []
        self._closed = False

    def capture(self, frame: np.ndarray, captured_at: float) -> Path:
        if self._closed:
            raise RuntimeError("PhotoCapture is closed")

        timestamp = datetime.fromtimestamp(captured_at)
        filename = timestamp.strftime("tello_%Y%m%d_%H%M%S_%f.jpg")
        output_path = self.output_directory / filename
        frame_copy = frame.copy()
        self._pending_writes.append(
            self._executor.submit(self._write, frame_copy, output_path)
        )
        return output_path

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)
        for write in self._pending_writes:
            write.result()

    @staticmethod
    def _write(frame: np.ndarray, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), frame):
            raise OSError(f"Could not save photo to {output_path}")

