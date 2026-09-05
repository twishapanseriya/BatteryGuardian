#!/usr/bin/env python3
"""
BatteryGuardian AI - NASA PCoE Dataset Parser & Processor
Parses benchmark NASA Ames Li-ion battery aging datasets (B0005, B0006, B0007, B0018),
extracts cycle-level operational features, computes true capacity-based SoH and RUL targets,
and exports clean, leak-free CSV datasets for ML training and evaluation.
"""

import os
import json
import scipy.io as sio
import numpy as np
import pandas as pd
from datetime import datetime

DATASET_DIR = "/home/Twisha/adaptive-resource-manager"
OUTPUT_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"
BENCHMARK_BATTERIES = ["B0005", "B0006", "B0007", "B0018"]
NOMINAL_CAPACITY_AH = 2.0

# EOL Thresholds:
# 1. Standard Industry EOL: 80% nominal capacity retention = 1.60 Ah (20% fade)
# 2. NASA Ames Experimental Termination EOL: 70% nominal capacity retention = 1.40 Ah (30% fade)
EOL_THRESHOLD_80_AH = 1.60
EOL_THRESHOLD_70_AH = 1.40

def parse_battery_mat(battery_id, mat_dir=DATASET_DIR):
    """
    Parse raw NASA .mat file into structured list of discharge cycle summaries.
    Ensures zero future-cycle leakage.
    """
    filepath = os.path.join(mat_dir, f"{battery_id}.mat")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing NASA dataset file: {filepath}")

    print(f"[PARSER] Loading {filepath}...")
    mat = sio.loadmat(filepath)
    cycle_struct = mat[battery_id][0, 0]["cycle"][0]

    # Pre-scan impedance operations to enable causal (past-only) impedance feature lookup
    impedance_history = []
    
    # Pre-scan discharge cycles to determine true EOL cycle indices
    temp_discharge_caps = []
    for c in cycle_struct:
        c_type = str(c["type"][0])
        if c_type == "discharge":
            data = c["data"][0, 0]
            if "Capacity" in data.dtype.names and data["Capacity"].size > 0:
                cap_val = float(data["Capacity"].flatten()[0])
                temp_discharge_caps.append(cap_val)

    # Determine ground-truth EOL cycle indices
    eol_cycle_80 = next((idx + 1 for idx, cap in enumerate(temp_discharge_caps) if cap <= EOL_THRESHOLD_80_AH), None)
    eol_cycle_70 = next((idx + 1 for idx, cap in enumerate(temp_discharge_caps) if cap <= EOL_THRESHOLD_70_AH), None)

    print(f"  [{battery_id}] Total Discharges: {len(temp_discharge_caps)}")
    print(f"  [{battery_id}] Initial Cap: {temp_discharge_caps[0]:.4f} Ah | Final Cap: {temp_discharge_caps[-1]:.4f} Ah")
    print(f"  [{battery_id}] EOL 80% (1.60Ah): Cycle {eol_cycle_80} | EOL 70% (1.40Ah): Cycle {eol_cycle_70}")

    initial_cap = temp_discharge_caps[0]
    records = []
    current_discharge_cycle = 0

    # Process operations sequentially (chronological order)
    for op in cycle_struct:
        op_type = str(op["type"][0])
        data = op["data"][0, 0]
        field_names = data.dtype.names

        # Track impedance operations (strictly prior or concurrent, never future)
        if op_type == "impedance":
            re_val = float(data["Re"].flatten()[0]) if "Re" in field_names and data["Re"].size > 0 else np.nan
            rct_val = float(data["Rct"].flatten()[0]) if "Rct" in field_names and data["Rct"].size > 0 else np.nan
            impedance_history.append({"Re": re_val, "Rct": rct_val})
            continue

        if op_type != "discharge":
            continue

        current_discharge_cycle += 1
        
        # Verify Capacity target exists
        if "Capacity" not in field_names or data["Capacity"].size == 0:
            continue
        
        cap = float(data["Capacity"].flatten()[0])
        
        # Continuous time-series vectors for this discharge cycle
        v_arr = data["Voltage_measured"].flatten() if "Voltage_measured" in field_names else np.array([])
        i_arr = data["Current_measured"].flatten() if "Current_measured" in field_names else np.array([])
        t_arr = data["Temperature_measured"].flatten() if "Temperature_measured" in field_names else np.array([])
        time_arr = data["Time"].flatten() if "Time" in field_names else np.array([])

        if len(v_arr) == 0 or len(time_arr) == 0:
            continue

        # Extract strictly current-cycle features
        duration_s = float(time_arr[-1] - time_arr[0])
        v_start = float(v_arr[0])
        v_end = float(v_arr[-1])
        v_min = float(np.min(v_arr))
        v_max = float(np.max(v_arr))
        v_mean = float(np.mean(v_arr))
        v_drop = float(v_start - v_min)

        i_mean = float(np.mean(i_arr))
        i_min = float(np.min(i_arr))
        i_max = float(np.max(i_arr))

        t_start = float(t_arr[0]) if len(t_arr) > 0 else np.nan
        t_end = float(t_arr[-1]) if len(t_arr) > 0 else np.nan
        t_min = float(np.min(t_arr)) if len(t_arr) > 0 else np.nan
        t_max = float(np.max(t_arr)) if len(t_arr) > 0 else np.nan
        t_mean = float(np.mean(t_arr)) if len(t_arr) > 0 else np.nan
        temp_rise = float(t_max - t_start) if not np.isnan(t_max) and not np.isnan(t_start) else np.nan
        temp_rise_rate = float(temp_rise / duration_s) if duration_s > 0 and not np.isnan(temp_rise) else np.nan

        # Discharge energy via numerical integration: P = V * (-I)
        # Note: In NASA dataset, discharge current is negative (e.g. -2.0 A)
        power_w = v_arr * (-i_arr)
        energy_wh = float(np.trapezoid(power_w, time_arr / 3600.0))

        # Nearest prior impedance parameters (causal lookup)
        latest_re = impedance_history[-1]["Re"] if impedance_history else np.nan
        latest_rct = impedance_history[-1]["Rct"] if impedance_history else np.nan

        # Target 1: State of Health (SoH %) relative to nominal rated capacity (2.0 Ah)
        soh_pct = float((cap / NOMINAL_CAPACITY_AH) * 100.0)

        # Target 2: State of Health relative to fresh first-cycle capacity
        soh_first_cycle_pct = float((cap / initial_cap) * 100.0)

        # Target 3: Remaining Useful Life (RUL) to 80% EOL (1.60 Ah)
        if eol_cycle_80 is not None:
            rul_80 = int(max(0, eol_cycle_80 - current_discharge_cycle))
        else:
            rul_80 = np.nan

        # Target 4: Remaining Useful Life (RUL) to 70% EOL (1.40 Ah)
        if eol_cycle_70 is not None:
            rul_70 = int(max(0, eol_cycle_70 - current_discharge_cycle))
        else:
            rul_70 = np.nan  # B0007 does not reach 1.40 Ah in test window

        # Ambient temperature & start date
        amb_temp = float(op["ambient_temperature"][0, 0]) if "ambient_temperature" in op.dtype.names else 24.0
        
        # Operation start date
        try:
            date_vec = op["time"][0]
            start_iso = datetime(
                int(date_vec[0]), int(date_vec[1]), int(date_vec[2]),
                int(date_vec[3]), int(date_vec[4]), int(date_vec[5])
            ).isoformat()
        except Exception:
            start_iso = ""

        records.append({
            "battery_id": battery_id,
            "cycle_number": current_discharge_cycle,
            "start_time_iso": start_iso,
            "ambient_temperature": amb_temp,
            # Time & duration features
            "duration_s": round(duration_s, 2),
            # Voltage features
            "v_start": round(v_start, 4),
            "v_end": round(v_end, 4),
            "v_min": round(v_min, 4),
            "v_max": round(v_max, 4),
            "v_mean": round(v_mean, 4),
            "v_drop": round(v_drop, 4),
            # Current features
            "i_mean": round(i_mean, 4),
            "i_min": round(i_min, 4),
            "i_max": round(i_max, 4),
            # Thermal features
            "t_start": round(t_start, 2),
            "t_end": round(t_end, 2),
            "t_min": round(t_min, 2),
            "t_max": round(t_max, 2),
            "t_mean": round(t_mean, 2),
            "temp_rise": round(temp_rise, 2),
            "temp_rise_rate": round(temp_rise_rate, 6),
            # Energy
            "energy_wh": round(energy_wh, 4),
            # Impedance (if available)
            "re_electrolyte_ohms": round(latest_re, 6) if not np.isnan(latest_re) else np.nan,
            "rct_charge_transfer_ohms": round(latest_rct, 6) if not np.isnan(latest_rct) else np.nan,
            # Ground-Truth Targets
            "capacity_ah": round(cap, 5),
            "nominal_capacity_ah": NOMINAL_CAPACITY_AH,
            "soh_pct": round(soh_pct, 3),
            "soh_first_cycle_pct": round(soh_first_cycle_pct, 3),
            "eol_cycle_80": eol_cycle_80,
            "rul_80": rul_80,
            "eol_cycle_70": eol_cycle_70,
            "rul_70": rul_70
        })

    return pd.DataFrame(records)

def process_all_benchmark_batteries():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_dfs = []

    for b_id in BENCHMARK_BATTERIES:
        df = parse_battery_mat(b_id)
        # Save individual battery file
        indiv_path = os.path.join(OUTPUT_DIR, f"{b_id}_cycles.csv")
        df.to_csv(indiv_path, index=False)
        print(f"  -> Saved {indiv_path} ({len(df)} cycles)")
        all_dfs.append(df)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_path = os.path.join(OUTPUT_DIR, "nasa_pcoe_cycles.csv")
    combined_df.to_csv(combined_path, index=False)
    print(f"\n[SUCCESS] Exported combined dataset: {combined_path}")
    print(f"  Total Rows (cycles): {len(combined_df)}")
    print(f"  Total Columns: {len(combined_df.columns)}")

    # Save metadata summary
    metadata = {
        "dataset_name": "NASA Ames PCoE Battery Aging Dataset",
        "official_source": "NASA Ames Prognostics Center of Excellence (B. Saha & K. Goebel, 2007)",
        "batteries_processed": BENCHMARK_BATTERIES,
        "total_discharge_cycles": int(len(combined_df)),
        "nominal_capacity_ah": NOMINAL_CAPACITY_AH,
        "eol_threshold_80_ah": EOL_THRESHOLD_80_AH,
        "eol_threshold_70_ah": EOL_THRESHOLD_70_AH,
        "eol_cycle_summary": {
            "B0005": {"eol_80": 75, "eol_70": 125, "total_cycles": 168},
            "B0006": {"eol_80": 63, "eol_70": 109, "total_cycles": 168},
            "B0007": {"eol_80": 86, "eol_70": None, "total_cycles": 168, "notes": "Ended at 1.4005 Ah; did not reach <= 1.40 Ah"},
            "B0018": {"eol_80": 45, "eol_70": 97, "total_cycles": 132}
        },
        "extracted_features": [
            "duration_s", "v_start", "v_end", "v_min", "v_max", "v_mean", "v_drop",
            "i_mean", "i_min", "i_max", "t_start", "t_end", "t_min", "t_max", "t_mean",
            "temp_rise", "temp_rise_rate", "energy_wh", "re_electrolyte_ohms", "rct_charge_transfer_ohms"
        ],
        "ground_truth_targets": [
            "capacity_ah", "soh_pct", "soh_first_cycle_pct", "rul_80", "rul_70"
        ],
        "leakage_protection": "All cycle features computed strictly from intra-cycle measurements or causal preceding impedance sweeps; no future-cycle leakage.",
        "processed_at": datetime.now().isoformat()
    }

    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  -> Saved metadata: {metadata_path}")

    return combined_df

if __name__ == "__main__":
    process_all_benchmark_batteries()
