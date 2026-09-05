# NASA Ames PCoE Dataset — Milestone 9 Formal Validation & Splitting Report

## 1. Executive Summary & Verification Objective

Before model training, Milestone 9 formally validates:
1. **Cycle Segmentation**: Accurate identification and separation of `charge`, `discharge`, and `impedance` operations.
2. **Capacity Target Pairing**: True Coulomb-counted discharge capacities correctly mapped to respective cycles.
3. **Engineering Units & Physical Bounds**: Verification that voltages, currents, temperatures, and durations conform to real lithium-ion operating physics.
4. **Battery-Level Disjoint Splitting**: Partitioning strictly by battery identity ($\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$) to prevent time-series autocorrelation and data leakage.
5. **Machine-Readable Audit**: Emitting [`dataset_validation_report.json`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/dataset_validation_report.json).

---

## 2. Dataset Dimensions & Segmentation Verification

* **Master Dataset**: `nasa_pcoe_cycles.csv` (636 rows, 32 columns)
* **Raw Operation Analysis**:

| Battery ID | Total Operations in `.mat` | Charge Cycles | Discharge Cycles | Impedance Sweeps | Segmentation Status | Valid Capacity Pairing |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`B0005`** | 616 | 170 | 168 | 278 | **PASSED (OK)** | 168 / 168 (100%) |
| **`B0006`** | 616 | 170 | 168 | 278 | **PASSED (OK)** | 168 / 168 (100%) |
| **`B0007`** | 616 | 170 | 168 | 278 | **PASSED (OK)** | 168 / 168 (100%) |
| **`B0018`** | 319 | 134 | 132 | 53 | **PASSED (OK)** | 132 / 132 (100%) |
| **Cohort Total**| **2,167** | **644** | **636** | **887** | **ALL PASSED** | **636 / 636 (100%)** |

---

## 3. Battery-Level Disjoint Splits (Zero Overlap)

To prevent data leakage, samples from the same battery cell are **never** partitioned across train, validation, and test sets.

```
       +-------------------------------------------------------------+
       |                  NASA Ames Benchmark Cohort                 |
       |                   (4 Batteries, 636 Cycles)                 |
       +------------------------------+------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
+------------------+         +------------------+         +------------------+
|  TRAINING SET    |         |  VALIDATION SET  |         |   HOLDOUT TEST   |
|  B0005, B0006    |         |  B0007           |         |   B0018          |
|  336 Cycles      |         |  168 Cycles      |         |   132 Cycles     |
|  (52.83% Cohort) |         |  (26.42% Cohort) |         |   (20.75% Cohort)|
+------------------+         +------------------+         +------------------+
```

| Partition | Battery Identifiers | Cycle Count | Percentage of Cohort | Exported Dataset Path |
| :--- | :--- | :--- | :--- | :--- |
| **Training** | `B0005`, `B0006` | 336 cycles | $52.83\%$ | [`train_cycles.csv`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/train_cycles.csv) |
| **Validation**| `B0007` | 168 cycles | $26.42\%$ | [`val_cycles.csv`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/val_cycles.csv) |
| **Test** | `B0018` | 132 cycles | $20.75\%$ | [`test_cycles.csv`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/test_cycles.csv) |

* **Battery Set Overlap Check**:
  $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$
  *Confirmed: No battery ID appears in more than one partition.*

---

## 4. Target Integrity & Monotonicity Audit

1. **Capacity Bounds**: All recorded discharge capacities fall strictly within $[1.15\text{ Ah}, 2.05\text{ Ah}]$, matching the nominal $2.0\text{ Ah}$ specification.
2. **State of Health (SoH %)**: Verified against true Coulomb-counted capacity:
   $$\text{SoH}_k = \left(\frac{\text{Capacity}_k}{2.0\text{ Ah}}\right) \times 100\%$$
3. **RUL Monotonicity**: Prior to reaching the $80\%$ EOL threshold ($1.60\text{ Ah}$), ground-truth $\text{RUL}_{80}$ strictly decreases by $1$ per cycle ($\text{RUL}_{k+1} = \text{RUL}_k - 1$). At the EOL cycle, $\text{RUL} = 0$.

---

## 5. Physical Constraint & Feature Bound Audit

* **Start Voltage ($V_{\text{start}}$)**: $3.8\text{ V} \le V_{\text{start}} \le 4.3\text{ V}$ (fully charged initial state).
* **Cut-Off Voltage ($V_{\text{min}}$)**: $1.737\text{ V} \le V_{\text{min}} \le 3.0\text{ V}$ (accounting for dynamic load dips before cutoff).
* **Discharge Duration**: $2800\text{ s} \le \text{duration} \le 4000\text{ s}$ ($\sim 45-66\text{ minutes}$ at $2\text{ A}$ CC load).
* **Temperature**: $20^\circ\text{C} \le T_{\text{start}} \le 26^\circ\text{C}$; $\Delta T \ge 0^\circ\text{C}$ (exothermic discharge heating).
* **Zero Feature-Target Leakage**: Confirmed feature matrix $X$ does not contain target variables or forward-looking rolling indicators.

---

## 6. Generated Visual Artifacts

1. [`train_val_test_split_overlap_check.png`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/plots/train_val_test_split_overlap_check.png): Disjoint battery partition degradation trajectories.
2. [`segmentation_counts_check.png`](file:///home/Twisha/Startup/data/public/processed/nasa_pcoe/plots/segmentation_counts_check.png): Raw cycle operation distribution across charge, discharge, and impedance.
