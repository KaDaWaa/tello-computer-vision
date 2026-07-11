"""
Taking only wanted gestures from dataset, crop the images to hand only and rearrange the dataset into a new folder structure.
"""

from dataclasses import dataclass
from pathlib import Path
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions
import numpy as np
from PIL import Image

parent_dir = Path(__file__).parent

options = vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(parent_dir / "hand_landmarker.task")),
    num_hands=1,
)

hand_landmarker = vision.HandLandmarker.create_from_options(options)


# ============================================================================
# CONFIGURATION: Change this to switch between "train", "val", or "test"
# ============================================================================
DATASET_SPLIT = "val"

preprocessed_dataset_path = parent_dir / "./preprocessed_dataset"

# Map dataset splits to their paths
DATASET_PATHS = {
    "train": {
        "images": preprocessed_dataset_path / "images/train",
        "labels": preprocessed_dataset_path / "labels/train",
        "output": parent_dir / "dataset" / "images/train",
    },
    "val": {
        "images": preprocessed_dataset_path / "images/val",
        "labels": preprocessed_dataset_path / "labels/val",
        "output": parent_dir / "dataset" / "images/val",
    },
    "test": {
        "images": preprocessed_dataset_path / "images/test",
        "labels": preprocessed_dataset_path / "labels/test",
        "output": parent_dir / "dataset" / "images/test",
    },
}

processed_dataset_path = parent_dir / "dataset"


MAX_IMAGES_PER_GESTURE = 200
wanted_gestures = {
    # 9: "like",
    # 1: "dislike",
    # 2: "fist",
    # 21: "stop",
    # 14: "ok",
    # 5: "grip",
    # 15: "one",
    # 17: "peace",
    # 25: "three2",
    # 3: "four",
    # 0: "call",
    4: "none",
    6: "none",
    7: "none",
    8: "none",
    10: "none",
    11: "none",
    12: "none",
    13: "none",
    18: "none",
    19: "none",
    20: "none",
    22: "none",
    23: "none",
    24: "none",
    26: "none",
    27: "none",
    28: "none",
    29: "none",
    30: "none",
    31: "none",
    32: "none",
    33: "none"
}

class_name_count = {
    # "like": 0,
    # "dislike": 0,
    # "fist": 0,
    # "stop": 0,
    # "ok": 0,
    # "grip": 0,
    # "one": 0,
    # "peace": 0,
    # "three2": 0,
    # "four": 0,
    # "call": 0,
    "none": 0
}

# Bounding box parameters for cropping the hand from the image
MARGIN = 0.15
MIN_WIDTH = 80
MIN_HEIGHT = 80

stats = {
    "saved": 0,
    "too_small": 0,
    "no_hand": 0,
}


@dataclass
class ImageInfo:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float


def yolo_to_xyxy(x, y, w, h, img_w, img_h):
    x1 = int((x - w / 2) * img_w)
    y1 = int((y - h / 2) * img_h)
    x2 = int((x + w / 2) * img_w)
    y2 = int((y + h / 2) * img_h)

    return x1, y1, x2, y2


def add_margin(x1, y1, x2, y2, img_w, img_h, margin=0.15):
    width = x2 - x1
    height = y2 - y1

    x1 -= width * margin
    y1 -= height * margin
    x2 += width * margin
    y2 += height * margin

    # Clamp to image boundaries
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(img_w, int(x2))
    y2 = min(img_h, int(y2))

    return x1, y1, x2, y2


def extract_image_info(image_path):
    gestures_info = []
    with open(image_path, "r") as f:
        lines = f.readlines()
        for line in lines:
            class_id, x_center, y_center, width, height = map(
                float, line.strip().split()
            )
            class_id = int(class_id)
            if class_id in wanted_gestures:
                gestures_info.append(
                    ImageInfo(
                        class_id=class_id,
                        x_center=x_center,
                        y_center=y_center,
                        width=width,
                        height=height,
                    )
                )
    return gestures_info


def validate_crop(cropped_img):
    try:
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=np.asarray(cropped_img),
        )

        result = hand_landmarker.detect(mp_image)
        return len(result.hand_landmarks) == 1

    except Exception:
        return False


def crop_and_save_image(
    image_path, image_info: ImageInfo, class_name: str, image_index: int, output_path: Path
):

    img = Image.open(image_path)
    img_w, img_h = img.size
    x1, y1, x2, y2 = yolo_to_xyxy(
        image_info.x_center,
        image_info.y_center,
        image_info.width,
        image_info.height,
        img_w,
        img_h,
    )
    x1, y1, x2, y2 = add_margin(x1, y1, x2, y2, img_w, img_h, margin=MARGIN)

    crop_w = x2 - x1
    crop_h = y2 - y1
    if crop_w < MIN_WIDTH or crop_h < MIN_HEIGHT:
        stats["too_small"] += 1
        return False

    cropped_img = img.crop((x1, y1, x2, y2)).convert("RGB")
    validation_img = cropped_img.resize((256, 256))

    if validate_crop(validation_img):
        cropped_img.save(output_path / f"{class_name}" / f"{image_index}.jpg")
        stats["saved"] += 1
        return True
    else:
        stats["no_hand"] += 1

    return False


if __name__ == "__main__":
    # Get paths for the selected dataset split
    paths = DATASET_PATHS[DATASET_SPLIT]
    images_path = paths["images"]
    labels_path = paths["labels"]
    output_path = paths["output"]

    output_path.mkdir(parents=True, exist_ok=True)
    for class_name in wanted_gestures.values():
        (output_path / class_name).mkdir(parents=True, exist_ok=True)

    print(f"Processing {DATASET_SPLIT} dataset...")
    for label_file in labels_path.glob("*.txt"):
        image_file = images_path / f"{label_file.stem}.jpg"
        if not image_file.exists():
            print(f"Image file {image_file} does not exist for label {label_file}")
            continue

        gestures_info = extract_image_info(label_file)
        for image_info in gestures_info:
            class_name = wanted_gestures[image_info.class_id]
            if class_name_count[class_name] < MAX_IMAGES_PER_GESTURE:
                if crop_and_save_image(
                    image_file, image_info, class_name, class_name_count[class_name], output_path
                ):
                    class_name_count[class_name] += 1
            else:
                print(
                    f"Reached max images for class {class_name}, skipping {image_file}"
                )

    print(f"Processing {DATASET_SPLIT} dataset complete.")
    for category, count in stats.items():
        print(f"{category.capitalize()}: {count}")