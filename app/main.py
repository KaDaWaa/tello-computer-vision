from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from time import time

import cv2

from app.application import ApplicationCoordinator, ApplicationFrame
from app.commands import AppCommand
from app.drawing.draw_utils import FPSCounter, render
from app.flight_controller import FlightController
from app.state import State
from core.camera.base_camera import BaseCamera
from core.drone.base_drone import BaseDrone
from core.types import DroneType


@dataclass
class _BatteryMonitor:
    poll_interval_seconds: float = 2.0
    value: int | None = None
    last_poll_timestamp: float = float("-inf")

    def update(self, drone: BaseDrone, timestamp: float) -> int | None:
        if timestamp - self.last_poll_timestamp < self.poll_interval_seconds:
            return self.value
        try:
            self.value = drone.get_battery()
        except Exception:
            pass
        self.last_poll_timestamp = timestamp
        return self.value


def main(drone_type: DroneType = DroneType.MOCK) -> int:
    from app.config import Config

    config = Config(drone_type)
    drone = config.init_drone()
    camera = config.init_camera(drone)
    state = State()
    flight_controller = FlightController(state, drone)
    application = ApplicationCoordinator(state, flight_controller)
    return run_application(drone, camera, application)


def run_application(
    drone: BaseDrone,
    camera: BaseCamera,
    application: ApplicationCoordinator,
) -> int:
    fps_counter = FPSCounter()
    battery = _BatteryMonitor()
    show_debug = True

    with ExitStack() as cleanup:
        cleanup.callback(cv2.destroyAllWindows)
        cleanup.callback(drone.disconnect)
        drone.connect()
        cleanup.callback(camera.stop)
        camera.start()
        cleanup.callback(application.close)
        application.start()
        cleanup.callback(_land_before_shutdown, application)

        while True:
            frame = camera.read()
            if frame is None:
                key = _read_key()
                if key == ord("q"):
                    break
                if key == ord("d"):
                    show_debug = not show_debug
                continue

            now = time()
            result = application.process_frame(frame, now)
            battery_value = battery.update(drone, now)
            fps = fps_counter.tick()
            display = _render_frame(
                result,
                application.state,
                battery_value,
                fps,
                show_debug,
            )
            cv2.imshow("Tello Computer Vision", display)

            key = _read_key()
            if key == ord("q"):
                break
            if key == ord("d"):
                show_debug = not show_debug

    return 0


def _render_frame(
    result: ApplicationFrame,
    state: State,
    battery: int | None,
    fps: float,
    show_debug: bool,
):
    feedback = result.command_feedback
    return render(
        result.vision.frame,
        result.vision.tracked_heads,
        result.vision.gestures,
        state.head_target_id,
        state.current_state.value,
        battery,
        fps,
        control_mode=state.control_mode.value,
        voice_listening=state.voice_listening,
        last_voice_cmd=state.last_voice_command,
        detected_input=result.detected_input,
        command_text=(feedback.command.description if feedback else None),
        command_status=(feedback.status if feedback else None),
        command_detail=(feedback.detail if feedback else None),
        photo_seconds_remaining=result.photo_seconds_remaining,
        photo_saved=result.photo_saved,
        show_debug=show_debug,
    )


def _read_key() -> int:
    """Read a keyboard event from OpenCV GUI and mask to 8-bit."""
    return cv2.waitKey(1) & 0xFF


def _land_before_shutdown(application: ApplicationCoordinator) -> None:
    state = application.state
    if state.is_flying() or state.is_following():
        application.flight_controller.handle(
            AppCommand.land(),
            tracked_heads=[],
            timestamp=time(),
        )
    elif not state.is_idle():
        application.flight_controller.drone.land()

