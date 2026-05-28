from .base_drone import BaseDrone
from djitellopy import Tello

class TelloDrone(BaseDrone):
    def __init__(self):
        self.tello = Tello()
        self.is_flying = False
        self.is_connected = False

    def connect(self):
        self.tello.connect()
        self.is_connected = True

    def disconnect(self):
        if self.is_connected:
            try:
                if self.is_flying:
                    self.land()
                self.tello.end()
            finally:
                self.is_connected = False    

    def takeoff(self):
            pass

    def land(self):
        if self.is_flying:
            try:
                self.tello.land()
            finally:
                self.is_flying = False
            

    def move(self, direction, distance):
        self.tello.send_rc_control

    def rotate(self, angle):
        pass

    def get_battery(self):
        pass