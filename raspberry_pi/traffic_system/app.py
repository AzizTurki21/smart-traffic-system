from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import os
import queue
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from .config import camera_map, env_bool, env_int
from .controller import TrafficController
from .detector import detector_process
from .hardware import ConsoleOutput, GpioOutput

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def create_mqtt_client(on_detection):
    import paho.mqtt.client as mqtt

    host = os.getenv("MQTT_HOST", "").strip()
    if not host:
        raise RuntimeError("Set MQTT_HOST to your broker address")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=os.getenv("MQTT_CLIENT_ID", "smart-traffic-pi"))
    username, password = os.getenv("MQTT_USERNAME"), os.getenv("MQTT_PASSWORD")
    if username:
        client.username_pw_set(username, password)
    if env_bool("MQTT_TLS", True):
        client.tls_set()

    detection_topic = os.getenv("MQTT_DETECTION_TOPIC", "SMdetection")

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info("Connected to MQTT broker; subscribing to %s", detection_topic)
            client.subscribe(detection_topic, qos=1)
        else:
            log.error("MQTT connection failed: %s", reason_code)

    def on_message(client, userdata, message):
        on_detection(message.payload)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, env_int("MQTT_PORT", 8883), keepalive=30)
    client.loop_start()
    return client


def run_simulation() -> None:
    output = ConsoleOutput()
    controller = TrafficController(output, None)
    stop = threading.Event()

    def read_commands() -> None:
        while not stop.is_set():
            try:
                line = input("simulate> ").strip()
            except EOFError:
                stop.set()
                break
            if line.lower() in {"q", "quit", "exit"}:
                stop.set()
            elif line.lower().startswith("priority "):
                lane = line.split(maxsplit=1)[1]
                controller.on_detection(json.dumps({"lane": lane, "class": "ambulance", "confidence": 0.99}))
            else:
                print("Commands: priority lane1|lane2|lane3, q")

    threading.Thread(target=read_commands, daemon=True).start()
    print("Simulating traffic lights. Type 'priority lane2' or 'q'.")
    try:
        while not stop.is_set():
            controller.tick()
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        output.close()


def run_hardware() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    output = GpioOutput() if env_bool("GPIO_ENABLED", False) else ConsoleOutput()
    events: mp.Queue = mp.Queue(maxsize=20)
    incoming: queue.Queue = queue.Queue(maxsize=20)
    stop = mp.Event()
    controller = TrafficController(output, None)

    def queue_detection(payload: bytes) -> None:
        try:
            incoming.put_nowait(payload)
        except queue.Full:
            log.warning("MQTT detection queue is full; dropping event")

    client = create_mqtt_client(queue_detection)

    cameras = camera_map()
    detector = mp.Process(
        target=detector_process,
        args=(cameras, os.getenv("MODEL_PATH", "../models/best.pt"),
              float(os.getenv("CONFIDENCE_THRESHOLD", "0.70")),
              env_int("FRAME_SKIP", 5), env_int("FRAME_WIDTH", 640),
              env_int("FRAME_HEIGHT", 360),
              float(os.getenv("DETECTION_COOLDOWN_SECONDS", "10")), events, stop),
        name="camera-detector",
        daemon=True,
    )
    detector.start()
    state_topic = os.getenv("MQTT_STATE_TOPIC", "SMTraffic")

    try:
        while True:
            try:
                event = events.get_nowait()
                client.publish(os.getenv("MQTT_DETECTION_TOPIC", "SMdetection"),
                               json.dumps(event), qos=1)
            except queue.Empty:
                pass
            try:
                while True:
                    controller.on_detection(incoming.get_nowait())
            except queue.Empty:
                pass
            controller.tick()
            client.publish(state_topic, controller.state_payload(), qos=1, retain=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        log.info("Stopping controller")
    finally:
        stop.set()
        detector.join(timeout=3)
        if detector.is_alive():
            detector.terminate()
            detector.join(timeout=1)
        client.loop_stop()
        client.disconnect()
        output.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart traffic tabletop prototype")
    parser.add_argument("--simulate", action="store_true", help="Run timing without GPIO, cameras, or MQTT")
    args = parser.parse_args()
    if args.simulate:
        run_simulation()
    else:
        run_hardware()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
