from enum import Enum

class states(Enum):
    IDLE = "idle"
    FLYING = "flying"
    LANDING = "landing"
    TAKING_OFF = "taking_off"
    FOLLOWING = "following"

class State:
    def __init__(self):
        self.current_state = states.IDLE