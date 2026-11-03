"""Train a YOLOv8n model using a dataset YAML supplied on the command line."""
from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to your dataset YAML")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None, help="For example: cpu, 0, or mps")
    args = parser.parse_args()

    data_path = Path(args.data).expanduser().resolve()
    if not data_path.is_file():
        parser.error(f"Dataset YAML not found: {data_path}")

    model = YOLO("yolov8n.pt")
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
        project="runs/detect",
        name="smart_traffic",
    )


if __name__ == "__main__":
    main()
