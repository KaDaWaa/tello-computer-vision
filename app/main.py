import cv2

from core.drone.base_drone import BaseDrone
from core.camera.base_camera import BaseCamera

from .config import Config
from core.types import DroneType, CameraType

def main(drone_type: DroneType = DroneType.MOCK):
    config = Config(drone_type)
    drone: BaseDrone = config.init_drone()
    camera: BaseCamera = config.init_camera(drone)   
    
    camera.start()
    try:
        drone.takeoff()
        while True:
            print("Reading frame... drone battery:", drone.get_battery())
            frame = camera.read()
            
            if frame is None:
                continue

            if config.camera_type == CameraType.TELLO:  
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            cv2.imshow("Frame", frame)


            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.stop()
        drone.land()
