from types import SimpleNamespace

import numpy as np

from app.drawing.draw_utils import render
from core.vision.bbox import BBox


def test_sidebar_keeps_status_outside_camera_frame() -> None:
    frame = np.full((480, 640, 3), 160, dtype=np.uint8)

    display = render(
        frame,
        [],
        [],
        current_state="flying",
        battery=87,
        fps=29.8,
        control_mode="voice commands",
        voice_listening=True,
        detected_input="go left",
        command_text="MOVE LEFT 30 cm",
        command_status="executed",
        show_debug=False,
    )

    assert display.shape == (480, 930, 3)
    assert np.array_equal(display[:, :640], frame)
    assert np.all(display[165, 900] < 160)


def test_debug_toggle_hides_non_target_tracking_boxes() -> None:
    head = SimpleNamespace(
        id=1,
        bbox=BBox(40, 40, 80, 80),
        gesture_zone=BBox(140, 40, 80, 100),
        contain_gesture=False,
    )
    without_debug = np.full((480, 640, 3), 100, dtype=np.uint8)
    with_debug = without_debug.copy()

    without_debug_display = render(
        without_debug, [head], [], show_debug=False
    )
    with_debug_display = render(with_debug, [head], [], show_debug=True)

    assert np.array_equal(
        without_debug_display[40, 40], np.array([100, 100, 100])
    )
    assert not np.array_equal(
        with_debug_display[40, 40], without_debug_display[40, 40]
    )


def test_photo_countdown_draws_centered_notification() -> None:
    baseline = np.full((480, 640, 3), 120, dtype=np.uint8)
    countdown = baseline.copy()

    baseline_display = render(baseline, [], [], show_debug=False)
    countdown_display = render(
        countdown,
        [],
        [],
        photo_seconds_remaining=2.1,
        show_debug=False,
    )

    sidebar_bottom = (slice(380, 470), slice(650, 920))
    assert not np.array_equal(
        countdown_display[sidebar_bottom],
        baseline_display[sidebar_bottom],
    )
