# NASA Ames PCoE Battery Aging Dataset — Processing & Provenance Documentation

## 1. Dataset Provenance & Overview

* **Dataset Title**: NASA Ames Prognostics Center of Excellence (PCoE) Battery Aging Dataset
* **Source Organization**: NASA Ames Research Center, Moffett Field, CA, USA
* **Authors / Reference**: B. Saha and K. Goebel (2007), *"Battery Data Set"*, NASA Ames Prognostics Data Repository
* **Battery Chemistry**: Commercial 18650 Cylindrical Cells, $\text{LiCoO}_2$ cathode / Graphite anode
* **Nominal Rating**: $3.7\text{ V}$ nominal terminal voltage, $2.0\text{ Ah}$ nominal rated capacity ($7.4\text{ Wh}$)
* **Operating Profile**:
  * **Charging**: Constant Current (CC) mode at $1.5\text{ A}$ to $4.2\text{ V}$, then Constant Voltage (CV) mode until current decayed to $20\text{ mA}$.
  * **Discharging**: Constant Current (CC) load at $2.0\text{ A}$ ($1.0\text{C}$ rate) down to designated cut-off voltages:
    * `B0005`: Cut-off at $2.7\text{ V}$
    * `B0006`: Cut-off at $2.5\text{ V}$
    * `B0007`: Cut-off at $2.2\text{ V}$
    * `B0018`: Cut-off at $2.5\text{ V}$
  * **Impedance (EIS)**: Frequency sweep from $0.1\text{ Hz}$ to $5\text{ kHz}$ to characterize internal electrolyte ($R_e$) and charge transfer ($R_{ct}$) resistance.

---

## 2. Processed Cycle Dataset Summary

* **Processed Master File**: `data/public/processed/nasa_pcoe/nasa_pcoe_cycles.csv`
* **Total Discharge Cycles Processed**: $636\text{ cycles}$
* **Battery Breakdown**:
  * `B0005`: $168\text{ cycles}$ (Capacity: $1.8565\text{ Ah} \to 1.3251\text{ Ah}$)
  * `B0006`: $168\text{ cycles}$ (Capacity: $2.0353\text{ Ah} \to 1.1857\text{ Ah}$)
  * `B0007`: $168\text{ cycles}$ (Capacity: $1.8911\text{ Ah} \to 1.4325\text{ Ah}$)
  * `B0018`: $132\text{ cycles}$ (Capacity: $1.8550\text{ Ah} \to 1.3411\text{ Ah}$)

---

## 3. Ground-Truth Target Definitions

### A. State of Health (SoH %)
1. **Nominal SoH** ($\text{soh\_pct}$):
   $$\text{SoH}_k = \left(\frac{\text{Capacity}_k}{C_{\text{nominal}}}\right) \times 100\% = \left(\frac{\text{Capacity}_k}{2.0\text{ Ah}}\right) \times 100\%$$
2. **First-Cycle Normalized SoH** ($\text{soh\_first\_cycle\_pct}$):
   $$\text{SoH}_{1, k} = \left(\frac{\text{Capacity}_k}{\text{Capacity}_1}\right) \times 100\%$$

### B. Remaining Useful Life (RUL)
1. **Standard Industry 80% EOL ($1.60\text{ Ah}$ / 20% degradation)**:
   $$\text{RUL}_{80, k} = \max\left(0, \text{EOL\_Cycle}_{80} - k\right)$$
   * `B0005`: $\text{EOL}_{80} = \text{Cycle } 75$
   * `B0006`: $\text{EOL}_{80} = \text{Cycle } 63$
   * `B0007`: $\text{EOL}_{80} = \text{Cycle } 86$
   * `B0018`: $\text{EOL}_{80} = \text{Cycle } 45$
2. **NASA Experimental 70% EOL ($1.40\text{ Ah}$ / 30% fade)**:
   $$\text{RUL}_{70, k} = \max\left(0, \text{EOL\_Cycle}_{70} - k\right)$$
   * `B0005`: $\text{EOL}_{70} = \text{Cycle } 125$
   * `B0006`: $\text{EOL}_{70} = \text{Cycle } 109$
   * `B0007`: Did not drop $\le 1.40\text{ Ah}$ during testing (minimum capacity reached was $1.4005\text{ Ah}$).
   * `B0018`: $\text{EOL}_{70} = \text{Cycle } 97$

---

## 4. Feature Extraction & Engineering Units

All features for cycle $k$ are derived strictly from intra-cycle time-series arrays or preceding impedance operations:

| Feature Name | Description | Source Field | Unit |
| :--- | :--- | :--- | :--- |
| `duration_s` | Total discharge duration ($t_{\text{end}} - t_0$) | `Time` | Seconds ($s$) |
| `v_start` | Terminal voltage at onset of discharge | `Voltage_measured[0]` | Volts ($V$) |
| `v_end` | Final voltage at load disconnect | `Voltage_measured[-1]` | Volts ($V$) |
| `v_min` | Minimum voltage reached under load | `min(Voltage_measured)` | Volts ($V$) |
| `v_max` | Peak voltage observed during discharge | `max(Voltage_measured)` | Volts ($V$) |
| `v_mean` | Mean discharge terminal voltage | `mean(Voltage_measured)`| Volts ($V$) |
| `v_drop` | Voltage drop from start to cutoff | `v_start - v_min` | Volts ($V$) |
| `i_mean` | Average discharge current | `mean(Current_measured)`| Amperes ($A$) |
| `i_min` | Minimum discharge current (most negative) | `min(Current_measured)` | Amperes ($A$) |
| `i_max` | Maximum discharge current | `max(Current_measured)` | Amperes ($A$) |
| `t_start` | Surface temperature at start of discharge | `Temperature_measured[0]`| Celsius ($^\circ\text{C}$) |
| `t_end` | Surface temperature at cutoff | `Temperature_measured[-1]`| Celsius ($^\circ\text{C}$) |
| `t_min` | Minimum temperature during cycle | `min(Temperature_measured)`| Celsius ($^\circ\text{C}$) |
| `t_max` | Peak surface temperature reached | `max(Temperature_measured)`| Celsius ($^\circ\text{C}$) |
| `t_mean` | Mean discharge surface temperature | `mean(Temperature_measured)`| Celsius ($^\circ\text{C}$) |
| `temp_rise` | Temperature change ($\Delta T = t_{\text{max}} - t_{\text{start}}$) | Temperature diff | Celsius ($^\circ\text{C}$) |
| `temp_rise_rate` | Thermal rate of change ($\Delta T / \text{duration}$) | Thermal slope | $^\circ\text{C} / s$ |
| `energy_wh` | Integrated discharge energy ($\int V \cdot (-I) dt$) | Trapezoidal numerical int. | Watt-hours ($\text{Wh}$) |
| `re_electrolyte_ohms` | Electrolyte resistance from nearest prior EIS | `Re` | Ohms ($\Omega$) |
| `rct_charge_transfer_ohms` | Charge transfer resistance from prior EIS | `Rct` | Ohms ($\Omega$) |

---

## 5. Leakage Prevention Methodology

1. **Intra-Cycle Temporal Causality**:
   * Features at cycle $k$ depend **strictly** on measurements recorded within cycle $k$ (or preceding cycles $\le k$).
   * No future information (e.g. from cycle $k+1$) is accessible during feature calculation for cycle $k$.
2. **Feature-Target Isolation**:
   * Measured discharge capacity, SoH, and RUL are strictly labeled as ground-truth targets and excluded from the predictive feature matrix $X$.
3. **No Mixed In-Cycle Splitting**:
   * In future ML training (Milestones 10–12), validation splits will be grouped strictly by battery or time-ordered cycle windows to prevent time-series autocorrelation leakage.

---

## 6. Generated Visualization Artifacts

The following high-resolution plots are available in `data/public/processed/nasa_pcoe/plots/`:
1. `capacity_vs_cycle.png`: Measured capacity degradation trajectories with $1.60\text{ Ah}$ and $1.40\text{ Ah}$ EOL reference lines.
2. `soh_vs_cycle.png`: Normalized State of Health (%) decay curves.
3. `temperature_rise_vs_cycle.png`: Thermal degradation ($\Delta T$) progression.
4. `discharge_duration_vs_cycle.png`: Discharge time fade curves.
5. `degradation_dashboard.png`: Unified 4-panel publication-grade degradation dashboard.
