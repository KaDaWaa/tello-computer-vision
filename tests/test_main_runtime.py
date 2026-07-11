from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.commands import CommandType
from app.main import run_application
from app.state import State


class RuntimeDrone:
    def __init__(self, events) -> None:
        self.events = events
        self.takeoff_calls = 0

    def connect(self) -> None:
        self.events.append("drone.connect")

    def disconnect(self) -> None:
        self.events.append("drone.disconnect")

    def get_battery(self) -> int:
        return 90

    def takeoff(self) -> None:
        self.takeoff_calls += 1

    def land(self) -> None:
        self.events.append("drone.land")


class RuntimeCamera:
    def __init__(self, events, frames) -> None:
        self.events = events
        self.frames = list(frames)

    def start(self) -> None:
        self.events.append("camera.start")

    def read(self):
        return self.frames.pop(0) if self.frames else None

    def stop(self) -> None:
        self.events.append("camera.stop")


class RuntimeFlightController:
    def __init__(self, events, state, drone) -> None:
        self.events = events
        self.state = state
        self.drone = drone
        self.commands = []

    def handle(self, command, tracked_heads, timestamp) -> bool:
        self.commands.append(command)
        self.events.append(f"flight.{command.type.value}")
        if command.type == CommandType.LAND:
            if self.state.is_following():
                self.state.release_follow()
            self.state.start_landing()
            self.drone.land()
            self.state.set_idle()
        return True


class RuntimeApplication:
    def __init__(self, events, state, drone, *, fail_processing=False) -> None:
        self.events = events
        self.state = state
        self.flight_controller = RuntimeFlightController(events, state, drone)
        self.fail_processing = fail_processing

    def start(self) -> None:
        self.events.append("application.start")

    def process_frame(self, frame, timestamp):
        self.events.append("application.process")
        if self.fail_processing:
            raise RuntimeError("processing failed")
        vision = SimpleNamespace(
            frame=frame,
            tracked_heads=[],
            gestures=[],
        )
        return SimpleNamespace(vision=vision)

    def close(self) -> None:
        self.events.append("application.close")


@pytest.fixture
def headless_opencv(monkeypatch):
    events = []
    monkeypatch.setattr("app.main.render", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.cv2.imshow", lambda *args: None)
    monkeypatch.setattr("app.main.cv2.waitKey", lambda delay: ord("q"))
    monkeypatch.setattr(
        "app.main.cv2.destroyAllWindows",
        lambda: events.append("opencv.close"),
    )
    return events


def test_runtime_starts_idle_without_automatic_takeoff(headless_opencv) -> None:
    events = headless_opencv
    state = State()
    drone = RuntimeDrone(events)
    camera = RuntimeCamera(events, [np.zeros((2, 2, 3), dtype=np.uint8)])
    application = RuntimeApplication(events, state, drone)

    assert run_application(drone, camera, application) == 0

    assert drone.takeoff_calls == 0
    assert application.flight_controller.commands == []
    assert events == [
        "drone.connect",
        "camera.start",
        "application.start",
        "application.process",
        "application.close",
        "camera.stop",
        "drone.disconnect",
        "opencv.close",
    ]


def test_runtime_lands_before_closing_resources(headless_opencv) -> None:
    events = headless_opencv
    state = State()
    state.set_flying()
    drone = RuntimeDrone(events)
    camera = RuntimeCamera(events, [np.zeros((2, 2, 3), dtype=np.uint8)])
    application = RuntimeApplication(events, state, drone)

    run_application(drone, camera, application)

    assert events[-6:] == [
        "flight.land",
        "drone.land",
        "application.close",
        "camera.stop",
        "drone.disconnect",
        "opencv.close",
    ]
    assert state.is_idle()


def test_runtime_cleans_up_and_lands_after_processing_error(
    headless_opencv,
) -> None:
    events = headless_opencv
    state = State()
    state.set_flying()
    drone = RuntimeDrone(events)
    camera = RuntimeCamera(events, [np.zeros((2, 2, 3), dtype=np.uint8)])
    application = RuntimeApplication(
        events,
        state,
        drone,
        fail_processing=True,
    )

    with pytest.raises(RuntimeError, match="processing failed"):
        run_application(drone, camera, application)

    assert "flight.land" in events
    assert events[-4:] == [
        "application.close",
        "camera.stop",
        "drone.disconnect",
        "opencv.close",
    ]
