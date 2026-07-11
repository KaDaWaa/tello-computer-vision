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
        self.tello.takeoff()
        self.is_flying = True

    def land(self):
        if self.is_flying:
            try:
                self.tello.land()
            finally:
                self.is_flying = False
            

    def move(self, direction, distance):
        self.tello.move(direction, distance)

    def rotate(self, angle):
        if angle >= 0:
            self.tello.rotate_clockwise(angle)
        else:
            self.tello.rotate_counter_clockwise(abs(angle))

    def flip(self, direction):
        self.tello.flip(direction)

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int, yaw_velocity: int):
        self.tello.send_rc_control(left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity)

    def get_battery(self):
        return self.tello.get_battery()
    
    def get_sdk_drone(self):
        return self.tello
