from abc import ABC, abstractmethod

class BaseDrone(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def takeoff(self):
        pass

    @abstractmethod
    def land(self):
        pass

    @abstractmethod
    def move(self, direction, distance):
        pass

    @abstractmethod
    def rotate(self, angle):
        pass

    @abstractmethod
    def flip(self, direction):
        pass

    @abstractmethod
    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int, yaw_velocity: int):
        pass

    @abstractmethod
    def get_battery(self):
        pass
    
    @abstractmethod
    def get_sdk_drone(self):
        pass