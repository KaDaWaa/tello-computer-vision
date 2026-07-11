from __future__ import annotations

from typing import TYPE_CHECKING

import cv2

from .base_camera import BaseCamera

if TYPE_CHECKING:
    from djitellopy import Tello


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

        # djitellopy creates the ndarray from a PIL image, so Tello frames
        # arrive as RGB. Normalize all camera implementations to OpenCV BGR.
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def stop(self):
        self.tello.streamoff()
        self.frame_reader = None
    
