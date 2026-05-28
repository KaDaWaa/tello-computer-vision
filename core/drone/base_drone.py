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
    def get_battery(self):
        pass