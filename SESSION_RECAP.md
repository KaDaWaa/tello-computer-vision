# Session Recap: Gesture-Controlled Drone Follow & Tracking Stabilization

**Date**: 2026-06-17  
**Objective**: Build gesture-controlled drone follow system and fix head detection instability

---

## Problem Identified

User reported that head detection bounding boxes were **jumping/unstable** during tracking, causing jerky visual feedback and unstable PID control inputs.

### Root Cause Analysis
1. **MediaPipe face detector natural jitter**: Detections naturally vary 50–150px frame-to-frame due to model inherent variation
2. **Strict matching threshold**: `max_distance=100.0px` was too tight, causing legitimate detections to exceed threshold
3. **No bbox smoothing**: When detections were matched, raw jittery coords were assigned directly without filtering
4. **ID reassignment**: When a jittery detection exceeded threshold, it created a *new head ID* instead of being matched to existing head, breaking consistency

## Solution Implemented

### Changes Made

#### `core/tracking/head_tracker.py`

**1. Increased matching threshold**
```python
# Before
max_distance: float = 100.0

# After
max_distance: float = 200.0  # Increased from 100 to handle jitter from MediaPipe detector
```

**2. Added EMA smoothing to TrackedHead**
```python
@dataclass
class TrackedHead:
    # ... existing fields ...
    ema_alpha: float = 0.3  # EMA smoothing factor (0=no smoothing, 1=only new)
    
    def smooth_bbox(self, new_bbox: BBox) -> BBox:
        """Apply exponential moving average to smooth bbox across frames"""
        smoothed_x = int(self.bbox.x * (1 - self.ema_alpha) + new_bbox.x * self.ema_alpha)
        smoothed_y = int(self.bbox.y * (1 - self.ema_alpha) + new_bbox.y * self.ema_alpha)
        smoothed_w = int(self.bbox.width * (1 - self.ema_alpha) + new_bbox.width * self.ema_alpha)
        smoothed_h = int(self.bbox.height * (1 - self.ema_alpha) + new_bbox.height * self.ema_alpha)
        return BBox(x=smoothed_x, y=smoothed_y, width=smoothed_w, height=smoothed_h)
```

**3. Applied EMA smoothing in update logic**
```python
# Before
tracked_head.bbox = closest_raw_head
tracked_head.center = closest_raw_head.get_center()

# After
tracked_head.bbox = tracked_head.smooth_bbox(closest_raw_head)
tracked_head.center = tracked_head.bbox.get_center()
```

### How It Works

1. **Relaxed matching (200px threshold)**: Allows MediaPipe's jitter to still match to the same head instead of creating new IDs
2. **EMA blending**: Each frame's detected bbox is blended 30% new + 70% old, creating smooth motion curves:
   - `smoothed_x = 0.7 * old_x + 0.3 * new_x`
   - Same for y, width, height
3. **Consistent tracking**: Same head ID maintained across frames → gesture detection and PID control get stable inputs

### Expected Result

- Head bounding boxes move smoothly without jumping
- Same head ID remains stable across frames (critical for gesture detection)
- PID yaw/forward control gets smooth error signals instead of noisy jitter
- Visual feedback shows fluid head tracking

---

## Prior Session Context (Full Implementation)

This session also built the complete gesture-controlled drone follow system in previous work:

### Architecture Implemented

**State Machine** (`app/state.py`)
- Flight states: IDLE → TAKING_OFF → FLYING → LANDING
- Follow mode: FLYING ↔ FOLLOWING
- Explicit transitions prevent invalid state changes

**Gesture-to-Action Mapping** (`app/controller.py`)
- **Closed Fist** (`closed_fist`, `closedfist`, `fist`) → Toggle follow mode ON
- **Open Hand** (`open_palm`, `open_hand`, `openhand`, `palm`) → Stop following
- **Victory / peace sign** (`victory`, `peace`, `v_sign`, `v_sign_hand`, `v_sign_gesture`) → Release follow and land
- **Move Gestures** → 12 directions (thumb_up=up, thumb_down=down, etc.)
- **Flip Gestures** → I love you sign triggers flip
- Debounce: 3-frame sustain + 0.45s cooldown prevents false triggers
- One-shot action lock: move/flip commands are ignored for a short busy window so they do not overlap

**PID-Based Follow Control** (`app/controller.py`)
- **Yaw PID**: Keeps head centered (yaw_kp=0.35, yaw_kd=0.08)
- **Forward/Back PID**: Maintains head size ratio at 0.18 of frame (forward_kp=0.45, forward_kd=0.08)
- RC commands throttled to max 1 per 0.05s
- Deadband removed so small corrections register immediately
- Current tuning is more aggressive than the original values to make tracking react faster

**Drone Implementations**
- `core/drone/base_drone.py`: Abstract interface
- `core/drone/tello_drone.py`: Real Tello SDK adapter with stream control and fail-soft move/flip handling
- `core/drone/mock_drone.py`: Test simulation

**Tracking & Gesture Detection** (`core/tracking/head_tracker.py`, gesture system)
- MediaPipe face detection + hand landmark tracking
- Head tracking with ID persistence
- Gesture zone positioning (zone to left of head for hand visibility)

**Visualization** (`app/drawing/draw_utils.py`)
- Tracking overlay: Center point + lines to each head (color-coded)
- Compact status panel (top-right, ~190px × 118px):
  - Current state
  - Active gestures
  - Battery %
  - FPS counter

**Battery & Performance Optimization** (`app/main.py`)
- Battery polled every 2s (not every frame)
- FPS counter active for real-time perf monitoring
- Sequential main loop (read → detect → control → render)

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `app/controller.py` | Victory-sign now releases follow and lands the drone |
| `app/main.py` | Main loop exits once landing starts |
| `core/drone/tello_drone.py` | Added fail-soft handling for rejected move/flip commands |
| `core/tracking/head_tracker.py` | Added EMA smoothing, increased max_distance from 100→200px |

---

## Files Created/Previously Implemented (Context)

| File | Purpose |
|------|---------|
| `app/state.py` | Flight/follow state machine |
| `app/controller.py` | Gesture debounce, PID follow control, RC throttling |
| `app/main.py` | Main loop, lifecycle, detector wiring |
| `core/drone/base_drone.py` | Abstract drone interface |
| `core/drone/tello_drone.py` | Tello SDK adapter |
| `core/drone/mock_drone.py` | Mock drone for testing |
| `core/vision/head_detection/head_detector.py` | MediaPipe face detection |
| `core/vision/hand_gestures/gesture_detector.py` | MediaPipe gesture recognition |
| `app/drawing/draw_utils.py` | Tracking overlay + status panel |

---

## Testing Notes

- **Before Fix**: Head bounding boxes jittered visibly, PID inputs were noisy
- **After Fix**: Head tracking should be smooth with stable ID persistence
- **Next Test**: Gesture recognition should be more responsive with stable bbox data
- **Performance**: Frame rate should remain unaffected (EMA is O(1) per frame)

---

## Future Tuning Options

If tracking is still not smooth enough:
1. Lower `ema_alpha` from 0.3 → 0.15 (more historical weight, smoother but slower response)
2. Increase `max_distance` further if jitter still causes ID switches
3. Add frame-to-frame velocity prediction for heads to anticipate motion

If gestures are missed or unstable:
1. Verify MediaPipe gesture names match expected strings (may vary by model)
2. Lower gesture debounce threshold from 3 frames
3. Reduce gesture zone cutoff distance (currently `head_bbox.width + 30`)

