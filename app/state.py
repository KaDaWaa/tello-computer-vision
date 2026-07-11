from enum import Enum
from typing import Optional

class states(Enum):
    IDLE = "idle"
    FLYING = "flying"
    LANDING = "landing"
    TAKING_OFF = "taking_off"
    FOLLOWING = "following"

class control_mode(Enum):
    GESTURES = "gestures"
    VOICE_COMMANDS = "voice commands"

class State:
    def __init__(self):
        self.control_mode = control_mode.GESTURES
        self.current_state = states.IDLE
        self.head_target_id: Optional[int] = None
        self.voice_listening: bool = False
        self.last_voice_command: str = ""

    def toggle_mode(self):
        """Switches the control mode between GESTURES and VOICE_COMMANDS.
        
        Allowed while IDLE, FLYING, or FOLLOWING.
        """
        next_mode = (
            control_mode.VOICE_COMMANDS
            if self.control_mode == control_mode.GESTURES
            else control_mode.GESTURES
        )
        self.set_control_mode(next_mode)

    def set_control_mode(self, mode: control_mode) -> bool:
        if self.current_state not in (
            states.IDLE,
            states.FLYING,
            states.FOLLOWING,
        ):
            return False

        self.control_mode = mode
        return True

    def is_voice_mode(self) -> bool:
        return self.control_mode == control_mode.VOICE_COMMANDS

    def get_mode(self):
        """Returns the current control mode"""
        return self.control_mode
    
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
