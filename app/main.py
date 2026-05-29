import cv2

from core.drone.base_drone import BaseDrone
from core.camera.base_camera import BaseCamera
from core.vision.hand_gestures.gesture_box import GestureBox
from core.vision.hand_gestures.gesture_detector import GestureDetector
from core.vision.head_detection.head_box import HeadBox
from core.vision.head_detection.head_detector import HeadDetector

from .config import Config
from core.types import DroneType, CameraType
from app.drawing.draw_utils import draw_battery, draw_bboxes, FPSCounter, draw_fps, draw_gestures
import time

def main(drone_type: DroneType = DroneType.MOCK):
    config = Config(drone_type)
    drone: BaseDrone = config.init_drone()
    camera: BaseCamera = config.init_camera(drone) 

    head_detector = HeadDetector()  
    gesture_detector = GestureDetector()
    
    drone.connect()
    camera.start()
    fps_counter = FPSCounter()

    try:
        drone.takeoff()
        while True:
            print("Reading frame... drone battery:", drone.get_battery())
            frame = camera.read()
            
            if frame is None:
                continue

            head_detections: list[HeadBox] = head_detector.detect(frame)

            # draw detections and overlays before potential color conversion
            if head_detections:
                draw_bboxes(frame, head_detections)
                draw_bboxes(frame, [GestureBox.from_head_box(head_box) for head_box in head_detections],label_prefix="Gesture")

            results = gesture_detector.detect(frame)
            if results:
                draw_gestures(frame, results)

                
                

            fps_val = fps_counter.tick()
            draw_fps(frame, fps_val)
            draw_battery(frame, drone.get_battery())

            if config.camera_type == CameraType.TELLO:  
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            cv2.imshow("Frame", frame)


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.stop()
        drone.land()
