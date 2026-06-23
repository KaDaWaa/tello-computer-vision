
from djitellopy import tello

from core.drone.base_drone import BaseDrone
from core.drone.mock_drone import MockDrone
from core.drone.tello_drone import TelloDrone
from core.types import DroneType, CameraType


class Config:
    def __init__(self, drone_type: DroneType = DroneType.MOCK):
        self.drone_type = drone_type

        if drone_type == DroneType.MOCK:
            self.camera_type = CameraType.WEBCAM
            self.webcam_width = 640
            self.webcam_height = 480
            self.webcam_src = 0
        elif drone_type == DroneType.TELLO:
            self.camera_type = CameraType.TELLO
    
    def init_drone(self):
        if self.drone_type == DroneType.MOCK:
            return MockDrone()
        elif self.drone_type == DroneType.TELLO:
            return TelloDrone()
        
    def init_camera(self, drone: BaseDrone):
        if self.camera_type == CameraType.WEBCAM:
            from core.camera.webcam import Webcam
            return Webcam(self.webcam_width, self.webcam_height, self.webcam_src)
        elif self.camera_type == CameraType.TELLO:
            from core.camera.tello_camera import TelloCamera
            return TelloCamera(drone.get_sdk_drone())
            