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
        self.head_target_id = None
        
    def follow(self, target_id: int):
        if self.head_target_id is None:
            self.head_target_id = target_id
            self.current_state = states.FOLLOWING
    
    def release_follow(self):
        self.head_target_id = None
        self.current_state = states.FLYING
        