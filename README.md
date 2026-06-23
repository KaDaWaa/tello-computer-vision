# 🤖 Tello Computer Vision

Gesture-controlled autonomous drone flight using real-time computer vision. The system detects faces and hand gestures via MediaPipe, tracks heads across frames, and translates gestures into drone commands — enabling hands-free control of a DJI Tello drone.

---

## ✨ Features

- **Face Detection & Tracking** — Detects faces using MediaPipe BlazeFace and tracks them across frames with ID persistence and EMA-smoothed bounding boxes.
- **Hand Gesture Recognition** — Recognizes gestures (fist, open palm, thumbs up/down, pointing, peace sign, etc.) using MediaPipe's gesture recognizer.
- **Gesture → Drone Control** — Maps recognized gestures to drone actions: follow, move, flip, land, and release.
- **Autonomous Follow Mode** — PID-controlled tracking that adjusts yaw, altitude, and forward/backward movement to keep a target head centered in frame.
- **Parallel Vision Pipeline** — Head detection and gesture recognition run concurrently via `ThreadPoolExecutor` for reduced latency.
- **Mock Drone Mode** — Full pipeline testing with a webcam and simulated drone (no hardware required).
- **Real-Time HUD** — On-screen overlay showing FPS, battery level, drone state, active gesture, tracked head IDs, and gesture zones.

---

## 🎮 Gesture Commands

| Gesture | Action |
|---|---|
| ✊ Closed Fist | Start following the nearest detected face |
| 🖐️ Open Palm | Stop following (release target) |
| ✌️ Victory / Peace | Land the drone |
| 👍 Thumb Up | Move up 30 cm |
| 👎 Thumb Down | Move down 30 cm |
| ☝️ Pointing Up | Move forward 30 cm |
| 👇 Pointing Down | Move backward 30 cm |
| 👈 Pointing Left | Move left 30 cm |
| 👉 Pointing Right | Move right 30 cm |
| 🤟 I Love You | Flip forward |

> **Note:** Gestures require **3 consecutive stable frames** before triggering and have cooldown timers to prevent accidental repeats.

---

## 📁 Project Structure

```
tello-computer-vision/
├── main.py                          # Entry point — parses args and launches the app
├── requirements.txt                 # Python dependencies
│
├── app/
│   ├── main.py                      # Main loop: capture → detect → track → control → render
│   ├── config.py                    # Configuration: drone type, camera source
│   ├── controller.py                # FollowController: gesture→action mapping + PID follow
│   ├── state.py                     # Finite state machine (idle → taking_off → flying → following → landing)
│   └── drawing/
│       └── draw_utils.py            # HUD rendering: bounding boxes, landmarks, status panel
│
├── core/
│   ├── types.py                     # DroneType / CameraType enums
│   ├── camera/
│   │   ├── base_camera.py           # Abstract camera interface
│   │   ├── webcam.py                # OpenCV webcam implementation
│   │   └── tello_camera.py          # Tello video stream implementation
│   ├── drone/
│   │   ├── base_drone.py            # Abstract drone interface
│   │   ├── tello_drone.py           # DJI Tello SDK wrapper
│   │   └── mock_drone.py            # Simulated drone for testing
│   ├── tracking/
│   │   └── head_tracker.py          # Multi-head tracker with ID assignment and EMA smoothing
│   └── vision/
│       ├── bbox.py                  # BBox data class
│       ├── head_detection/
│       │   └── head_detector.py     # MediaPipe BlazeFace face detector
│       ├── hand_gestures/
│       │   ├── gesture_detector.py  # MediaPipe gesture recognizer
│       │   └── gesture_result.py    # GestureDetection data class
│       └── models/                  # MediaPipe model files (.task / .tflite)
```

---

## 🔄 State Machine

```
IDLE ──takeoff──▶ TAKING_OFF ──done──▶ FLYING ◀──release──┐
                                         │                │
                                    closed fist       open palm
                                         │                │
                                         ▼                │
                                     FOLLOWING ───────────┘
                                         │
                                    victory/peace
                                         │
                                         ▼
                                      LANDING ──done──▶ IDLE
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- A webcam (for mock mode) or a DJI Tello drone
- MediaPipe model files in `core/vision/models/mediapipe/`:
  - `gesture_recognizer.task`
  - `blaze_face_full_range.tflite`

### Installation

```bash
# Clone the repository
git clone https://github.com/KaDaWaa/tello-computer-vision.git
cd tello-computer-vision

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Run with mock drone (webcam only, no hardware needed)
python main.py --drone mock

# Run with a real DJI Tello
python main.py --drone tello
```

Press **`q`** to quit the application. If the drone is airborne, it will land automatically on exit.

---

## 🛠 Technical Details

### PID Follow Controller

When in **FOLLOWING** state, three independent PID controllers adjust:

| Axis | Error Signal | Control Output |
|---|---|---|
| **Yaw** | Horizontal offset of the head from frame center | Rotational velocity |
| **Forward/Back** | Difference between target and actual head-height ratio | Forward/backward velocity |
| **Up/Down** | Vertical offset of the head from frame center | Altitude velocity |

All PID outputs are clamped to `[-100, 100]` and sent as RC control commands at a minimum interval of 50 ms.

### Head Tracking

The tracker uses a **nearest-neighbor greedy assignment** strategy with a configurable maximum distance threshold. Bounding boxes are smoothed across frames using an **exponential moving average** (α = 0.8) to reduce jitter from per-frame MediaPipe detections. Stale tracks are pruned after 1 second of non-detection.

### Gesture Zones

Each tracked head has an associated **gesture zone** — a region to the left of the face where hand gestures are expected. Only gestures with hand landmarks fully inside this zone are attributed to that head, preventing cross-person command conflicts.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Video capture, image processing, and HUD rendering |
| `mediapipe` | Face detection (BlazeFace) and hand gesture recognition |
| `djitellopy` | DJI Tello SDK communication |

---

## 📄 License

This project is provided as-is for educational and experimental purposes.
