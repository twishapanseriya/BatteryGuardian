#include "sensors.h"
#include <stdio.h>
#include <math.h>

// Sensor Driver Instances
static Adafruit_INA219 ina219(INA219_I2C_ADDRESS);
static OneWire oneWire(DS18B20_PIN);
static DallasTemperature tempSensors(&oneWire);

static bool s_ina219_ok = false;
static int s_ds18b20_count = 0;

// Internal ADC Over-sampled Reader
static float readADCVoltage(int pin) {
    uint32_t total = 0;
    for (int i = 0; i < ADC_SAMPLES; i++) {
        total += analogRead(pin);
        delayMicroseconds(150);
    }
    float raw_avg = (float)total / (float)ADC_SAMPLES;
    return (raw_avg / (float)ADC_MAX_RAW) * ADC_REFERENCE_VOLTAGE;
}

// Convert measured ADC voltage at divider midpoint to actual node voltage with calibration
static inline float convertDividerVoltage(float adc_v, float cal_k) {
    return (adc_v / DIVIDER_RATIO) * cal_k;
}

bool initSensors() {
    // Initialize I2C Bus
    Wire.begin(SDA_PIN, SCL_PIN);
    
    // Initialize ADC
    analogReadResolution(ADC_RESOLUTION_BITS);
    pinMode(CELL1_ADC_PIN, INPUT);
    pinMode(CELL2_ADC_PIN, INPUT);
    pinMode(CELL3_ADC_PIN, INPUT);
    
    // Initialize INA219 Current Sensor
    if (ina219.begin()) {
        s_ina219_ok = true;
        ina219.setCalibration_32V_2A();
    } else {
        s_ina219_ok = false;
    }
    
    // Initialize DS18B20 1-Wire Temperature Sensors
    tempSensors.begin();
    s_ds18b20_count = tempSensors.getDeviceCount();
    
    // Perform initial blocking request so valid readings exist immediately
    if (s_ds18b20_count > 0) {
        tempSensors.setWaitForConversion(true);
        tempSensors.requestTemperatures();
    }
    // Switch to non-blocking mode for the main runtime loop
    tempSensors.setWaitForConversion(false);
    
    return true;
}

void updateSensors(BatteryTelemetry &t, unsigned long delta_ms) {
    t.timestamp_ms = millis();
    t.ina219_ok = s_ina219_ok;
    t.ds18b20_count = s_ds18b20_count;
    
    // 1. Read Midpoint ADC Voltages
    float adc1 = readADCVoltage(CELL1_ADC_PIN);
    float adc2 = readADCVoltage(CELL2_ADC_PIN);
    float adc3 = readADCVoltage(CELL3_ADC_PIN);
    
    // 2. Scale via Voltage Divider Ratio (10k / 43k) & Apply Per-Channel Calibration
    t.node1_v = convertDividerVoltage(adc1, CALIBRATION_K1);
    t.node2_v = convertDividerVoltage(adc2, CALIBRATION_K2);
    t.node3_v = convertDividerVoltage(adc3, CALIBRATION_K3);
    
    // 3. Compute Differential Cell Voltages
    t.cell1_v = t.node1_v;
    t.cell2_v = t.node2_v - t.node1_v;
    t.cell3_v = t.node3_v - t.node2_v;
    t.pack_voltage_v = t.node3_v;
    
    // Prevent negative voltage artifacts on zero input
    if (t.cell1_v < 0.0f) t.cell1_v = 0.0f;
    if (t.cell2_v < 0.0f) t.cell2_v = 0.0f;
    if (t.cell3_v < 0.0f) t.cell3_v = 0.0f;
    if (t.pack_voltage_v < 0.0f) t.pack_voltage_v = 0.0f;
    
    // 4. Compute Cell Imbalance: max(c1, c2, c3) - min(c1, c2, c3)
    float min_c = t.cell1_v;
    float max_c = t.cell1_v;
    
    if (t.cell2_v < min_c) min_c = t.cell2_v;
    if (t.cell3_v < min_c) min_c = t.cell3_v;
    
    if (t.cell2_v > max_c) max_c = t.cell2_v;
    if (t.cell3_v > max_c) max_c = t.cell3_v;
    
    t.cell_imbalance_v = max_c - min_c;
    
    // 5. Read INA219 Current & Power
    if (s_ina219_ok) {
        t.bus_voltage_v = ina219.getBusVoltage_V();
        float current_ma = ina219.getCurrent_mA();
        float power_mw = ina219.getPower_mW();
        
        t.current_a = current_ma / 1000.0f;
        t.power_w = power_mw / 1000.0f;
    } else {
        t.bus_voltage_v = t.pack_voltage_v;
        t.current_a = 0.0f;
        t.power_w = 0.0f;
    }
    
    // 6. Read DS18B20 Multi-probe Temperatures
    if (s_ds18b20_count > 0) {
        float r1 = tempSensors.getTempCByIndex(0);
        float r2 = (s_ds18b20_count > 1) ? tempSensors.getTempCByIndex(1) : r1;
        float r3 = (s_ds18b20_count > 2) ? tempSensors.getTempCByIndex(2) : r1;
        
        // Filter disconnected codes (-127C) or initial default power-on values
        if (!isnan(r1) && r1 > -50.0f && r1 < 125.0f) t.temp1_c = r1;
        if (!isnan(r2) && r2 > -50.0f && r2 < 125.0f) t.temp2_c = r2;
        if (!isnan(r3) && r3 > -50.0f && r3 < 125.0f) t.temp3_c = r3;
        
        t.avg_temp_c = (t.temp1_c + t.temp2_c + t.temp3_c) / 3.0f;
        
        // Asynchronously request next temperature conversion
        tempSensors.requestTemperatures();
    } else {
        t.temp1_c = 25.0f;
        t.temp2_c = 25.0f;
        t.temp3_c = 25.0f;
        t.avg_temp_c = 25.0f;
    }
    
    // 7. Coulomb Counting & Energy Integration
    float delta_hours = (float)delta_ms / 3600000.0f;
    if (t.current_a > CURRENT_ACTIVE_THRESHOLD_A) {
        snprintf(t.state, sizeof(t.state), "DISCHARGE");
        t.discharged_mah += (t.current_a * 1000.0f) * delta_hours;
        t.energy_mwh += (t.power_w * 1000.0f) * delta_hours;
    } else if (t.current_a < -CURRENT_ACTIVE_THRESHOLD_A) {
        snprintf(t.state, sizeof(t.state), "CHARGE");
    } else {
        snprintf(t.state, sizeof(t.state), "IDLE");
    }
    
    // 8. Warning Diagnoses
    t.voltage_warning = (t.cell1_v < CELL_MIN_VOLTAGE || t.cell1_v > CELL_MAX_VOLTAGE ||
                         t.cell2_v < CELL_MIN_VOLTAGE || t.cell2_v > CELL_MAX_VOLTAGE ||
                         t.cell3_v < CELL_MIN_VOLTAGE || t.cell3_v > CELL_MAX_VOLTAGE);
                         
    t.imbalance_warning = (t.cell_imbalance_v > MAX_CELL_IMBALANCE_WARNING);
    
    t.temperature_warning = (t.temp1_c > MAX_TEMP_WARNING_C ||
                             t.temp2_c > MAX_TEMP_WARNING_C ||
                             t.temp3_c > MAX_TEMP_WARNING_C);
}

void generateTelemetryJSON(const BatteryTelemetry &t, char *output, size_t max_len) {
    snprintf(output, max_len,
        "{\"ts\":%lu,\"c1\":%.3f,\"c2\":%.3f,\"c3\":%.3f,\"v_pack\":%.3f,"
        "\"curr\":%.3f,\"pwr\":%.3f,\"t1\":%.1f,\"t2\":%.1f,\"t3\":%.1f,"
        "\"imb\":%.3f,\"mah\":%.1f,\"state\":\"%s\",\"cycle\":%lu}",
        (unsigned long)(t.timestamp_ms / 1000),
        t.cell1_v,
        t.cell2_v,
        t.cell3_v,
        t.pack_voltage_v,
        t.current_a,
        t.power_w,
        t.temp1_c,
        t.temp2_c,
        t.temp3_c,
        t.cell_imbalance_v,
        t.discharged_mah,
        t.state,
        (unsigned long)t.cycle_count
    );
}
