
from .base_drone import BaseDrone


class MockDrone(BaseDrone):
    def __init__(self):
        self.is_flying = False

    def connect(self):
        print("MockDrone connected")

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

    def get_battery(self):
        return 100