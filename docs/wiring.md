# Wiring notes

## Raspberry Pi 4 signal LEDs

The report lists BCM GPIO numbers. Confirm these against your model wiring before enabling GPIO output. Each LED must use a suitable series resistor and a safe common ground.

| Approach | Green | Red | Yellow |
| --- | ---: | ---: | ---: |
| lane1 | GPIO22 | GPIO17 | GPIO27 |
| lane2 | GPIO23 | GPIO25 | GPIO24 |
| lane3 | GPIO5 | GPIO26 | GPIO6 |

## Heltec Wireless Stick and RC522

The report records these receiver-side connections: red LED GPIO12, yellow LED GPIO13, green LED GPIO33, I2C SDA GPIO21, SPI SCK GPIO5, MOSI GPIO27, MISO GPIO19, and reset GPIO22. It does not make clear whether GPIO22 is the RC522 reset or another reset line, nor does it identify every radio pin or the board revision.

Heltec's official Wireless Stick V1 pinout identifies onboard LoRa CS GPIO18, SCK GPIO5, MISO GPIO19, MOSI GPIO27, reset GPIO14, and DIO0 GPIO26. The receiver sketch uses GPIO22 for the MFRC522 reset, and the built-in radio pins above for LoRa. Verify this against the exact board before wiring. Do not connect the external RC522 to a pin already used by the onboard radio or OLED.

## Heltec transmitter display

The report lists I2C SDA GPIO4 and SCL GPIO15 for the transmitter display. The sketch uses those pins for the onboard SSD1306 display. Radio SPI uses the board's separate onboard LoRa pins.

## Radio revision warning

Heltec Wireless Stick revisions are not interchangeable in firmware. V1/V2 use SX1276 and are compatible with the classic `LoRa` Arduino library used here. V3 changed to SX1262; use a compatible SX1262 driver and verify its pin mapping instead of uploading these sketches unchanged. The report does not state the revision. See Heltec's [hardware update log](https://docs.heltec.org/en/node/esp32/wireless_stick/hardware_update_log.html) and [V1 pinout](https://resource.heltec.cn/download/Wireless_Stick/Wireless_Stick.pdf).

## Power and RF

Do not power multiple LEDs or modules from a GPIO pin. Use appropriate resistors, stable regulated supplies, and shared ground where required. Confirm that both radios use the same supported frequency and antenna configuration. Check local radio rules before operating.
