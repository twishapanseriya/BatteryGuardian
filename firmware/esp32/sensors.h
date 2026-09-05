#ifndef SENSORS_H
#define SENSORS_H

#include "config.h"
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Structured Battery Telemetry Data Model
struct BatteryTelemetry {
    uint32_t timestamp_ms;
    
    // ADC Divider Node Voltages (V)
    float node1_v;
    float node2_v;
    float node3_v;
    
    // Differential Cell Voltages (V)
    float cell1_v;
    float cell2_v;
    float cell3_v;
    float pack_voltage_v;
    float cell_imbalance_v;
    
    // Current & Power (INA219)
    float bus_voltage_v;
    float current_a;
    float power_w;
    
    // Thermal Probes (DS18B20, deg C)
    float temp1_c;
    float temp2_c;
    float temp3_c;
    float avg_temp_c;
    
    // Integrated Energy Metrics
    float discharged_mah;
    float energy_mwh;
    
    // Operational State
    char state[12]; // "IDLE", "DISCHARGE", "CHARGE"
    uint32_t cycle_count;
    
    // Diagnostic Warning Flags
    bool voltage_warning;
    bool imbalance_warning;
    bool temperature_warning;
    bool ina219_ok;
    bool oled_ok;
    int ds18b20_count;
};

// Sensor Interface Functions
bool initSensors();
void updateSensors(BatteryTelemetry &telemetry, unsigned long delta_ms);
void generateTelemetryJSON(const BatteryTelemetry &telemetry, char *output, size_t max_len);

#endif // SENSORS_H
