# Setup guide

## 1. Prepare the model

The original trained weights and image dataset were not included in the report file. If you still have the training images and YOLO labels, arrange them according to `raspberry_pi/config/dataset.example.yaml`, train with the included helper, and copy `runs/detect/smart_traffic/weights/best.pt` to `models/best.pt`. Otherwise, obtain or recreate a suitable labeled dataset first. The demo will not start camera detection without a compatible weights file.

## 2. Prepare MQTT

Create an MQTT broker account or use a broker on your own network. Set host, port, username, password, and TLS options in environment variables based on that broker's connection details. The code does not hard-code public broker credentials. Use the same broker settings on the Raspberry Pi and Heltec transmitter.

## 3. Install Pi dependencies

Use a Raspberry Pi OS image supported by your camera and GPIO packages. Install Python 3, OpenCV system dependencies, and the Raspberry Pi GPIO library appropriate for that OS. Then:

```bash
cd raspberry_pi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `../.env.example` to `.env` from the `raspberry_pi` folder, or export those values into the service environment. Set broker details, `MODEL_PATH` to the actual weights file, and `PRIORITY_CLASSES` to the exact names in the model. The detector reports the model names on startup.

## 4. Identify cameras

Run a short OpenCV camera enumeration on the Pi and check the view for each index. Set `CAMERAS` to the camera index and lane mapping, for example `0:lane1,1:lane2,2:lane3`. The mapping must match the physical camera placement. Lower frame dimensions or increase `FRAME_SKIP` if inference is slow.

## 5. Install Arduino libraries

For a V1/V2 Wireless Stick, install the ESP32 board support package and these Arduino libraries:

- LoRa by Sandeep Mistry (SX127x boards only)
- PubSubClient
- ArduinoJson
- MFRC522 (receiver sketch)
- U8g2 (transmitter OLED)

The board revision is unknown from the report. The sketches' pin map targets SX1276 Wireless Stick V1/V2; V3 uses SX1262 and requires porting to a compatible driver.

For the transmitter's TLS connection, paste the broker's root CA certificate into `MQTT_ROOT_CA` in `transmitter.ino`. The sketch uses certificate verification and will not connect while the certificate is empty. Never use a credentialed public broker without certificate verification.

## 6. Scan RFID tags

Upload the receiver sketch, open Serial Monitor, and scan each lane tag and the intersection tag. Copy the printed UIDs into the sketch's tag map, recompile, and upload. The receiver will show no lane-specific state until its UID map is filled in.

## 7. Start and verify in stages

1. Run `python -m traffic_system --simulate` on a computer to inspect the timing and event flow.
2. Start the Pi with `GPIO_ENABLED=false` and confirm MQTT messages arrive.
3. Test one LED set with the bench supply disconnected from any traffic equipment; verify pin mapping and polarity.
4. Enable GPIO output for the tabletop model only.
5. Add the LoRa transmitter and receiver; check Serial logs, then test one RFID lane tag and the intersection tag.
6. Connect cameras and model weights last, then tune resolution, frame skipping, and confidence threshold.

Do not treat this educational prototype as a road safety system.
