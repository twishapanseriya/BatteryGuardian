// ============================================================================
// BATTERYGUARDIAN AI - COMPLETE ALL-IN-ONE ESP32 FIRMWARE (VERIFIED)
// ============================================================================
// Target: ESP32 Dev Module (WROOM-32)
// Battery: 3S1P Li-ion (IMR-18650, 11.1V Nom, 12.6V Max, 1200mAh)
// Discharge Load: 100-ohm, 50W Wirewound Resistor
// Sensors:
//   - 3S Differential Voltage Ladder (33k Top / 10k Bottom + 100nF RC filter)
//     Pins: GPIO 34 (Tap 1), GPIO 35 (Tap 2), GPIO 32 (Tap 3)
//   - INA219 I2C Current Sensor (SDA: GPIO 21, SCL: GPIO 22, Addr: 0x40)
//   - DS18B20 1-Wire Digital Probes (GPIO 4, 4.2k-4.7k pull-up)
//   - SSD1306 128x64 OLED (SDA: GPIO 21, SCL: GPIO 22, Addr: 0x3C)
// BLE GATT Server:
//   - Service UUID: 4fafc201-1fb5-459e-8fcc-c5c9c331914b
//   - Telemetry Char UUID (Notify): beb5483e-36e1-4688-b7f5-ea07361b26a8
//   - Rate: 1000 ms (1 Hz)
// ============================================================================

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ============================================================================
// HARDWARE PIN DEFINITIONS (CONFIRMED)
// ============================================================================
#define SDA_PIN 21
#define SCL_PIN 22

#define DS18B20_PIN 4

#define CELL1_ADC_PIN 34  // ADC1_CH6: Cell 1 Tap (0 - 4.2V)
#define CELL2_ADC_PIN 35  // ADC1_CH7: Cell 2 Tap (0 - 8.4V)
#define CELL3_ADC_PIN 32  // ADC1_CH4: Cell 3 / Pack Tap (0 - 12.6V)

// ============================================================================
// VOLTAGE DIVIDER CONFIGURATION (33k Top / 10k Bottom)
// ============================================================================
const float R_TOP = 33000.0f;
const float R_BOTTOM = 10000.0f;
const float DIVIDER_RATIO = R_BOTTOM / (R_TOP + R_BOTTOM); // 10/43 ≈ 0.232558f

// ============================================================================
// PER-CHANNEL HARDWARE CALIBRATION MULTIPLIERS
// Adjust these against a calibrated Digital Multimeter (DMM) to nullify
// resistor tolerance variations (e.g., 1% error) and ADC non-linearities.
// Formula: k = V_measured_by_DMM / V_reported_by_ESP32
// ============================================================================
const float CALIBRATION_K1 = 1.0000f; // Node 1 multiplier
const float CALIBRATION_K2 = 1.0000f; // Node 2 multiplier
const float CALIBRATION_K3 = 1.0000f; // Node 3 multiplier

const int ADC_RESOLUTION_BITS = 12;
const int ADC_MAX_RAW = 4095;
const float ADC_REFERENCE_VOLTAGE = 3.30f;
const int ADC_SAMPLES = 16;

// ============================================================================
// BATTERY PARAMETERS & LIMITS (3S Li-ion IMR-18650)
// ============================================================================
const float CELL_MIN_VOLTAGE = 2.50f;
const float CELL_MAX_VOLTAGE = 4.25f;
const float MAX_CELL_IMBALANCE = 0.100f; // 100 mV
const float MAX_TEMP_WARNING_C = 55.0f;
const float CURRENT_ACTIVE_THRESHOLD_A = 0.020f; // 20 mA

// ============================================================================
// OLED & INA219 PERIPHERALS
// ============================================================================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDRESS 0x3C
#define INA219_ADDRESS 0x40

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
Adafruit_INA219 ina219(INA219_ADDRESS);
OneWire oneWire(DS18B20_PIN);
DallasTemperature tempSensors(&oneWire);

bool oledOK = false;
bool ina219OK = false;
int sensorCount = 0;

// ============================================================================
// BLE GATT DEFINITIONS
// ============================================================================
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLEServer *pServer = nullptr;
BLECharacteristic *pTelemetryChar = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("[BLE] Flutter Client Connected.");
    }
    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("[BLE] Flutter Client Disconnected.");
    }
};

// ============================================================================
// STATE & TELEMETRY VARIABLES
// ============================================================================
float node1_v = 0.0f;
float node2_v = 0.0f;
float node3_v = 0.0f;

float cell1_v = 0.0f;
float cell2_v = 0.0f;
float cell3_v = 0.0f;
float pack_voltage_v = 0.0f;
float cell_imbalance_v = 0.0f;

float bus_voltage_v = 0.0f;
float current_a = 0.0f;
float power_w = 0.0f;

float temp1_c = 25.0f;
float temp2_c = 25.0f;
float temp3_c = 25.0f;
float avg_temp_c = 25.0f;

float discharged_mah = 0.0f;
float energy_mwh = 0.0f;
char battery_state[12] = "IDLE";
uint32_t cycle_number = 1;

bool voltageWarning = false;
bool imbalanceWarning = false;
bool temperatureWarning = false;

char json_payload[256];

// Timing track
unsigned long last_adc_ms = 0;
unsigned long last_oled_ms = 0;
unsigned long last_telemetry_ms = 0;
unsigned long last_loop_ms = 0;

// ============================================================================
// ADC & VOLTAGE CONVERSION
// ============================================================================
float readADCVoltage(int pin) {
    uint32_t total = 0;
    for (int i = 0; i < ADC_SAMPLES; i++) {
        total += analogRead(pin);
        delayMicroseconds(150);
    }
    float rawAverage = (float)total / (float)ADC_SAMPLES;
    return (rawAverage / (float)ADC_MAX_RAW) * ADC_REFERENCE_VOLTAGE;
}

inline float convertDividerVoltage(float adcVoltage, float cal_k) {
    return (adcVoltage / DIVIDER_RATIO) * cal_k;
}

// ============================================================================
// SENSORS ACQUISITION ROUTINE
// ============================================================================
void updateAllSensors(unsigned long delta_ms) {
    // 1. Read ADC node voltages
    float adc1 = readADCVoltage(CELL1_ADC_PIN);
    float adc2 = readADCVoltage(CELL2_ADC_PIN);
    float adc3 = readADCVoltage(CELL3_ADC_PIN);

    // 2. Scale via Divider Ratio (10k / 43k) & Apply Calibration Multipliers
    node1_v = convertDividerVoltage(adc1, CALIBRATION_K1);
    node2_v = convertDividerVoltage(adc2, CALIBRATION_K2);
    node3_v = convertDividerVoltage(adc3, CALIBRATION_K3);

    // 3. Calculate Differential Cell Voltages
    cell1_v = node1_v;
    cell2_v = node2_v - node1_v;
    cell3_v = node3_v - node2_v;
    pack_voltage_v = node3_v;

    if (cell1_v < 0.0f) cell1_v = 0.0f;
    if (cell2_v < 0.0f) cell2_v = 0.0f;
    if (cell3_v < 0.0f) cell3_v = 0.0f;
    if (pack_voltage_v < 0.0f) pack_voltage_v = 0.0f;

    // 4. Cell Imbalance
    float minC = cell1_v;
    float maxC = cell1_v;
    if (cell2_v < minC) minC = cell2_v;
    if (cell3_v < minC) minC = cell3_v;
    if (cell2_v > maxC) maxC = cell2_v;
    if (cell3_v > maxC) maxC = cell3_v;
    cell_imbalance_v = maxC - minC;

    // 5. Read INA219
    if (ina219OK) {
        bus_voltage_v = ina219.getBusVoltage_V();
        float current_ma = ina219.getCurrent_mA();
        float power_mw = ina219.getPower_mW();
        current_a = current_ma / 1000.0f;
        power_w = power_mw / 1000.0f;
    } else {
        bus_voltage_v = pack_voltage_v;
        current_a = 0.0f;
        power_w = 0.0f;
    }

    // 6. Read DS18B20 Temperatures
    if (sensorCount > 0) {
        float r1 = tempSensors.getTempCByIndex(0);
        float r2 = (sensorCount > 1) ? tempSensors.getTempCByIndex(1) : r1;
        float r3 = (sensorCount > 2) ? tempSensors.getTempCByIndex(2) : r1;
        
        if (!isnan(r1) && r1 > -50.0f && r1 < 125.0f) temp1_c = r1;
        if (!isnan(r2) && r2 > -50.0f && r2 < 125.0f) temp2_c = r2;
        if (!isnan(r3) && r3 > -50.0f && r3 < 125.0f) temp3_c = r3;
        
        avg_temp_c = (temp1_c + temp2_c + temp3_c) / 3.0f;
        
        // Request next asynchronous reading
        tempSensors.requestTemperatures();
    } else {
        temp1_c = 25.0f; temp2_c = 25.0f; temp3_c = 25.0f; avg_temp_c = 25.0f;
    }

    // 7. Coulomb Counting & State Machine
    float delta_hours = (float)delta_ms / 3600000.0f;
    if (current_a > CURRENT_ACTIVE_THRESHOLD_A) {
        strcpy(battery_state, "DISCHARGE");
        discharged_mah += (current_a * 1000.0f) * delta_hours;
        energy_mwh += (power_w * 1000.0f) * delta_hours;
    } else if (current_a < -CURRENT_ACTIVE_THRESHOLD_A) {
        strcpy(battery_state, "CHARGE");
    } else {
        strcpy(battery_state, "IDLE");
    }

    // 8. Warning Checks
    voltageWarning = (cell1_v < CELL_MIN_VOLTAGE || cell1_v > CELL_MAX_VOLTAGE ||
                      cell2_v < CELL_MIN_VOLTAGE || cell2_v > CELL_MAX_VOLTAGE ||
                      cell3_v < CELL_MIN_VOLTAGE || cell3_v > CELL_MAX_VOLTAGE);
    imbalanceWarning = (cell_imbalance_v > MAX_CELL_IMBALANCE);
    temperatureWarning = (temp1_c > MAX_TEMP_WARNING_C || temp2_c > MAX_TEMP_WARNING_C || temp3_c > MAX_TEMP_WARNING_C);
}

// ============================================================================
// OLED DISPLAY UPDATE
// ============================================================================
void updateOLEDDisplay() {
    if (!oledOK) return;

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);

    // Header with BLE Status
    display.setCursor(0, 0);
    display.print("BAT GUARDIAN ");
    display.print(deviceConnected ? "[BLE]" : "[--]");
    display.drawLine(0, 9, 127, 9, SSD1306_WHITE);

    // Pack Voltage & Current
    display.setCursor(0, 12);
    display.print("V: ");
    display.print(pack_voltage_v, 2);
    display.print("V  I:");
    display.print(current_a, 2);
    display.print("A");

    // Cells 1 & 2
    display.setCursor(0, 24);
    display.print("C1:");
    display.print(cell1_v, 2);
    display.print(" C2:");
    display.print(cell2_v, 2);

    // Cell 3 & Imbalance
    display.setCursor(0, 36);
    display.print("C3:");
    display.print(cell3_v, 2);
    display.print(" dV:");
    display.print((int)(cell_imbalance_v * 1000.0f));
    display.print("mV");

    // Temp & Status
    display.setCursor(0, 48);
    display.print("T:");
    display.print((int)temp1_c);
    display.print("/");
    display.print((int)temp2_c);
    display.print("C ");

    if (voltageWarning || imbalanceWarning || temperatureWarning) {
        display.print("!WARN!");
    } else {
        display.print(battery_state);
    }

    display.display();
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
    Serial.begin(115200);
    delay(1500);

    Serial.println("\n==================================================");
    Serial.println("           BATTERYGUARDIAN AI - ESP32             ");
    Serial.println("        Real-Time Battery Telemetry Node          ");
    Serial.println("==================================================");

    // 1. I2C Bus & OLED
    Wire.begin(SDA_PIN, SCL_PIN);
    if (display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
        oledOK = true;
        display.clearDisplay();
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(0, 10);
        display.println("BATTERY GUARDIAN");
        display.setCursor(0, 25);
        display.println("Starting Telemetry...");
        display.display();
        Serial.println("[INIT] OLED: OK");
    } else {
        oledOK = false;
        Serial.println("[INIT] OLED: FAILED");
    }

    // 2. INA219
    if (ina219.begin()) {
        ina219OK = true;
        ina219.setCalibration_32V_2A();
        Serial.println("[INIT] INA219: OK");
    } else {
        ina219OK = false;
        Serial.println("[INIT] INA219: FAILED");
    }

    // 3. DS18B20 1-Wire
    tempSensors.begin();
    sensorCount = tempSensors.getDeviceCount();
    Serial.printf("[INIT] DS18B20 Probes Found: %d\n", sensorCount);
    
    // Initial blocking conversion so valid readings exist immediately
    if (sensorCount > 0) {
        tempSensors.setWaitForConversion(true);
        tempSensors.requestTemperatures();
    }
    tempSensors.setWaitForConversion(false);

    // 4. ADC Configuration
    analogReadResolution(ADC_RESOLUTION_BITS);
    pinMode(CELL1_ADC_PIN, INPUT);
    pinMode(CELL2_ADC_PIN, INPUT);
    pinMode(CELL3_ADC_PIN, INPUT);

    // 5. BLE GATT Server Initialization
    BLEDevice::init("BatteryGuardian-ESP32");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());

    BLEService *pService = pServer->createService(SERVICE_UUID);
    pTelemetryChar = pService->createCharacteristic(
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
    );
    pTelemetryChar->addDescriptor(new BLE2902());
    pService->start();

    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
    Serial.println("[INIT] BLE GATT Server Active & Advertising.");

    last_loop_ms = millis();
    last_adc_ms = last_loop_ms;
    last_oled_ms = last_loop_ms;
    last_telemetry_ms = last_loop_ms;

    Serial.println("[READY] Running non-blocking telemetry loop...\n");
}

// ============================================================================
// MAIN LOOP
// ============================================================================
void loop() {
    unsigned long current_ms = millis();
    last_loop_ms = current_ms;

    // Task 1: Read & Filter Sensors (5 Hz / 200 ms)
    if (current_ms - last_adc_ms >= 200) {
        unsigned long dt = current_ms - last_adc_ms;
        last_adc_ms = current_ms;
        updateAllSensors(dt);
    }

    // Task 2: Refresh OLED (2 Hz / 500 ms)
    if (current_ms - last_oled_ms >= 500) {
        last_oled_ms = current_ms;
        updateOLEDDisplay();
    }

    // Task 3: Emit Telemetry (1 Hz / 1000 ms)
    if (current_ms - last_telemetry_ms >= 1000) {
        last_telemetry_ms = current_ms;

        // Generate JSON String (<180 bytes)
        snprintf(json_payload, sizeof(json_payload),
            "{\"ts\":%lu,\"c1\":%.3f,\"c2\":%.3f,\"c3\":%.3f,\"v_pack\":%.3f,"
            "\"curr\":%.3f,\"pwr\":%.3f,\"t1\":%.1f,\"t2\":%.1f,\"t3\":%.1f,"
            "\"imb\":%.3f,\"mah\":%.1f,\"state\":\"%s\",\"cycle\":%lu}",
            (unsigned long)(current_ms / 1000),
            cell1_v, cell2_v, cell3_v, pack_voltage_v,
            current_a, power_w,
            temp1_c, temp2_c, temp3_c,
            cell_imbalance_v, discharged_mah,
            battery_state, (unsigned long)cycle_number
        );

        // Print to Serial Monitor
        Serial.printf("[TELEMETRY] %s\n", json_payload);
        Serial.printf(" >> V_Pack: %.2fV | C1: %.3fV | C2: %.3fV | C3: %.3fV | Imb: %.0fmV | I: %.3fA | T: %.1fC | %s\n",
            pack_voltage_v, cell1_v, cell2_v, cell3_v,
            cell_imbalance_v * 1000.0f, current_a, avg_temp_c, battery_state);

        // Notify BLE Client
        if (deviceConnected && pTelemetryChar != nullptr) {
            pTelemetryChar->setValue((uint8_t*)json_payload, strlen(json_payload));
            pTelemetryChar->notify();
        }
    }

    // BLE Auto-reconnection maintenance
    if (!deviceConnected && oldDeviceConnected) {
        delay(500);
        pServer->startAdvertising();
        Serial.println("[BLE] Advertising Restarted.");
        oldDeviceConnected = deviceConnected;
    }
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
    }

    delay(5);
}
