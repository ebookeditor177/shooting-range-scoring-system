/**
 * Shooting Range ESP32 Firmware
 * 
 * Reads piezo sensor inputs, detects hits, calculates accuracy,
 * and sends events to the backend via WebSocket.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <vector>

// ============================================================================
// CONFIGURATION
// ============================================================================

// WiFi Configuration
const char* WIFI_SSID = "YourWiFiSSID";
const char* WIFI_PASSWORD = "YourWiFiPassword";

// Server Configuration
const char* SERVER_HOST = "192.168.1.100";
const uint16_t SERVER_PORT = 8000;
const char* SERVER_PATH = "/ws/device/";

// Device Configuration
const char* DEVICE_ID = "esp32-001";
const int LANE_NUMBER = 1;

// Sensor Pins (analog inputs)
const int SENSOR_PINS[] = { 34, 35, 36, 37, 38 };  // VP, VN, D34, D35, D36
const char* SENSOR_NAMES[] = { "head", "chest", "stomach", "left_leg", "right_leg" };
const int NUM_SENSORS = 5;

// Hit Detection Settings
const int HIT_THRESHOLD = 100;        // Minimum analog value to detect a hit
const unsigned long DEBOUNCE_MS = 50;  // Debounce time in milliseconds
const unsigned long MIN_HIT_INTERVAL_MS = 100;  // Minimum time between hits on same sensor

// Heartbeat Settings
const unsigned long HEARTBEAT_INTERVAL_MS = 5000;  // Send heartbeat every 5 seconds

// ============================================================================
// GLOBAL STATE
// ============================================================================

WebSocketsClient webSocket;
bool isConnected = false;
unsigned long lastHeartbeat = 0;
unsigned long lastReconnectAttempt = 0;

// Sensor state
struct SensorState {
    int pin;
    const char* name;
    unsigned long lastHitTime;
    bool wasAboveThreshold;
};

std::vector<SensorState> sensors;

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

String getTimestamp() {
    unsigned long ms = millis();
    time_t now = time(nullptr);
    struct tm timeinfo;
    gmtime_r(&now, &timeinfo);
    
    char buffer[32];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &timeinfo);
    
    // Add milliseconds
    String result = String(buffer);
    result += ".";
    result += String(ms % 1000);
    result += "Z";
    
    return result;
}

void sendJson(const JsonDocument& doc) {
    if (isConnected) {
        String output;
        serializeJson(doc, output);
        webSocket.sendTXT(output);
    }
}

void sendRegistration() {
    StaticJsonDocument<256> doc;
    doc["type"] = "register_device";
    doc["device_id"] = DEVICE_ID;
    doc["lane"] = LANE_NUMBER;
    
    JsonArray sensorArray = doc.createNestedArray("sensors");
    for (int i = 0; i < NUM_SENSORS; i++) {
        sensorArray.add(SENSOR_NAMES[i]);
    }
    
    doc["firmware"] = "v1.0.0";
    doc["timestamp"] = getTimestamp();
    
    sendJson(doc);
    Serial.println("Sent registration");
}

void sendHeartbeat() {
    StaticJsonDocument<128> doc;
    doc["type"] = "heartbeat";
    doc["device_id"] = DEVICE_ID;
    doc["timestamp"] = getTimestamp();
    
    sendJson(doc);
    Serial.println("Sent heartbeat");
}

void sendHit(const char* position, int accuracy, int rawStrength) {
    StaticJsonDocument<256> doc;
    doc["type"] = "hit";
    doc["device_id"] = DEVICE_ID;
    doc["lane"] = LANE_NUMBER;
    doc["position"] = position;
    doc["accuracy"] = accuracy / 1024.0;  // Normalize to 0-1
    doc["raw_strength"] = rawStrength;
    doc["event_timestamp"] = getTimestamp();
    
    sendJson(doc);
    Serial.printf("Sent hit: %s, accuracy: %.2f\n", position, accuracy / 1024.0);
}

// ============================================================================
// WEBSOCKET CALLBACKS
// ============================================================================

void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("WebSocket disconnected");
            isConnected = false;
            break;
            
        case WStype_CONNECTED:
            Serial.println("WebSocket connected");
            isConnected = true;
            sendRegistration();
            break;
            
        case WStype_TEXT:
            Serial.printf("Received: %s\n", payload);
            // Handle server messages if needed
            break;
            
        case WStype_ERROR:
            Serial.println("WebSocket error");
            break;
            
        default:
            break;
    }
}

// ============================================================================
// SENSOR PROCESSING
// ============================================================================

void initSensors() {
    for (int i = 0; i < NUM_SENSORS; i++) {
        SensorState sensor;
        sensor.pin = SENSOR_PINS[i];
        sensor.name = SENSOR_NAMES[i];
        sensor.lastHitTime = 0;
        sensor.wasAboveThreshold = false;
        
        pinMode(sensor.pin, INPUT);
        sensors.push_back(sensor);
        
        Serial.printf("Initialized sensor: %s on pin %d\n", sensor.name, sensor.pin);
    }
}

void processSensors() {
    unsigned long currentTime = millis();
    
    for (auto& sensor : sensors) {
        int value = analogRead(sensor.pin);
        bool isAboveThreshold = value > HIT_THRESHOLD;
        
        // Detect rising edge (hit start)
        if (isAboveThreshold && !sensor.wasAboveThreshold) {
            // Check debounce
            if (currentTime - sensor.lastHitTime > MIN_HIT_INTERVAL_MS) {
                // Calculate accuracy based on signal strength
                // Higher value = better accuracy (closer to center of sensor)
                int accuracy = map(value, HIT_THRESHOLD, 1024, 0, 1024);
                accuracy = constrain(accuracy, 0, 1024);
                
                sendHit(sensor.name, accuracy, value);
                sensor.lastHitTime = currentTime;
            }
        }
        
        sensor.wasAboveThreshold = isAboveThreshold;
    }
}

// ============================================================================
// WIFI & RECONNECT
// ============================================================================

void connectWiFi() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected");
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nWiFi connection failed");
    }
}

void connectWebSocket() {
    Serial.println("Connecting to WebSocket server...");
    webSocket.begin(SERVER_HOST, SERVER_PORT, SERVER_PATH);
    webSocket.onEvent(onWebSocketEvent);
    webSocket.setReconnectInterval(5000);
}

// ============================================================================
// MAIN SETUP & LOOP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n=== Shooting Range ESP32 Firmware ===");
    Serial.printf("Device ID: %s\n", DEVICE_ID);
    Serial.printf("Lane: %d\n", LANE_NUMBER);
    
    // Initialize sensors
    initSensors();
    
    // Connect to WiFi
    connectWiFi();
    
    // Connect to WebSocket
    connectWebSocket();
}

void loop() {
    unsigned long currentTime = millis();
    
    // Process WebSocket events
    webSocket.loop();
    
    // Process sensors
    processSensors();
    
    // Send heartbeat
    if (isConnected && currentTime - lastHeartbeat > HEARTBEAT_INTERVAL_MS) {
        sendHeartbeat();
        lastHeartbeat = currentTime;
    }
    
    // Handle reconnection
    if (!isConnected && currentTime - lastReconnectAttempt > 5000) {
        if (WiFi.status() == WL_CONNECTED) {
            connectWebSocket();
        } else {
            connectWiFi();
        }
        lastReconnectAttempt = currentTime;
    }
    
    delay(1);  // Small delay to prevent watchdog issues
}
