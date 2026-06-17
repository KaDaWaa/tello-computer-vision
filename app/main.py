import cv2

from core.drone.base_drone import BaseDrone
from core.camera.base_camera import BaseCamera
from core.tracking.head_tracker import HeadTracker
from core.vision.hand_gestures.gesture_detector import GestureDetector
from core.vision.head_detection.head_detector import HeadDetector

from .config import Config
from .controller import FollowController
from .state import State
from core.types import DroneType, CameraType
from app.drawing.draw_utils import draw_battery, draw_bbox, FPSCounter, draw_fps, draw_gestures, render
from time import time, sleep

def main(drone_type: DroneType = DroneType.MOCK):
    config = Config(drone_type)
    drone: BaseDrone = config.init_drone()
    camera: BaseCamera = config.init_camera(drone) 

    head_detector = HeadDetector()
    head_tracker = HeadTracker()
    gesture_detector = GestureDetector()
    state = State()
    controller = FollowController(state)
    
    
    drone.connect()
    camera.start()
    fps_counter = FPSCounter()

    try:
        state.start_takeoff()
        drone.takeoff()
        state.finish_takeoff()
        battery_cache = None
        last_battery_poll = 0.0
        while True:
            frame = camera.read()
            
            if frame is None:
                continue

            # Convert to RGB early so all processing uses consistent color format
            if config.camera_type == CameraType.TELLO:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            fps_value = fps_counter.tick()
            now = time()
            if now - last_battery_poll > 2.0:
                try:
                    battery_cache = drone.get_battery()
                except Exception:
                    battery_cache = None
                last_battery_poll = now

            head_tracker.update(head_detector.detect(frame), now)
            gesture_results = gesture_detector.detect(frame)
            
            for head in head_tracker.tracked_heads:
                head.contains_gesture(gesture_results, frame.shape[1], frame.shape[0])

            controller.update(
                drone,
                head_tracker.tracked_heads,
                gesture_results,
                frame.shape[1],
                frame.shape[0],
                now,
            )
            
            
            render(
                frame,
                head_tracker.tracked_heads,
                gesture_results,
                state.head_target_id,
                state.current_state.value,
                battery_cache,
                fps_value,
            )

            cv2.imshow("Frame", frame)
            #render(frame, head_tracker.tracked_heads, gesture_results,)

            if state.is_landing():
                drone.land()
                state.set_idle()
                break


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        if not state.is_idle():
            state.start_landing()
            drone.land()
        camera.stop()
        state.set_idle()
