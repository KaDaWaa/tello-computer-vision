from pathlib import Path

import cv2
import mediapipe as mp
from core.vision.hand_gestures.gesture_result import GestureDetection

model_path = (
    Path(__file__).resolve().parent.parent / "models" / "mediapipe" / "gesture_recognizer.task"
)

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=str(model_path)),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.5)

class GestureDetector:
    def __init__(self):
        self.recognizer = GestureRecognizer.create_from_options(options)

    def detect(self, image) -> list[GestureDetection]:
        if self.recognizer is None:
            raise RuntimeError("GestureRecognizer not initialized")
        
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=image)
        
        results = self.recognizer.recognize(image)  
        detections = []
        for hand_landmarks, raw_gestures in zip(results.hand_landmarks, results.gestures):
            gesture_name = raw_gestures[0].category_name if raw_gestures else None
            confidence = raw_gestures[0].score if raw_gestures else None
            detections.append(GestureDetection(gesture_name, confidence, hand_landmarks, raw_gestures))           
        
        return detections