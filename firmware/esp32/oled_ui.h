#ifndef OLED_UI_H
#define OLED_UI_H

#include "config.h"
#include "sensors.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Initialize OLED SSD1306 Display
bool initOLED();

// Render Real-Time Telemetry & Status Dashboard
void updateOLED(const BatteryTelemetry &telemetry, bool ble_connected);

#endif // OLED_UI_H
