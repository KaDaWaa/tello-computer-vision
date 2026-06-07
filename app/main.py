import cv2

from core.drone.base_drone import BaseDrone
from core.camera.base_camera import BaseCamera
from core.tracking.head_tracker import HeadTracker
from core.vision.hand_gestures.gesture_detector import GestureDetector
from core.vision.head_detection.head_detector import HeadDetector

from .config import Config
from core.types import DroneType, CameraType
from app.drawing.draw_utils import draw_battery, draw_bbox, FPSCounter, draw_fps, draw_gestures, render
from time import time

def main(drone_type: DroneType = DroneType.MOCK):
    config = Config(drone_type)
    drone: BaseDrone = config.init_drone()
    camera: BaseCamera = config.init_camera(drone) 

    head_detector = HeadDetector()
    head_tracker = HeadTracker()
    gesture_detector = GestureDetector()
    
    
    drone.connect()
    camera.start()
    fps_counter = FPSCounter()

    try:
        drone.takeoff()
        while True:
            frame = camera.read()
            
            if frame is None:
                continue

            head_tracker.update(head_detector.detect(frame), time())
            gesture_results = gesture_detector.detect(frame)
            
            for head in head_tracker.tracked_heads:
                head.contains_gesture(gesture_results, frame.shape[1], frame.shape[0])
            
            
            render(frame, head_tracker.tracked_heads, gesture_results)

                
                

            # fps_val = fps_counter.tick()
            # draw_fps(frame, fps_val)
            # draw_battery(frame, drone.get_battery())

            if config.camera_type == CameraType.TELLO:  
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            cv2.imshow("Frame", frame)
            #render(frame, head_tracker.tracked_heads, gesture_results,)


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.stop()
        drone.land()
