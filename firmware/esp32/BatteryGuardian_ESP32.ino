#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// --- Milestone 12:SOH AND RUL  Machine Learning Headers ---
#include "scaler_params.h"
#include "model_weights.h"
#include "model_inference.h"
#include "rul_model.h"


// --- Hardware Pin Definitions ---
#define I2C_SDA          21
#define I2C_SCL          22
#define ONE_WIRE_BUS     4

// --- OLED Display Configuration ---
#define SCREEN_WIDTH     128
#define SCREEN_HEIGHT    64
#define OLED_RESET       -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- Sensor Objects ---
Adafruit_ADS1115 ads;
Adafruit_INA219 ina219;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

// --- Calibrated Voltage Divider Ratios ---
const float DIVIDER_RATIO_1 = 4.0309; // Node 1 (Cell 1)
const float DIVIDER_RATIO_2 = 4.0304; // Node 2 (Cell 2)
const float DIVIDER_RATIO_3 = 4.0308; // Node 3 (Cell 3 / Total Pack)

// --- Safety Threshold Constants ---
const float CRIT_TEMP_MAX      = 45.0; // Over-temperature limit (°C)
const float CRIT_CELL_MIN      = 3.00; // Under-voltage limit per cell (V)
const float CRIT_CELL_MAX      = 4.25; // Over-voltage limit per cell (V)
const float CRIT_IMBALANCE_MAX = 0.10; // Max cell voltage delta (100mV)
const float CRIT_CURRENT_MAX   = 3500;  // Over-current limit (mA)

// --- Timing Variables (Non-Blocking millis) ---
unsigned long lastSensorReadTime = 0;
unsigned long lastPageSwapTime   = 0;
const unsigned long SENSOR_INTERVAL = 1000;  // Update sensors every 1 sec
const unsigned long PAGE_INTERVAL   = 10000; // Alternate display every 10 sec

// Display Page State: false = Telemetry Data, true = Large Status Screen
bool showStatusPage = false;

// Dynamic Open Circuit Voltage tracking for Internal Resistance estimation
float vOpenCircuit = 11.80;

//new for milestone 12
// --- Machine Learning Cycle Tracking ---
float cycle_start_voltage = 0.0;
float cycle_min_voltage = 99.0;
float cycle_max_voltage = 0.0;
float cycle_start_temp = 0.0;
float cycle_min_temp = 99.0;
float cycle_max_temp = 0.0;
unsigned long cycle_start_time = 0;
float accumulated_energy_wh = 0.0;


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println(F("\n=============================================="));
  Serial.println(F("     ESP32 BATTERY GUARDIAN INITIALIZATION    "));
  Serial.println(F("=============================================="));

  Wire.begin(I2C_SDA, I2C_SCL);

  // 1. Initialize OLED Display
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("ERROR: OLED Display initialization failed!"));
    for (;;);
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(16, 20);
  display.println(F("BATTERY GUARDIAN"));
  display.setCursor(16, 35);
  display.println(F("Booting System..."));
  display.display();

  // 2. Initialize ADS1115 ADC
  if (!ads.begin(0x48)) {
    Serial.println(F("ERROR: ADS1115 ADC initialization failed!"));
  } else {
    Serial.println(F("SUCCESS: ADS1115 Detected."));
  }
  ads.setGain(GAIN_ONE); // Gain = 1 (+/- 4.096V range)

  // 3. Initialize INA219 Current Sensor
  if (!ina219.begin()) {
    Serial.println(F("ERROR: INA219 Power Monitor failed!"));
  } else {
    Serial.println(F("SUCCESS: INA219 Detected."));
  }

  // 4. Initialize DS18B20 Temperature Sensors
  tempSensor.begin();
  int sensorsFound = tempSensor.getDS18Count();
  Serial.printf("SUCCESS: Found %d DS18B20 sensor(s) on 1-Wire bus.\n", sensorsFound);

  delay(1500);
}

void loop() {
  unsigned long currentMillis = millis();

  // --- Page Switch Timer (Toggles every 10 Seconds) ---
  if (currentMillis - lastPageSwapTime >= PAGE_INTERVAL) {
    lastPageSwapTime = currentMillis;
    showStatusPage = !showStatusPage;
  }

  // --- Sensor Reading Loop (Runs every 1 Second) ---
  if (currentMillis - lastSensorReadTime >= SENSOR_INTERVAL) {
    lastSensorReadTime = currentMillis;

    // 1. Read ADS1115 Pin Voltages
    float vPin0 = ads.computeVolts(ads.readADC_SingleEnded(0));
    float vPin1 = ads.computeVolts(ads.readADC_SingleEnded(1));
    float vPin2 = ads.computeVolts(ads.readADC_SingleEnded(2));

    // 2. Scale up by Calibrated Dividers
    float vNode1 = vPin0 * DIVIDER_RATIO_1;
    float vNode2 = vPin1 * DIVIDER_RATIO_2;
    float vNode3 = vPin2 * DIVIDER_RATIO_3;

    // Differential Cell Voltages
    float vCell1 = vNode1;
    float vCell2 = vNode2 - vNode1;
    float vCell3 = vNode3 - vNode2;

    if (vCell1 < 0) vCell1 = 0;
    if (vCell2 < 0) vCell2 = 0;
    if (vCell3 < 0) vCell3 = 0;

    // Calculate Min, Max, and Cell Imbalance Delta
    float minCell = min(vCell1, min(vCell2, vCell3));
    float maxCell = max(vCell1, max(vCell2, vCell3));
    float cellDelta = maxCell - minCell;

    // 3. Read INA219 Metrics
    float current_mA = abs(ina219.getCurrent_mA());
    float power_W = (vNode3 * current_mA) / 1000.0;

    // 4. Calculate Internal Resistance (Rint) in mΩ
    if (current_mA < 30.0) {
      vOpenCircuit = vNode3;
    }

    float vDrop = vOpenCircuit - vNode3;
    float rInt_mOhm = 0.0;

    if (current_mA > 100.0 && vDrop > 0.01) {
      rInt_mOhm = (vDrop / (current_mA / 1000.0)) * 1000.0;
    }

    // 5. Read DS18B20 Temperatures
    tempSensor.requestTemperatures();

    float t1 = tempSensor.getTempCByIndex(0);
    float t2 = tempSensor.getTempCByIndex(1);
    float t3 = tempSensor.getTempCByIndex(2);

    float maxTemp = max(t1, max(t2, t3));

    // 6. Critical Condition Diagnostic Evaluation
    bool isCritical = false;
    String criticalReason = "";

    if (maxTemp > CRIT_TEMP_MAX) {
      isCritical = true;
      criticalReason = "OVER TEMPERATURE!";
    } else if (minCell < CRIT_CELL_MIN) {
      isCritical = true;
      criticalReason = "UNDER VOLTAGE!";
    } else if (maxCell > CRIT_CELL_MAX) {
      isCritical = true;
      criticalReason = "OVER VOLTAGE!";
    } else if (cellDelta > CRIT_IMBALANCE_MAX) {
      isCritical = true;
      criticalReason = "CELL UNBALANCE!";
    } else if (current_mA > CRIT_CURRENT_MAX) {
      isCritical = true;
      criticalReason = "OVER CURRENT!";
    }

//milestone 12 update
// --- 6.5 Machine Learning AI Inference (Ridge Regression) ---
    // Update cycle tracking statistics
    if (vNode3 < cycle_min_voltage) cycle_min_voltage = vNode3;
    if (vNode3 > cycle_max_voltage) cycle_max_voltage = vNode3;
    if (maxTemp < cycle_min_temp) cycle_min_temp = maxTemp;
    if (maxTemp > cycle_max_temp) cycle_max_temp = maxTemp;
    
    // Simple trapezoidal integration for energy (W * hours)
    accumulated_energy_wh += (power_W * (SENSOR_INTERVAL / 3600000.0));

    // Map instantaneous/tracked variables to the 23 hardware features
    float raw_features[NUM_HARDWARE_FEATURES] = {0};
    raw_features[IDX_DURATION_S] = (currentMillis - cycle_start_time) / 1000.0;
    raw_features[IDX_V_START] = cycle_start_voltage;
    raw_features[IDX_V_END] = vNode3;
    raw_features[IDX_V_MIN] = cycle_min_voltage;
    raw_features[IDX_V_MAX] = cycle_max_voltage;
    raw_features[IDX_V_MEAN] = (cycle_start_voltage + vNode3) / 2.0; 
    raw_features[IDX_V_DROP] = cycle_start_voltage - cycle_min_voltage;
    raw_features[IDX_V_STD] = 0.1; // Placeholder
    raw_features[IDX_VOLTAGE_SLOPE] = (cycle_start_voltage - vNode3) / max(1.0f, raw_features[IDX_DURATION_S]);
    raw_features[IDX_V_SKEW] = 0.0; // Placeholder
    raw_features[IDX_DC_IR] = rInt_mOhm / 1000.0; 
    raw_features[IDX_I_MEAN] = current_mA / 1000.0; 
    raw_features[IDX_I_MIN] = current_mA / 1000.0;  
    raw_features[IDX_I_MAX] = current_mA / 1000.0;
    raw_features[IDX_T_START] = cycle_start_temp;
    raw_features[IDX_T_END] = maxTemp;
    raw_features[IDX_T_MIN] = cycle_min_temp;
    raw_features[IDX_T_MAX] = cycle_max_temp;
    raw_features[IDX_T_MEAN] = (cycle_start_temp + maxTemp) / 2.0;
    raw_features[IDX_TEMP_RISE] = cycle_max_temp - cycle_start_temp;
    raw_features[IDX_TEMP_RISE_RATE] = raw_features[IDX_TEMP_RISE] / max(1.0f, raw_features[IDX_DURATION_S]);
    raw_features[IDX_TEMP_STD] = 0.5; // Placeholder
    raw_features[IDX_ENERGY_WH] = accumulated_energy_wh;

    // Run the on-device prediction 
    float predicted_soh = predict_soh_pct(raw_features);

// Run the on-device RUL prediction (Random Forest)
    float predicted_rul = score(raw_features);



    // --- 7. Print Clean Output to Serial Monitor ---
    Serial.println(F("========================================================="));

    Serial.printf(
      "VOLTAGES  | C1: %.2fV  | C2: %.2fV  | C3: %.2fV  | Total: %.2fV\n",
      vCell1, vCell2, vCell3, vNode3
    );

    Serial.printf(
      "METRICS   | Imbal: %.0fmV | Rint: %.1fmOhm\n",
      cellDelta * 1000.0, rInt_mOhm
    );

    Serial.printf(
      "POWER     | Current: %.1fmA | Power: %.2fW\n",
      current_mA, power_W
    );

    Serial.printf(
      "TEMPS     | T1: %.1fC  | T2: %.1fC  | T3: %.1fC\n",
      t1, t2, t3
    );

    if (isCritical) {
      Serial.printf(
        "STATUS    | >>> CRITICAL ALERT: %s <<<\n",
        criticalReason.c_str()
      );
    } else {
      Serial.println(F("STATUS    | System Normal [OK]"));
    }

//milestone 12 update
Serial.printf("AI PREDICT| SoH: %.2f%%  | RUL: %.1f cycles\n", predicted_soh, predicted_rul);


    Serial.println(F("=========================================================\n"));
    Serial.flush();

    // --- 8. Render Clean, Non-Overlapping OLED Display ---
    display.clearDisplay();

    if (showStatusPage) {
      // PAGE A: LARGE SYSTEM STATUS SCREEN
      display.setTextSize(1);
      display.setCursor(16, 0);
      display.print(F("-- SYSTEM STATUS --"));

      if (isCritical) {
        display.setTextSize(2);
        display.setCursor(12, 16);
        display.print(F("CRITICAL!"));

        display.setTextSize(1);
        display.setCursor(10, 36);
        display.print(criticalReason);

        display.setCursor(0, 52);
        display.printf(
          "Pk:%.1fV I:%.0fmA T:%.0fC",
          vNode3, current_mA, maxTemp
        );
      } else {
        display.setTextSize(2);
        display.setCursor(28, 16);
        display.print(F("NORMAL"));

        display.setTextSize(1);
        display.setCursor(22, 36);
        display.print(F("All Systems OK"));

        display.setCursor(0, 52);
        display.printf(
          "Pack:%.2fV  R:%.0fmOhm",
          vNode3, rInt_mOhm
        );
      }

    } else {
      // PAGE B: SYSTEMATIC TELEMETRY DATA
      display.setCursor(16, 0);
      display.print(F("BATTERY GUARDIAN"));

      display.setCursor(0, 11);
      display.printf(
        "C1:%.2fV  C2:%.2fV",
        vCell1, vCell2
      );

      display.setCursor(0, 21);
      display.printf(
        "C3:%.2fV  Pk:%.2fV",
        vCell3, vNode3
      );

      display.setCursor(0, 31);
      display.printf(
        "I:%.0fmA    P:%.2fW",
        current_mA, power_W
      );

      display.setCursor(0, 41);
      display.printf(
        "R:%.0fmOhm   dV:%.0fmV",
        rInt_mOhm, cellDelta * 1000.0
      );

      display.setCursor(0, 52);
      display.printf(
        "T1:%.0fC T2:%.0fC T3:%.0fC",
        t1, t2, t3
      );
    }

    display.display();
  }
}
