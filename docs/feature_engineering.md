# BatteryGuardian AI — Milestone 10: Feature Engineering & Normalization Pipeline

## 1. Executive Summary & Objective

Milestone 10 prepares the validated NASA Ames PCoE battery aging dataset for supervised machine learning by:
1. **Extracting 25 domain-informed features** (electrochemical, temporal, thermal, and statistical).
2. **Classifying features into Hardware-Reproducible (23 features)** and **Lab-Only (2 EIS features)**.
3. **Applying zero-leakage normalization** (fitting `StandardScaler` and `RobustScaler` strictly on the training partition).
4. **Exporting edge-compatible scaling parameters** (`feature_scaler_params.json`) ready for direct C/C++ embedded or FastAPI deployment.

---

## 2. Feature Catalog & Engineering Units

### A. Hardware-Reproducible Features (23 Features)
All 23 features can be computed from standard DC voltage, current, temperature, and duration measurements captured by the BatteryGuardian hardware:

| # | Feature Name | Description | Source Sensor / Derivation | Engineering Unit |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `duration_s` | Total discharge duration ($t_{\text{cutoff}} - t_0$) | Timer (`millis()`) | seconds ($s$) |
| 2 | `v_start` | Terminal voltage at discharge onset | Voltage Divider ADC | Volts ($V$) |
| 3 | `v_end` | Final voltage at cutoff disconnect | Voltage Divider ADC | Volts ($V$) |
| 4 | `v_min` | Minimum dynamic voltage during cycle | Voltage Divider ADC | Volts ($V$) |
| 5 | `v_max` | Maximum terminal voltage | Voltage Divider ADC | Volts ($V$) |
| 6 | `v_mean` | Mean discharge terminal voltage | Voltage Divider ADC | Volts ($V$) |
| 7 | `v_drop` | Total voltage drop ($v_{\text{start}} - v_{\text{min}}$) | Derived | Volts ($V$) |
| 8 | `v_std` | Standard deviation of voltage trajectory | Statistical | Volts ($V$) |
| 9 | `voltage_slope`| Rate of voltage decay ($(v_{\text{start}} - v_{\text{end}}) / \text{duration}$) | Derived | Volts/second ($V/s$) |
| 10| `v_skew` | Skewness of voltage discharge distribution | Statistical | dimensionless |
| 11| `dc_internal_resistance`| Instantaneous DC IR ($\Delta V_{\text{load\_step}} / \vert I_{\text{load\_step}} \vert$) | Derived step response | Ohms ($\Omega$) |
| 12| `i_mean` | Average discharge current | INA219 Current Sensor | Amperes ($A$) |
| 13| `i_min` | Minimum current (peak negative magnitude) | INA219 Current Sensor | Amperes ($A$) |
| 14| `i_max` | Maximum current | INA219 Current Sensor | Amperes ($A$) |
| 15| `t_start` | Surface temperature at discharge onset | DS18B20 1-Wire Probe | degrees Celsius ($^\circ\text{C}$) |
| 16| `t_end` | Surface temperature at cutoff | DS18B20 1-Wire Probe | degrees Celsius ($^\circ\text{C}$) |
| 17| `t_min` | Minimum temperature recorded | DS18B20 1-Wire Probe | degrees Celsius ($^\circ\text{C}$) |
| 18| `t_max` | Peak surface temperature reached | DS18B20 1-Wire Probe | degrees Celsius ($^\circ\text{C}$) |
| 19| `t_mean` | Mean discharge surface temperature | DS18B20 1-Wire Probe | degrees Celsius ($^\circ\text{C}$) |
| 20| `temp_rise` | Temperature change ($\Delta T = t_{\text{max}} - t_{\text{start}}$) | Derived | degrees Celsius ($^\circ\text{C}$) |
| 21| `temp_rise_rate`| Thermal rise slope ($\Delta T / \text{duration}$) | Derived | degrees Celsius/second ($^\circ\text{C}/s$) |
| 22| `temp_std` | Standard deviation of temperature trajectory | Statistical | degrees Celsius ($^\circ\text{C}$) |
| 23| `energy_wh` | Integrated discharge energy ($\int V \cdot \vert I \vert dt / 3600$) | Numerical integration | Watt-hours ($\text{Wh}$) |

### B. Lab-Only Features (2 Features)
* `re_electrolyte_ohms`: High-frequency electrolyte resistance ($\Omega$) from AC impedance sweep ($0.1\text{ Hz} - 5\text{ kHz}$).
* `rct_charge_transfer_ohms`: Charge transfer resistance ($\Omega$) from AC impedance sweep.

---

## 3. Normalization Strategy & Leakage Prevention

1. **Strict Training Fit Only**:
   * Scalers (`StandardScaler` and `RobustScaler`) were fitted **exclusively** on the Training partition (`train_features.csv`, consisting of `B0005` and `B0006`, 336 cycles).
   * Validation (`B0007`) and Holdout Test (`B0018`) data were never seen during scaler fitting.
2. **Target Isolation**:
   * Ground truth targets (`capacity_ah`, `soh_pct`, `rul_80`, `rul_70`) were strictly kept external to the feature scaling transformations.
3. **Temporal Causality**:
   * Intra-cycle features for cycle $k$ depend exclusively on cycle $k$ observations; no rolling future windows were permitted.

---

## 4. Hardware Scaling Parameters for Edge / Microcontroller Deployment

The scaling parameters in [`data/public/processed/nasa_pcoe/feature_scaler_params.json`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/feature_scaler_params.json) allow an ESP32 firmware or FastAPI service to execute instantaneous normalization:

$$x_{\text{scaled}} = \frac{x_{\text{raw}} - \mu}{\sigma}$$

#### Key Normalization Parameters (Sample):
* `duration_s`: $\mu = 3087.64\text{ s}, \quad \sigma = 265.59\text{ s}$
* `v_mean`: $\mu = 3.5204\text{ V}, \quad \sigma = 0.0538\text{ V}$
* `dc_internal_resistance`: $\mu = 0.1068\ \Omega, \quad \sigma = 0.0076\ \Omega$
* `temp_rise`: $\mu = 14.15^\circ\text{C}, \quad \sigma = 1.09^\circ\text{C}$
* `voltage_slope`: $\mu = 0.000305\text{ V/s}, \quad \sigma = 0.000038\text{ V/s}$
* `energy_wh`: $\mu = 6.0123\text{ Wh}, \quad \sigma = 0.5878\text{ Wh}$

---

## 5. Visual Artifacts Generated

1. [`feature_correlation_matrix.png`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/plots/feature_correlation_matrix.png): Correlation matrix showing Pearson coefficients between all 23 hardware features and SoH/RUL targets.
2. [`feature_distributions_unscaled_vs_scaled.png`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/plots/feature_distributions_unscaled_vs_scaled.png): Histograms verifying $\mu = 0, \sigma = 1$ standardization on training data.
3. [`hardware_aligned_features_vs_soh.png`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/plots/hardware_aligned_features_vs_soh.png): Scatter plots illustrating monotonic relationships between hardware features (`duration_s`, `dc_internal_resistance`, `temp_rise`, `voltage_slope`) and ground-truth SoH (%).
