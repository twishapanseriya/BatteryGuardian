// ============================================================================
// BATTERYGUARDIAN AI - ESP32 FIRMWARE
// 3S Li-ion Battery Health Telemetry & BLE GATT Server
// ============================================================================
// Target Board: ESP32 Dev Module (WROOM-32)
// Architecture: Non-blocking task scheduler with differential cell voltage math,
//               hardware anti-aliasing RC filtering, INA219 current integration,
//               DS18B20 1-Wire multi-probe thermal sensing, and BLE GATT Notify.
// ============================================================================

#include "config.h"
#include "sensors.h"
#include "ble_service.h"
#include "oled_ui.h"

// Telemetry State & Global Buffers
static BatteryTelemetry g_telemetry;
static char g_json_buffer[256];

// Non-blocking Timing Trackers
static unsigned long g_last_adc_ms = 0;
static unsigned long g_last_oled_ms = 0;
static unsigned long g_last_telemetry_ms = 0;
static unsigned long g_last_loop_ms = 0;

void setup() {
    Serial.begin(115200);
    delay(1500); // Allow hardware power rails to stabilize
    
    Serial.println("\n==================================================");
    Serial.println("           BATTERYGUARDIAN AI - ESP32             ");
    Serial.println("        Real-Time Battery Telemetry Node          ");
    Serial.println("==================================================");
    Serial.printf("Firmware Version : %s\n", FIRMWARE_VERSION);
    Serial.printf("BLE Service UUID : %s\n", SERVICE_UUID);
    Serial.printf("BLE Char UUID    : %s\n", CHARACTERISTIC_UUID);
    Serial.printf("Voltage Divider  : 33k Top / 10k Bottom (Ratio: %.5f)\n", DIVIDER_RATIO);
    Serial.println("--------------------------------------------------");
    
    // 1. Initialize Hardware Sensors (I2C, ADC, INA219, DS18B20)
    initSensors();
    Serial.println("[INIT] Sensors initialized.");
    
    // 2. Initialize OLED Display
    if (initOLED()) {
        Serial.println("[INIT] SSD1306 OLED Display: OK");
    } else {
        Serial.println("[INIT] SSD1306 OLED Display: NOT DETECTED");
    }
    
    // 3. Initialize BLE GATT Server
    initBLE();
    Serial.println("[INIT] BLE Server & GATT advertising active.");
    
    // Initialize timing
    g_last_loop_ms = millis();
    g_last_adc_ms = g_last_loop_ms;
    g_last_oled_ms = g_last_loop_ms;
    g_last_telemetry_ms = g_last_loop_ms;
    
    // Zero telemetry metrics
    memset(&g_telemetry, 0, sizeof(BatteryTelemetry));
    strcpy(g_telemetry.state, "IDLE");
    g_telemetry.cycle_count = 1;
    
    Serial.println("==================================================");
    Serial.println("[READY] Entering Real-Time Telemetry Loop...\n");
}

void loop() {
    unsigned long current_ms = millis();
    unsigned long delta_loop_ms = current_ms - g_last_loop_ms;
    g_last_loop_ms = current_ms;
    
    // -------------------------------------------------------------
    // Task 1: Sample & Filter Sensors (Every 200 ms / 5 Hz)
    // -------------------------------------------------------------
    if (current_ms - g_last_adc_ms >= ADC_SAMPLE_INTERVAL_MS) {
        unsigned long dt = current_ms - g_last_adc_ms;
        g_last_adc_ms = current_ms;
        
        updateSensors(g_telemetry, dt);
    }
    
    // -------------------------------------------------------------
    // Task 2: Update OLED Dashboard (Every 500 ms / 2 Hz)
    // -------------------------------------------------------------
    if (current_ms - g_last_oled_ms >= OLED_UPDATE_INTERVAL_MS) {
        g_last_oled_ms = current_ms;
        
        updateOLED(g_telemetry, isBLEConnected());
    }
    
    // -------------------------------------------------------------
    // Task 3: Emit Telemetry Packet (Every 1000 ms / 1 Hz)
    // -------------------------------------------------------------
    if (current_ms - g_last_telemetry_ms >= TELEMETRY_INTERVAL_MS) {
        g_last_telemetry_ms = current_ms;
        
        // Generate compact, deterministic JSON payload
        generateTelemetryJSON(g_telemetry, g_json_buffer, sizeof(g_json_buffer));
        
        // 1. Output over Serial Monitor for local logging / debugging
        Serial.printf("[TELEMETRY] %s\n", g_json_buffer);
        
        // Formatted human-readable diagnostic log
        Serial.printf(" >> Pack: %.2fV | C1: %.3fV | C2: %.3fV | C3: %.3fV | Imb: %.0fmV | I: %.3fA | T: %.1fC | State: %s\n",
            g_telemetry.pack_voltage_v,
            g_telemetry.cell1_v,
            g_telemetry.cell2_v,
            g_telemetry.cell3_v,
            g_telemetry.cell_imbalance_v * 1000.0f,
            g_telemetry.current_a,
            g_telemetry.avg_temp_c,
            g_telemetry.state
        );
        
        // 2. Broadcast via BLE GATT Notification if Flutter client connected
        if (isBLEConnected()) {
            sendBLETelemetry(g_json_buffer);
        }
    }
    
    // -------------------------------------------------------------
    // Task 4: Maintain BLE Stack Connection State
    // -------------------------------------------------------------
    updateBLE();
    
    // Yield to FreeRTOS scheduler
    delay(5);
}
