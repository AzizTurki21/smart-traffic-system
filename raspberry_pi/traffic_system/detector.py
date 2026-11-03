from __future__ import annotations

import logging
import multiprocessing as mp
import os
import queue
import time
from pathlib import Path

log = logging.getLogger(__name__)


def detector_process(cameras: list[tuple[int, str]], model_path: str, confidence: float,
                     frame_skip: int, width: int, height: int,
                     cooldown: float, events: mp.Queue, stop: mp.Event) -> None:
    """One model process cycles through cameras to avoid loading one model per camera."""
    import cv2
    from ultralytics import YOLO

    model_file = Path(model_path).expanduser().resolve()
    if not model_file.is_file():
        log.error("YOLO weights missing: %s. Camera detection is disabled.", model_file)
        return
    model = YOLO(str(model_file))
    names = model.names
    wanted = {part.strip().lower() for part in os.getenv(
        "PRIORITY_CLASSES", "ambulance,police,fire_truck"
    ).split(",")}
    class_ids = [int(i) for i, name in names.items() if str(name).lower() in wanted]
    if not class_ids:
        log.error("No priority class names %s found in model names %s", wanted, names)
        return

    captures: dict[int, object] = {}
    frame_counts = {index: 0 for index, _ in cameras}
    last_event: dict[int, float] = {}
    try:
        for index, lane in cameras:
            cap = cv2.VideoCapture(index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            if not cap.isOpened():
                log.error("Could not open camera %s for %s", index, lane)
                cap.release()
            else:
                captures[index] = cap

        if not captures:
            log.error("No cameras opened")
            return

        while not stop.is_set():
            for index, lane in cameras:
                cap = captures.get(index)
                if cap is None:
                    continue
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.1)
                    continue
                frame_counts[index] += 1
                if frame_counts[index] % max(1, frame_skip) != 0:
                    continue
                result = model.predict(frame, imgsz=max(width, height), conf=confidence,
                                       classes=class_ids, verbose=False)[0]
                if result.boxes is None or len(result.boxes) == 0:
                    continue
                best = max(result.boxes, key=lambda box: float(box.conf[0]))
                now = time.monotonic()
                if now - last_event.get(index, 0.0) < cooldown:
                    continue
                label = str(names[int(best.cls[0])])
                payload = {
                    "lane": lane,
                    "class": label,
                    "confidence": float(best.conf[0]),
                    "camera": index,
                    "timestamp": time.time(),
                }
                try:
                    events.put(payload, timeout=0.2)
                    last_event[index] = now
                except queue.Full:
                    log.warning("Detection event queue is full; dropping event")
    finally:
        for cap in captures.values():
            cap.release()

