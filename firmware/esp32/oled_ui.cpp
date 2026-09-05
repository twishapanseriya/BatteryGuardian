#include "oled_ui.h"

static Adafruit_SSD1306 s_display(OLED_SCREEN_WIDTH, OLED_SCREEN_HEIGHT, &Wire, -1);
static bool s_oled_ok = false;

bool initOLED() {
    if (s_display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS)) {
        s_oled_ok = true;
        s_display.clearDisplay();
        s_display.setTextColor(SSD1306_WHITE);
        s_display.setTextSize(1);
        
        s_display.setCursor(0, 0);
        s_display.println("BATTERY GUARDIAN");
        s_display.setCursor(0, 16);
        s_display.println("AI Telemetry Node");
        s_display.setCursor(0, 32);
        s_display.println("Sensors Init: OK");
        s_display.setCursor(0, 48);
        s_display.println("BLE Ready...");
        s_display.display();
        return true;
    }
    s_oled_ok = false;
    return false;
}

void updateOLED(const BatteryTelemetry &t, bool ble_connected) {
    if (!s_oled_ok) return;
    
    s_display.clearDisplay();
    s_display.setTextColor(SSD1306_WHITE);
    s_display.setTextSize(1);
    
    // Row 0: Header & BLE Indicator
    s_display.setCursor(0, 0);
    s_display.print("BAT GUARDIAN ");
    if (ble_connected) {
        s_display.print("[BLE]");
    } else {
        s_display.print("[--]");
    }
    
    // Horizontal Separator Line
    s_display.drawLine(0, 9, 127, 9, SSD1306_WHITE);
    
    // Row 1: Pack Voltage & Current
    s_display.setCursor(0, 12);
    s_display.print("V: ");
    s_display.print(t.pack_voltage_v, 2);
    s_display.print("V  I:");
    s_display.print(t.current_a, 2);
    s_display.print("A");
    
    // Row 2: Cell 1 & Cell 2 Voltages
    s_display.setCursor(0, 24);
    s_display.print("C1:");
    s_display.print(t.cell1_v, 2);
    s_display.print(" C2:");
    s_display.print(t.cell2_v, 2);
    
    // Row 3: Cell 3 Voltage & Imbalance (mV)
    s_display.setCursor(0, 36);
    s_display.print("C3:");
    s_display.print(t.cell3_v, 2);
    s_display.print(" dV:");
    s_display.print((int)(t.cell_imbalance_v * 1000.0f));
    s_display.print("mV");
    
    // Row 4: Temperature & Battery State
    s_display.setCursor(0, 48);
    s_display.print("T:");
    s_display.print((int)t.temp1_c);
    s_display.print("/");
    s_display.print((int)t.temp2_c);
    s_display.print("C ");
    
    if (t.voltage_warning || t.imbalance_warning || t.temperature_warning) {
        s_display.print("!WARN!");
    } else {
        s_display.print(t.state);
    }
    
    s_display.display();
}
