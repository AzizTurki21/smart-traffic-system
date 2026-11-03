/*
 * MQTT-to-LoRa transmitter for Heltec Wireless Stick V1/V2 (SX1276).
 * Wireless Stick V3 uses SX1262 and needs a different radio driver.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <LoRa.h>
#include <Wire.h>
#include <U8g2lib.h>

#define WIFI_SSID       "CHANGE_ME"
#define WIFI_PASSWORD   "CHANGE_ME"
#define MQTT_HOST       "CHANGE_ME"
#define MQTT_PORT       8883
#define MQTT_USER       "CHANGE_ME"
#define MQTT_PASSWORD   "CHANGE_ME"
#define MQTT_TOPIC      "SMTraffic"
#define LORA_FREQUENCY  868E6  // Verify regional rules and both radio modules.

// Paste the root CA certificate supplied by your MQTT broker here.
// TLS connection intentionally fails until a valid CA is configured.
static const char MQTT_ROOT_CA[] PROGMEM = "";

// Heltec Wireless Stick V1 pinout from the manufacturer.
static const int LORA_CS = 18;
static const int LORA_RST = 14;
static const int LORA_DIO0 = 26;
static const int DISPLAY_SDA = 4;
static const int DISPLAY_SCL = 15;

WiFiClientSecure wifiClient;
PubSubClient mqtt(wifiClient);
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);
String latestState = "Waiting for MQTT";

void showText(const String& text) {
  display.clearBuffer();
  display.setFont(u8g2_font_6x10_tf);
  display.drawUTF8(0, 12, "Smart Traffic");
  display.drawUTF8(0, 28, text.c_str());
  display.sendBuffer();
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  if (String(topic) != MQTT_TOPIC || length == 0 || length > 200) return;
  String packet;
  for (unsigned int i = 0; i < length; ++i) packet += static_cast<char>(payload[i]);

  LoRa.beginPacket();
  LoRa.print(packet);
  int sent = LoRa.endPacket();
  if (sent == 1) {
    latestState = packet;
    showText("State sent over LoRa");
    Serial.println("LoRa TX: " + packet);
  } else {
    showText("LoRa send failed");
    Serial.println("LoRa transmit failed");
  }
}

void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = "smart-traffic-tx-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      mqtt.subscribe(MQTT_TOPIC, 1);
      showText("MQTT connected");
    } else {
      showText("MQTT retrying");
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(DISPLAY_SDA, DISPLAY_SCL);
  display.begin();
  showText("Starting");

  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQUENCY)) {
    showText("LoRa init failed");
    while (true) delay(1000);
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  wifiClient.setCACert(MQTT_ROOT_CA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(256);
  showText("WiFi connected");
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  delay(5);
}
