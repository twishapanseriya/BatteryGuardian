# BatteryGuardian AI — Hardware Interface & Firmware Documentation

## 1. System Hardware Overview

The BatteryGuardian AI embedded hardware node is built on an **ESP32 Dev Module (WROOM-32)** to measure individual cell voltages, pack voltage, current, and temperatures from a 3-series lithium-ion battery pack, broadcasting real-time telemetry over Bluetooth Low Energy (BLE) to the Flutter mobile application.

```
                  +-----------------------------------+
                  |  3S1P Li-ion Battery Pack         |
                  |  Nominal: 11.1V | Max: 12.6V      |
                  |  Capacity: 1200 mAh (13.32 Wh)    |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
  [Cell Taps (1, 2, 3)]    [Pack Current Path]    [Cell Surfaces]
            |                       |                       |
            v                       v                       v
   Voltage Dividers           INA219 High-Side        DS18B20 1-Wire
   (33k / 10k + 100nF)       Current Sensor (I2C)     Digital Probes
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
                                    v
                            +---------------+
                            |     ESP32     |
                            | Microchip MCU |
                            +-------+-------+
                                    |
                      +-------------+-------------+
                      |                           |
                      v                           v
              SSD1306 OLED (I2C)           BLE GATT Server
              (Local Visuals)            (JSON Stream to App)
```

---

## 2. Pin Mapping & Electrical Interconnects (Confirmed)

| Subsystem / Sensor | ESP32 GPIO | Channel / Interface | Electrical Configuration & Scaling |
| :--- | :--- | :--- | :--- |
| **Cell 1 Tap (Node 1)** | `GPIO 34` | ADC1_CH6 (Input Only) | Voltage Divider ($33\text{k}\Omega$ Top / $10\text{k}\Omega$ Bottom) + $100\text{nF}$ Cap |
| **Cell 2 Tap (Node 2)** | `GPIO 35` | ADC1_CH7 (Input Only) | Voltage Divider ($33\text{k}\Omega$ Top / $10\text{k}\Omega$ Bottom) + $100\text{nF}$ Cap |
| **Cell 3 / Pack (Node 3)** | `GPIO 32` | ADC1_CH4 (Input Only) | Voltage Divider ($33\text{k}\Omega$ Top / $10\text{k}\Omega$ Bottom) + $100\text{nF}$ Cap |
| **Current Sensor (INA219)** | `GPIO 21` (SDA)<br>`GPIO 22` (SCL) | I2C Bus (`0x40`) | High-Side $0.1\,\Omega$ Shunt Resistor (Range: $\pm 3.2\text{A}$) |
| **Temp Sensors (DS18B20)** | `GPIO 4` | 1-Wire Bus | Up to 3 Digital Probes with $4.2\text{k}\Omega - 4.7\text{k}\Omega$ Pull-Up to $3.3\text{V}$ |
| **OLED Display (SSD1306)** | `GPIO 21` (SDA)<br>`GPIO 22` (SCL) | I2C Bus (`0x3C`) | $128 \times 64$ Monochrome OLED Display |

---

## 3. Voltage Divider, Calibration & Anti-Aliasing Calculations

### Resistor Divider Ratio
* Top Resistor ($R_{\text{top}}$): $33,000\,\Omega$ ($33\text{ k}\Omega$)
* Bottom Resistor ($R_{\text{bottom}}$): $10,000\,\Omega$ ($10\text{ k}\Omega$)

$$\text{Divider Ratio} = \frac{R_{\text{bottom}}}{R_{\text{top}} + R_{\text{bottom}}} = \frac{10,000}{33,000 + 10,000} = \frac{10}{43} \approx 0.232558$$

### Maximum Voltage at ESP32 ADC Input
* Fully Charged 3S Pack ($V_{\text{pack, max}} = 12.60\text{ V}$):
  $$V_{\text{pin, max}} = 12.60\text{ V} \times 0.232558 = 2.930\text{ V}$$
  *Result: $2.930\text{ V} < 3.30\text{ V}$ (ESP32 ADC ceiling), providing a safe $370\text{ mV}$ operating safety headroom.*

### Per-Channel Hardware Calibration Multipliers
Because discrete $33\text{k}\Omega$ and $10\text{k}\Omega$ resistors have manufacturing tolerances (typically $\pm 1\%$), small variations between dividers can propagate into false differential cell imbalances. The firmware provides 3 multipliers:
$$V_{\text{node1}} = \left(\frac{V_{\text{adc1}}}{\text{DIVIDER\_RATIO}}\right) \times k_1$$
$$V_{\text{node2}} = \left(\frac{V_{\text{adc2}}}{\text{DIVIDER\_RATIO}}\right) \times k_2$$
$$V_{\text{node3}} = \left(\frac{V_{\text{adc3}}}{\text{DIVIDER\_RATIO}}\right) \times k_3$$

**Calibration Procedure:**
1. Connect a charged battery pack and measure the real physical voltages at Node 1 (Pin 34 tap), Node 2 (Pin 35 tap), and Node 3 (Pin 32 tap) relative to GND with a Digital Multimeter (DMM).
2. Read the uncalibrated voltages displayed on the Serial Monitor (`$k_1=1.0, k_2=1.0, k_3=1.0$`).
3. Compute: $k_i = \frac{V_{\text{DMM, node } i}}{V_{\text{ESP32, node } i}}$
4. Update `CALIBRATION_K1`, `CALIBRATION_K2`, `CALIBRATION_K3` in [`config.h`](file:///home/Twisha/Startup/firmware/esp32/config.h).

### Differential Series Cell Derivation
* **Cell 1 Voltage**: $V_{\text{cell1}} = V_{\text{node1}}$
* **Cell 2 Voltage**: $V_{\text{cell2}} = V_{\text{node2}} - V_{\text{node1}}$
* **Cell 3 Voltage**: $V_{\text{cell3}} = V_{\text{node3}} - V_{\text{node2}}$
* **Pack Voltage**: $V_{\text{pack}} = V_{\text{node3}}$
* **Cell Imbalance**: $\Delta V = \max(V_{\text{cell1}}, V_{\text{cell2}}, V_{\text{cell3}}) - \min(V_{\text{cell1}}, V_{\text{cell2}}, V_{\text{cell3}})$

### Hardware RC Anti-Aliasing Filter
A $100\text{ nF}$ ceramic capacitor is placed across each $10\text{ k}\Omega$ bottom resistor.
The Thévenin equivalent resistance of the divider is:
$$R_{\text{th}} = R_{\text{top}} \parallel R_{\text{bottom}} = \frac{33\text{ k}\Omega \times 10\text{ k}\Omega}{33\text{ k}\Omega + 10\text{ k}\Omega} \approx 7.674\text{ k}\Omega$$

The low-pass filter cutoff frequency ($f_c$) is:
$$f_c = \frac{1}{2\pi \cdot R_{\text{th}} \cdot C} = \frac{1}{2\pi \cdot 7674\,\Omega \cdot 100 \times 10^{-9}\text{ F}} \approx 207.4\text{ Hz}$$

---

## 4. BLE GATT Communication Protocol

### BLE Service & Characteristic Identifiers
* **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
* **Telemetry Characteristic UUID**: `beb5483e-36e1-4688-b7f5-ea07361b26a8`
* **Properties**: `READ` | `NOTIFY`
* **Descriptor**: `BLE2902` (Client Characteristic Configuration)
* **Broadcast Rate**: $1\text{ Hz}$ ($1000\text{ ms}$ periodic timer)

### Telemetry JSON Payload Format
```json
{
  "ts": 1725201600,
  "c1": 4.120,
  "c2": 4.085,
  "c3": 4.032,
  "v_pack": 12.237,
  "curr": 0.122,
  "pwr": 1.493,
  "t1": 28.5,
  "t2": 28.7,
  "t3": 29.1,
  "imb": 0.088,
  "mah": 14.2,
  "state": "DISCHARGE",
  "cycle": 1
}
```

---

## 5. Physical Compilation, Flashing & Testing Guide

### Prerequisites:
1. **Arduino IDE** (v2.x recommended) or **VS Code with PlatformIO**.
2. Install **ESP32 Board Package** by Espressif (`v2.0.x` or `v3.x`).
3. Install required libraries via Arduino Library Manager:
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
   - `Adafruit INA219`
   - `OneWire`
   - `DallasTemperature`

### Flashing Steps:
1. Open [`firmware/esp32/BatteryGuardian_ESP32.ino`](file:///home/Twisha/Startup/firmware/esp32/BatteryGuardian_ESP32.ino) in Arduino IDE.
2. Under **Tools** menu, configure:
   - **Board**: `ESP32 Dev Module`
   - **Upload Speed**: `921600` (or `115200` if connection is unstable)
   - **Flash Frequency**: `80MHz`
   - **Partition Scheme**: `Default 4MB with spiffs`
   - **Port**: Select your ESP32 serial COM port (`/dev/ttyUSB0` or `COMx`).
3. Click **Upload** ($\rightarrow$).

### Step-by-Step Hardware Testing Checklist:
1. **OLED Visual Verification**:
   - On boot, OLED shows `BATTERY GUARDIAN` splash, followed by live Pack Voltage, Current, C1/C2/C3 voltages, imbalance $\text{mV}$, temperatures, and `[--]` (unconnected BLE icon).
2. **Serial Monitor Verification**:
   - Open Serial Monitor at **115200 baud**.
   - Verify that JSON telemetry lines and formatted diagnostic rows are emitted once per second.
3. **Multimeter Calibration Check**:
   - Measure actual voltage between GND and Tap 1, Tap 2, Tap 3 using a DMM. Compare against Serial readings and adjust `CALIBRATION_K1/K2/K3` if needed.
4. **BLE GATT Broadcast Verification**:
   - Open the **nRF Connect** or **LightBlue** app on your phone.
   - Scan for `BatteryGuardian-ESP32`.
   - Connect and find Service `4fafc201-1fb5-459e-8fcc-c5c9c331914b`.
   - Subscribe to notifications on Characteristic `beb5483e-36e1-4688-b7f5-ea07361b26a8`.
   - Confirm that raw JSON telemetry packets arrive every second and the OLED updates its indicator to `[BLE]`.
