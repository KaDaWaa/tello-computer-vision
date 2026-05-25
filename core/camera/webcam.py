import cv2

from .base_camera import BaseCamera

class Webcam(BaseCamera):
    def __init__(self, width=640, height=480, src=0):
        self.src = src
        self.width = width
        self.height = height

        self.camera = None



    def start(self):
        self.camera = cv2.VideoCapture(self.src)

        if not self.camera.isOpened():
            raise Exception("Could not open webcam")
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        

    def read(self):
        success, frame = self.camera.read()

        if not success:
            return None

        return frame

    def stop(self):
        if self.camera:
            self.camera.release()