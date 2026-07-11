from __future__ import annotations

from threading import Barrier
from types import SimpleNamespace

import numpy as np
import pytest

from app.pipeline.vision_pipeline import VisionPipeline


class RecordingDetector:
    def __init__(self, result, barrier: Barrier | None = None) -> None:
        self.result = result
        self.barrier = barrier
        self.frames: list[np.ndarray] = []
        self.closed = False

    def detect(self, frame: np.ndarray):
        self.frames.append(frame.copy())
        if self.barrier is not None:
            self.barrier.wait(timeout=2)
        return self.result

    def close(self) -> None:
        self.closed = True


class RecordingHead:
    def __init__(self, *, contains_gesture: bool) -> None:
        self.contain_gesture = contains_gesture
        self.association_calls = []

    def contains_gesture(self, gestures, width: int, height: int) -> None:
        self.association_calls.append((gestures, width, height))


class RecordingTracker:
    def __init__(self, tracked_heads) -> None:
        self.tracked_heads = tracked_heads
        self.updates = []

    def update(self, raw_heads, timestamp: float):
        self.updates.append((raw_heads, timestamp))
        return self.tracked_heads


def make_pipeline(
    *,
    heads_result=None,
    gesture_result=None,
    tracked_heads=None,
    barrier: Barrier | None = None,
):
    head_detector = RecordingDetector(heads_result or [], barrier)
    gesture_detector = RecordingDetector(gesture_result or [], barrier)
    tracker = RecordingTracker(tracked_heads or [])
    pipeline = VisionPipeline(head_detector, gesture_detector, tracker)
    return pipeline, head_detector, gesture_detector, tracker


def test_pipeline_converts_bgr_copy_to_rgb_for_both_detectors() -> None:
    pipeline, heads, gestures, _ = make_pipeline()
    frame = np.array([[[1, 2, 3], [10, 20, 30]]], dtype=np.uint8)

    result = pipeline.process(frame, timestamp=10.0)
    pipeline.close()

    expected_rgb = np.array([[[3, 2, 1], [30, 20, 10]]], dtype=np.uint8)
    assert np.array_equal(heads.frames[0], expected_rgb)
    assert np.array_equal(gestures.frames[0], expected_rgb)
    assert result.frame is frame
    assert np.array_equal(frame, np.array([[[1, 2, 3], [10, 20, 30]]]))


def test_head_and_gesture_detection_run_concurrently() -> None:
    barrier = Barrier(2)
    pipeline, _, _, _ = make_pipeline(barrier=barrier)

    pipeline.process(np.zeros((2, 2, 3), dtype=np.uint8), timestamp=10.0)
    pipeline.close()


def test_pipeline_updates_tracker_and_associates_gesture_zones() -> None:
    gesture = SimpleNamespace(gesture_name="fist")
    head = RecordingHead(contains_gesture=True)
    pipeline, _, _, tracker = make_pipeline(
        heads_result=["raw-head"],
        gesture_result=[gesture],
        tracked_heads=[head],
    )

    result = pipeline.process(
        np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=12.5,
    )
    pipeline.close()

    assert tracker.updates == [(["raw-head"], 12.5)]
    assert head.association_calls == [([gesture], 640, 480)]
    assert result.tracked_heads == [head]
    assert result.gestures == [gesture]
    assert result.width == 640
    assert result.height == 480
    assert result.control_gesture_name == "fist"


def test_control_gesture_is_hidden_when_outside_all_head_zones() -> None:
    gesture = SimpleNamespace(gesture_name="fist")
    head = RecordingHead(contains_gesture=False)
    pipeline, _, _, _ = make_pipeline(
        gesture_result=[gesture],
        tracked_heads=[head],
    )

    result = pipeline.process(
        np.zeros((2, 2, 3), dtype=np.uint8),
        timestamp=10.0,
    )
    pipeline.close()

    assert result.control_gesture_name is None


def test_close_releases_owned_resources_and_is_idempotent() -> None:
    pipeline, head_detector, gesture_detector, _ = make_pipeline()

    pipeline.close()
    pipeline.close()

    assert head_detector.closed
    assert gesture_detector.closed
    with pytest.raises(RuntimeError):
        pipeline.process(np.zeros((2, 2, 3), dtype=np.uint8))


@pytest.mark.parametrize(
    "frame",
    [
        np.zeros((2, 2), dtype=np.uint8),
        np.zeros((2, 2, 4), dtype=np.uint8),
    ],
)
def test_pipeline_rejects_non_bgr_frames(frame: np.ndarray) -> None:
    pipeline, _, _, _ = make_pipeline()

    with pytest.raises(ValueError):
        pipeline.process(frame)

    pipeline.close()
