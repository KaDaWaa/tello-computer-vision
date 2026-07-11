from types import SimpleNamespace

import numpy as np

from core.camera.tello_camera import TelloCamera


class FakeTello:
    def __init__(self, frame) -> None:
        self.frame_reader = SimpleNamespace(frame=frame)
        self.stream_started = False
        self.stream_stopped = False

    def streamon(self) -> None:
        self.stream_started = True

    def get_frame_read(self):
        return self.frame_reader

    def streamoff(self) -> None:
        self.stream_stopped = True


def test_tello_rgb_frame_is_normalized_to_bgr() -> None:
    rgb_frame = np.array([[[255, 20, 10]]], dtype=np.uint8)
    tello = FakeTello(rgb_frame)
    camera = TelloCamera(tello)
    camera.start()

    bgr_frame = camera.read()

    assert np.array_equal(bgr_frame, np.array([[[10, 20, 255]]]))


def test_tello_camera_lifecycle_controls_video_stream() -> None:
    tello = FakeTello(np.zeros((1, 1, 3), dtype=np.uint8))
    camera = TelloCamera(tello)

    camera.start()
    camera.stop()

    assert tello.stream_started
    assert tello.stream_stopped
    assert camera.frame_reader is None


def test_tello_camera_preserves_missing_frame_signal() -> None:
    tello = FakeTello(None)
    camera = TelloCamera(tello)
    camera.start()

    assert camera.read() is None
