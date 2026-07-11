import numpy as np
import pytest

from app.photo_capture import PhotoCapture


def test_photo_is_written_in_background_on_close(tmp_path) -> None:
    capture = PhotoCapture(tmp_path)

    output_path = capture.capture(
        np.zeros((4, 6, 3), dtype=np.uint8),
        captured_at=10.0,
    )
    capture.close()

    assert output_path.parent == tmp_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_closed_photo_capture_rejects_new_frames(tmp_path) -> None:
    capture = PhotoCapture(tmp_path)
    capture.close()

    with pytest.raises(RuntimeError):
        capture.capture(np.zeros((2, 2, 3), dtype=np.uint8), 10.0)
