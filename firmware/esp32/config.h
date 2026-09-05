#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ============================================================================
// BATTERYGUARDIAN AI - FIRMWARE CONFIGURATION
// ============================================================================

// Device Identification
#define DEVICE_NAME "BatteryGuardian-ESP32"
#define FIRMWARE_VERSION "1.0.1"

// ============================================================================
// PIN DEFINITIONS (CONFIRMED HARDWARE)
// ============================================================================

// I2C Bus Pins (INA219 Current Sensor & SSD1306 OLED)
#define SDA_PIN 21
#define SCL_PIN 22

// 1-Wire Digital Temperature Sensor (DS18B20)
#define DS18B20_PIN 4

// Analog ADC Channels (Cell Voltage Divider Taps)
#define CELL1_ADC_PIN 34  // ADC1_CH6: Cell 1 Tap (0 - 4.2V nominal)
#define CELL2_ADC_PIN 35  // ADC1_CH7: Cell 2 Tap (0 - 8.4V nominal)
#define CELL3_ADC_PIN 32  // ADC1_CH4: Cell 3 / Pack Tap (0 - 12.6V nominal)

// ============================================================================
// VOLTAGE DIVIDER CONFIGURATION (33 kOhm Top / 10 kOhm Bottom)
// ============================================================================
const float R_TOP = 33000.0f;       // 33 kOhm
const float R_BOTTOM = 10000.0f;    // 10 kOhm

// Divider Ratio: R_BOTTOM / (R_TOP + R_BOTTOM) = 10 / 43 ≈ 0.232558
const float DIVIDER_RATIO = R_BOTTOM / (R_TOP + R_BOTTOM);

// ============================================================================
// PER-CHANNEL HARDWARE CALIBRATION MULTIPLIERS
// Adjust these against a calibrated Digital Multimeter (DMM) to nullify
// resistor tolerance variations (e.g., 1% error) and ADC non-linearities.
// Formula: k = V_measured_by_DMM / V_reported_by_ESP32
// ============================================================================
const float CALIBRATION_K1 = 1.0000f; // Node 1 (Tap 1) multiplier
const float CALIBRATION_K2 = 1.0000f; // Node 2 (Tap 2) multiplier
const float CALIBRATION_K3 = 1.0000f; // Node 3 (Tap 3 / Pack) multiplier

// ADC Calibration & Resolution
const int ADC_RESOLUTION_BITS = 12;
const int ADC_MAX_RAW = 4095;
const float ADC_REFERENCE_VOLTAGE = 3.30f; // Nominal ESP32 reference
const int ADC_SAMPLES = 16;                // Oversampling for noise reduction

// ============================================================================
// I2C PERIPHERAL ADDRESSES
// ============================================================================
#define OLED_I2C_ADDRESS 0x3C
#define OLED_SCREEN_WIDTH 128
#define OLED_SCREEN_HEIGHT 64

#define INA219_I2C_ADDRESS 0x40

// ============================================================================
// BATTERY & CHEMISTRY THRESHOLDS (3S Li-ion IMR-18650)
// ============================================================================
const float NOMINAL_CELL_VOLTAGE = 3.70f;
const float NOMINAL_PACK_VOLTAGE = 11.10f;
const float NOMINAL_CAPACITY_MAH = 1200.0f;

const float CELL_MIN_VOLTAGE = 2.50f;     // Absolute emergency low cutoff
const float CELL_MAX_VOLTAGE = 4.25f;     // Absolute emergency high cutoff
const float PACK_DISCHARGE_CUTOFF = 9.0f; // 3S Pack empty threshold (3.0V/cell)
const float PACK_FULL_CHARGED = 12.60f;   // 3S Pack full threshold (4.2V/cell)

const float MAX_CELL_IMBALANCE_WARNING = 0.100f; // 100 mV imbalance warning
const float MAX_TEMP_WARNING_C = 55.0f;          // 55 deg C thermal warning

// Current state detection thresholds (Amps)
const float CURRENT_ACTIVE_THRESHOLD_A = 0.020f; // 20 mA threshold

// ============================================================================
// BLE GATT CONFIGURATION
// ============================================================================
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// ============================================================================
// TIMING INTERVALS (Non-blocking millis)
// ============================================================================
const unsigned long TELEMETRY_INTERVAL_MS = 1000; // 1 Hz (1000ms)
const unsigned long OLED_UPDATE_INTERVAL_MS = 500; // 2 Hz (500ms)
const unsigned long ADC_SAMPLE_INTERVAL_MS = 200;  // 5 Hz (200ms)

#endif // CONFIG_H
