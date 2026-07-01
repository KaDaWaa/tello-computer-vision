# tello-computer-vision

Gesture/voice-controlled DJI Tello drone using MediaPipe face + hand detection.

## Quick start

```bash
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py              # default: --drone mock (webcam + simulated drone)
python main.py --drone tello  # real hardware
```

## Entry point

`main.py` → `app/main.py:main()` — parses args, inits camera/drone/detectors, runs the capture→detect→track→control→render loop.

## Architecture

- **`app/`** — orchestration: config, state machine, controller, voice controller, HUD drawing
- **`core/`** — abstract interfaces + implementations: camera (webcam/tello), drone (mock/tello), tracking, vision (MediaPipe detectors)
- **`core/vision/models/mediapipe/`** — required model files: `gesture_recognizer.task`, `blaze_face_full_range.tflite`
- **`core/voice/models/vosk-model-small-en-us-0.15/`** — required Vosk model directory for voice mode

## Important details

- **Two control modes**: gesture (default) and voice. Toggle by showing "I Love You" gesture for 5 consecutive frames (2s cooldown).
- **State machine**: IDLE → TAKING_OFF → FLYING ↔ FOLLOWING → LANDING → IDLE. Only transitions from FLYING to FOLLOWING (closed fist) and back (open palm).
- **Vision pipeline**: head detection + gesture recognition run in parallel via `ThreadPoolExecutor(max_workers=2)`.
- **Color space**: Webcam returns BGR (used as-is, MediaPipe expects RGB but detection works). Tello camera returns RGB via djitellopy. RGB conversion applied in `app/main.py:72-73`.
- **Gesture stability**: commands require 3 consecutive stable frames + cooldown; one-shot moves/flips have a lock duration to prevent repeats.
- **PID follow**: three independent PID controllers (yaw, forward/back, up/down), all clamped to [-100, 100], RC commands at 50ms min interval.
- **Head tracking**: nearest-neighbor greedy assignment, EMA smoothing (α=0.8), stale tracks pruned after 1s.

## Known gaps

- No tests exist anywhere in the repo.
- No lint/typecheck/formatter config.
- No CI/CD pipeline.
