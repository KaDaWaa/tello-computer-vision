from concurrent.futures import ThreadPoolExecutor, wait
from time import sleep, time

import cv2

from app.drawing.draw_utils import (FPSCounter, draw_battery, draw_bbox,
                                    draw_fps, draw_gestures, render)
from core.camera.base_camera import BaseCamera
from core.drone.base_drone import BaseDrone
from core.tracking.head_tracker import HeadTracker
from core.types import CameraType, DroneType
from core.vision.hand_gestures.gesture_detector import GestureDetector
from core.vision.head_detection.head_detector import HeadDetector
from core.voice.voice_listener import VoiceListener

from .config import Config
from .controller import FollowController
from .state import State, control_mode
from .voice_controller import VoiceController

def _normalized_gesture(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().lower().replace(" ", "_")


def main(drone_type: DroneType = DroneType.MOCK):
    config = Config(drone_type)
    drone: BaseDrone = config.init_drone()
    camera: BaseCamera = config.init_camera(drone) 

    head_detector = HeadDetector()
    gesture_detector = GestureDetector()
    voice_listener = VoiceListener()
    
    state = State()
    head_tracker = HeadTracker()
    gesture_controller = FollowController(state)
    voice_controller = VoiceController(state)

    
    drone.connect()
    camera.start()
    fps_counter = FPSCounter()

    # -- Mode-toggle gesture detection state --
    MODE_TOGGLE_GESTURES = {"iloveyou", "i_love_you"}
    TOGGLE_REQUIRED_FRAMES = 5      # need 5 stable frames to trigger
    TOGGLE_COOLDOWN_SECONDS = 2.0   # prevent rapid toggling
    toggle_stable_frames = 0
    toggle_last_gesture = ""
    toggle_last_time = 0.0

    vision_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="VisionWorker")
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
                    pass
                last_battery_poll = now

            heads_task = vision_executor.submit(head_detector.detect, frame)
            gesture_task = vision_executor.submit(gesture_detector.detect, frame)
            wait([heads_task, gesture_task])
            
            head_tracker.update(heads_task.result(), now)
            gesture_results = gesture_task.result()

            for head in head_tracker.tracked_heads:
                head.contains_gesture(gesture_results, frame.shape[1], frame.shape[0])

            # ---------------------------------------------------------------
            # Mode toggle detection (ILoveYou gesture toggles voice/gesture)
            # ---------------------------------------------------------------
            toggle_gesture_detected = False
            for det in gesture_results:
                g = _normalized_gesture(det.gesture_name)
                if g in MODE_TOGGLE_GESTURES:
                    toggle_gesture_detected = True
                    if g == toggle_last_gesture:
                        toggle_stable_frames += 1
                    else:
                        toggle_last_gesture = g
                        toggle_stable_frames = 1
                    break

            if not toggle_gesture_detected:
                toggle_stable_frames = 0
                toggle_last_gesture = ""

            if toggle_stable_frames >= TOGGLE_REQUIRED_FRAMES and (now - toggle_last_time) > TOGGLE_COOLDOWN_SECONDS:
                state.toggle_mode()
                toggle_last_time = now
                toggle_stable_frames = 0

                # Start / stop microphone based on new mode
                if state.is_voice_mode():
                    voice_listener.start()
                    state.voice_listening = True
                else:
                    voice_listener.stop()
                    voice_listener.drain()
                    state.voice_listening = False
                    state.last_voice_command = ""

            # ---------------------------------------------------------------
            # Control dispatch — gesture mode vs voice mode
            # ---------------------------------------------------------------
            if state.is_voice_mode():
                # Poll all queued voice commands this frame
                voice_cmd = voice_listener.poll_command()
                while voice_cmd is not None:
                    voice_controller.handle(
                        voice_cmd,
                        drone,
                        head_tracker.tracked_heads,
                        now,
                    )
                    voice_cmd = voice_listener.poll_command()
            else:
                gesture_controller.update(
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
                control_mode=state.control_mode.value,
                voice_listening=state.voice_listening,
                last_voice_cmd=state.last_voice_command,
            )

            cv2.imshow("Frame", frame)

            if state.is_landing():
                drone.land()
                state.set_idle()
                break


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        voice_listener.stop()
        if not state.is_idle():
            state.set_idle()
            state.start_landing()
            drone.land()
        camera.stop()
