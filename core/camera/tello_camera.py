from djitellopy import Tello

from .base_camera import BaseCamera

class TelloCamera(BaseCamera):
    def __init__(self, tello: Tello):
        self.tello = tello
        self.frame_reader = None

    def start(self):
        self.tello.streamon()
        self.frame_reader = self.tello.get_frame_read()
    
    def read(self):
        frame = self.frame_reader.frame

        if frame is None:
            return None

        return frame

    def stop(self):
        self.tello.streamoff()
        self.frame_reader = None
    