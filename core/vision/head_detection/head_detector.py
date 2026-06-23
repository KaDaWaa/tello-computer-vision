from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from core.vision.bbox import BBox
from mediapipe.tasks.python.vision.face_detector import FaceDetector, FaceDetectorOptions
model_path = (
    Path(__file__).resolve().parent.parent / "models" / "mediapipe" / "blaze_face_full_range.tflite"
)

BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=str(model_path)),
    running_mode=VisionRunningMode.IMAGE,
)



class HeadDetector:
    def __init__(self):
        self.detector = FaceDetector.create_from_options(options)

    def detect(self, image)-> list[BBox]:
        if not isinstance(image, mp.Image):
            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=image
            )

        results = self.detector.detect(image)
        return [BBox.from_detection(detection) for detection in results.detections] or []