from enum import Enum
from typing import Optional

class states(Enum):
    IDLE = "idle"
    FLYING = "flying"
    LANDING = "landing"
    TAKING_OFF = "taking_off"
    FOLLOWING = "following"

class State:
    def __init__(self):
        self.current_state = states.IDLE
        self.head_target_id: Optional[int] = None
    
    # Flight state helpers
    def is_idle(self):
        return self.current_state == states.IDLE

    def is_flying(self):
        return self.current_state == states.FLYING

    def is_taking_off(self):
        return self.current_state == states.TAKING_OFF

    def is_landing(self):
        return self.current_state == states.LANDING

    # Following state management
    def is_following(self):
        return self.current_state == states.FOLLOWING
        
    def start_follow(self, target_id: int):
        if self.current_state in (states.FLYING, states.FOLLOWING):
            self.head_target_id = target_id
            self.current_state = states.FOLLOWING
    
    def release_follow(self):
        if self.current_state == states.FOLLOWING:
            self.head_target_id = None
            self.current_state = states.FLYING
    

    # Takeoff and landing state management
    def start_takeoff(self):
        if self.current_state == states.IDLE:
            self.current_state = states.TAKING_OFF
            self.head_target_id = None
        
    def start_landing(self):
        if self.current_state in (states.FLYING, states.FOLLOWING):
            self.current_state = states.LANDING
            self.head_target_id = None

    def finish_takeoff(self):
        if self.current_state == states.TAKING_OFF:
            self.current_state = states.FLYING

    # Idle state management
    def set_idle(self):
        if self.current_state == states.LANDING:
            self.current_state = states.IDLE
            self.head_target_id = None
    
    def set_flying(self):
        self.current_state = states.FLYING
        self.head_target_id = None