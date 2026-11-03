# Architecture

The report describes a T-junction model with three controlled approaches.

1. A Raspberry Pi reads three camera feeds and runs a YOLOv8n model trained to identify priority vehicles.
2. A detection publishes the approach to MQTT on `SMdetection`.
3. The Raspberry Pi subscribes to that topic. It temporarily makes the detected approach green and the others red, then returns to the normal timed cycle.
4. The Pi publishes current light states to `SMTraffic` once per second.
5. A Heltec Wireless Stick at the intersection receives `SMTraffic` over MQTT and broadcasts it over LoRa.
6. A second Heltec in the model vehicle receives the LoRa packet. An MFRC522 reader identifies RFID tags along the model road. Lane tags select which signal state is shown on the vehicle; an intersection tag clears the display.

The implementation keeps the camera detector in a separate process from GPIO/MQTT control. A single detector process cycles over the camera feeds and loads one model instance to limit memory use. This is a practical reconstruction choice, not a claim about the lost original implementation.

## Normal timing

The report documents a demonstrator cycle with a 7-second green phase and a 3-second yellow phase per approach. Other approaches remain red. A priority event pauses the normal cycle while the selected approach receives priority, then resumes the cycle.

## Safety boundary

All timing, detection, and radio behavior here is for a tabletop model. Real traffic control requires certified equipment, rigorous safety analysis, redundant sensing, and authorized engineering.
