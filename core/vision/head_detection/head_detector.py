from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from .head_box import HeadBox

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

    def detect(self, image)-> list[HeadBox]:
        if not isinstance(image, mp.Image):
            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
            )

        results = self.detector.detect(image)
        return [HeadBox(x=int(detection.bounding_box.origin_x),
                        y=int(detection.bounding_box.origin_y),
                        w=int(detection.bounding_box.width),
                        h=int(detection.bounding_box.height))
                        .expanded(1.2, 1.2) for detection in results.detections]