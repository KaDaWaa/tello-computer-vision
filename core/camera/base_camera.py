from abc import ABC, abstractmethod

class BaseCamera(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def stop(self):
        pass