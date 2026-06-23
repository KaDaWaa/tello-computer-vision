
from .base_drone import BaseDrone


class MockDrone(BaseDrone):
    def __init__(self):
        self.is_flying = False
        self.rc_state = (0, 0, 0, 0)

    def connect(self):
        print("MockDrone connected")
        
    def disconnect(self):
        print("MockDrone disconnected")

    def takeoff(self):
        print("MockDrone taking off...")
        self.is_flying = True

    def land(self):
        print("MockDrone landing...")
        self.is_flying = False

    def move(self, direction, distance):
        print(f"MockDrone moving {direction} {distance} cm.")

    def rotate(self, angle):
        print(f"MockDrone rotating {angle} degrees.")

    def flip(self, direction):
        print(f"MockDrone flipping {direction}.")

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int, yaw_velocity: int):
        self.rc_state = (left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity)
        print(
            "MockDrone RC control: "
            f"lr={left_right_velocity}, fb={forward_backward_velocity}, ud={up_down_velocity}, yaw={yaw_velocity}"
        )

    def get_battery(self):
        return 100
    
    def get_sdk_drone(self):
        return None