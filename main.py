import argparse

from core.types import DroneType
from app.main import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tello computer vision app")
    parser.add_argument("--drone", default="mock", choices=["tello","mock"], help="Drone type")
    args = parser.parse_args()
    
    raise SystemExit(main(DroneType(args.drone)))
