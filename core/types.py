from enum import StrEnum

class DroneType(StrEnum):
    TELLO = "tello"
    MOCK = "mock"

class CameraType(StrEnum):
    TELLO = "tello"
    WEBCAM = "webcam"
