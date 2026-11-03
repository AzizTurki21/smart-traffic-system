/*
 * LoRa + RFID receiver for a tabletop model vehicle.
 * Target: Heltec Wireless Stick V1/V2 (SX1276); check board revision first.
 */
#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

#define LORA_FREQUENCY 868E6  // Must match transmitter; confirm local band.

// Onboard SX1276 pins for Heltec Wireless Stick V1.
static const int LORA_CS = 18;
static const int LORA_RST = 14;
static const int LORA_DIO0 = 26;
static const int LORA_SCK = 5;
static const int LORA_MISO = 19;
static const int LORA_MOSI = 27;

// Report lists GPIO22 as reset on the receiver and GPIO12/13/33 for LEDs.
// Here GPIO22 is used for the RC522 reset; keep radio reset on its onboard GPIO14.
static const int RFID_SS = 4;
static const int RFID_RST = 22;
static const int LED_RED = 12;
static const int LED_YELLOW = 13;
static const int LED_GREEN = 33;

MFRC522 reader(RFID_SS, RFID_RST);
String latestPacket;
String selectedLane;
bool atIntersection = false;
unsigned long lastTagAt = 0;

// Replace these example UIDs with values printed by your own tags.
const char* LANE_TAGS[][2] = {
  {"", "lane1"},
  {"", "lane2"},
  {"", "lane3"}
};
const char* INTERSECTION_TAG = "";

String uidToString(MFRC522::Uid* uid) {
  String value;
  for (byte i = 0; i < uid->size; ++i) {
    if (uid->uidByte[i] < 0x10) value += "0";
    value += String(uid->uidByte[i], HEX);
  }
  value.toUpperCase();
  return value;
}

void setVehicleLeds(const String& color) {
  digitalWrite(LED_RED, color == "red" ? HIGH : LOW);
  digitalWrite(LED_YELLOW, color == "yellow" ? HIGH : LOW);
  digitalWrite(LED_GREEN, color == "green" ? HIGH : LOW);
}

void showSelectedState() {
  if (atIntersection || selectedLane.isEmpty() || latestPacket.isEmpty()) {
    setVehicleLeds("off");
    return;
  }
  JsonDocument doc;
  if (deserializeJson(doc, latestPacket)) return;
  String color = doc["lanes"][selectedLane] | "red";
  if (color != "red" && color != "yellow" && color != "green") color = "red";
  setVehicleLeds(color);
}

void scanRfid() {
  if (!reader.PICC_IsNewCardPresent() || !reader.PICC_ReadCardSerial()) return;
  String uid = uidToString(&reader.uid);
  Serial.println("RFID UID: " + uid);
  lastTagAt = millis();

  if (strlen(INTERSECTION_TAG) > 0 && uid.equalsIgnoreCase(INTERSECTION_TAG)) {
    atIntersection = true;
    selectedLane = "";
    Serial.println("Intersection tag: vehicle LEDs off");
  } else {
    atIntersection = false;
    bool known = false;
    for (size_t i = 0; i < sizeof(LANE_TAGS) / sizeof(LANE_TAGS[0]); ++i) {
      if (strlen(LANE_TAGS[i][0]) > 0 && uid.equalsIgnoreCase(LANE_TAGS[i][0])) {
        selectedLane = LANE_TAGS[i][1];
        known = true;
        Serial.println("Selected " + selectedLane);
        break;
      }
    }
    if (!known) Serial.println("Unknown tag. Add this UID to the tag map.");
  }

  reader.PICC_HaltA();
  reader.PCD_StopCrypto1();
  showSelectedState();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  setVehicleLeds("off");

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("LoRa init failed; check board revision, pins, and frequency");
    while (true) delay(1000);
  }

  // RC522 shares SPI clock/data with LoRa and has its own chip-select line.
  reader.PCD_Init();
  Serial.println("Receiver ready. Scan lane and intersection tags to map their UIDs.");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0 && packetSize <= 200) {
    String incoming;
    while (LoRa.available()) incoming += static_cast<char>(LoRa.read());
    JsonDocument check;
    if (!deserializeJson(check, incoming)) {
      latestPacket = incoming;
      Serial.println("LoRa RX: " + latestPacket);
      showSelectedState();
    } else {
      Serial.println("Ignored invalid JSON radio packet");
    }
  }

  scanRfid();
  // Clear the vehicle display after the car leaves the intersection/tag zone.
  if (atIntersection && millis() - lastTagAt > 1500) {
    atIntersection = false;
    setVehicleLeds("off");
  }
  delay(5);
}
