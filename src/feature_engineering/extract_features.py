#!/usr/bin/env python3
"""
BatteryGuardian AI - Milestone 10: Feature Extraction Pipeline
Extracts comprehensive electrochemical, temporal, thermal, and statistical features
from the validated NASA Ames PCoE benchmark batteries (B0005, B0006, B0007, B0018).
Aligns feature definitions with hardware reproducibility standards.
"""

import os
import json
import scipy.io as sio
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.stats import skew

RAW_DATASET_DIR = "/home/Twisha/adaptive-resource-manager"
PROCESSED_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"
BENCHMARK_BATTERIES = ["B0005", "B0006", "B0007", "B0018"]
NOMINAL_CAPACITY_AH = 2.0

EOL_THRESHOLD_80_AH = 1.60
EOL_THRESHOLD_70_AH = 1.40

# Hardware Reproducibility Classification:
# Hardware-reproducible features are those that can be directly captured or computed
# from the ESP32 embedded hardware (voltage dividers, INA219 current, DS18B20 temp, and timer).
HARDWARE_REPRODUCIBLE_FEATURES = [
    "duration_s",
    "v_start",
    "v_end",
    "v_min",
    "v_max",
    "v_mean",
    "v_drop",
    "v_std",
    "voltage_slope",
    "v_skew",
    "dc_internal_resistance",
    "i_mean",
    "i_min",
    "i_max",
    "t_start",
    "t_end",
    "t_min",
    "t_max",
    "t_mean",
    "temp_rise",
    "temp_rise_rate",
    "temp_std",
    "energy_wh"
]

LAB_ONLY_FEATURES = [
    "re_electrolyte_ohms",
    "rct_charge_transfer_ohms"
]

ALL_FEATURE_COLUMNS = HARDWARE_REPRODUCIBLE_FEATURES + LAB_ONLY_FEATURES

TARGET_COLUMNS = [
    "capacity_ah",
    "nominal_capacity_ah",
    "soh_pct",
    "soh_first_cycle_pct",
    "eol_cycle_80",
    "rul_80",
    "eol_cycle_70",
    "rul_70"
]

METADATA_COLUMNS = [
    "battery_id",
    "cycle_number",
    "start_time_iso",
    "ambient_temperature"
]

def extract_battery_features(battery_id, mat_dir=RAW_DATASET_DIR):
    filepath = os.path.join(mat_dir, f"{battery_id}.mat")
    mat = sio.loadmat(filepath)
    cycle_struct = mat[battery_id][0, 0]["cycle"][0]

    # Pre-scan discharge cycles to determine true EOL cycle indices
    temp_discharge_caps = []
    for c in cycle_struct:
        if str(c["type"][0]) == "discharge":
            data = c["data"][0, 0]
            if "Capacity" in data.dtype.names and data["Capacity"].size > 0:
                temp_discharge_caps.append(float(data["Capacity"].flatten()[0]))

    eol_cycle_80 = next((idx + 1 for idx, cap in enumerate(temp_discharge_caps) if cap <= EOL_THRESHOLD_80_AH), None)
    eol_cycle_70 = next((idx + 1 for idx, cap in enumerate(temp_discharge_caps) if cap <= EOL_THRESHOLD_70_AH), None)
    initial_cap = temp_discharge_caps[0]

    impedance_history = []
    records = []
    current_discharge_cycle = 0

    for op in cycle_struct:
        op_type = str(op["type"][0])
        data = op["data"][0, 0]
        field_names = data.dtype.names

        # Causal impedance lookup (strictly preceding)
        if op_type == "impedance":
            re_val = float(data["Re"].flatten()[0]) if "Re" in field_names and data["Re"].size > 0 else np.nan
            rct_val = float(data["Rct"].flatten()[0]) if "Rct" in field_names and data["Rct"].size > 0 else np.nan
            impedance_history.append({"Re": re_val, "Rct": rct_val})
            continue

        if op_type != "discharge":
            continue

        current_discharge_cycle += 1
        if "Capacity" not in field_names or data["Capacity"].size == 0:
            continue

        cap = float(data["Capacity"].flatten()[0])
        v_arr = data["Voltage_measured"].flatten() if "Voltage_measured" in field_names else np.array([])
        i_arr = data["Current_measured"].flatten() if "Current_measured" in field_names else np.array([])
        t_arr = data["Temperature_measured"].flatten() if "Temperature_measured" in field_names else np.array([])
        time_arr = data["Time"].flatten() if "Time" in field_names else np.array([])

        if len(v_arr) == 0 or len(time_arr) == 0:
            continue

        # 1. Temporal feature
        duration_s = float(time_arr[-1] - time_arr[0])

        # 2. Voltage features
        v_start = float(v_arr[0])
        v_end = float(v_arr[-1])
        v_min = float(np.min(v_arr))
        v_max = float(np.max(v_arr))
        v_mean = float(np.mean(v_arr))
        v_drop = float(v_start - v_min)
        v_std = float(np.std(v_arr))
        v_slope = float((v_start - v_end) / duration_s) if duration_s > 0 else 0.0
        v_skew_val = float(skew(v_arr)) if len(v_arr) > 2 else 0.0

        # 3. Electrochemical DC Internal Resistance Proxy (load onset step response)
        load_idx = np.where(i_arr < -1.0)[0]
        if len(load_idx) > 0:
            fl = load_idx[0]
            v_ocv = v_arr[fl - 1] if fl > 0 else v_arr[0]
            v_load = v_arr[fl]
            i_load = i_arr[fl]
            dc_ir = float(abs(v_ocv - v_load) / abs(i_load)) if abs(i_load) > 0.1 else np.nan
        else:
            dc_ir = np.nan

        # 4. Current features
        i_mean = float(np.mean(i_arr))
        i_min = float(np.min(i_arr))
        i_max = float(np.max(i_arr))

        # 5. Thermal features
        t_start = float(t_arr[0]) if len(t_arr) > 0 else np.nan
        t_end = float(t_arr[-1]) if len(t_arr) > 0 else np.nan
        t_min = float(np.min(t_arr)) if len(t_arr) > 0 else np.nan
        t_max = float(np.max(t_arr)) if len(t_arr) > 0 else np.nan
        t_mean = float(np.mean(t_arr)) if len(t_arr) > 0 else np.nan
        temp_rise = float(t_max - t_start) if not np.isnan(t_max) and not np.isnan(t_start) else np.nan
        temp_rise_rate = float(temp_rise / duration_s) if duration_s > 0 and not np.isnan(temp_rise) else np.nan
        temp_std = float(np.std(t_arr)) if len(t_arr) > 0 else np.nan

        # 6. Energy feature
        power_w = v_arr * (-i_arr)
        energy_wh = float(np.trapezoid(power_w, time_arr / 3600.0))

        # 7. Lab EIS Impedance features (if available causally)
        latest_re = impedance_history[-1]["Re"] if impedance_history else np.nan
        latest_rct = impedance_history[-1]["Rct"] if impedance_history else np.nan

        # Targets
        soh_pct = float((cap / NOMINAL_CAPACITY_AH) * 100.0)
        soh_first_cycle_pct = float((cap / initial_cap) * 100.0)
        rul_80 = int(max(0, eol_cycle_80 - current_discharge_cycle)) if eol_cycle_80 is not None else np.nan
        rul_70 = int(max(0, eol_cycle_70 - current_discharge_cycle)) if eol_cycle_70 is not None else np.nan

        # Metadata
        amb_temp = float(op["ambient_temperature"][0, 0]) if "ambient_temperature" in op.dtype.names else 24.0
        try:
            d_vec = op["time"][0]
            start_iso = datetime(int(d_vec[0]), int(d_vec[1]), int(d_vec[2]), int(d_vec[3]), int(d_vec[4]), int(d_vec[5])).isoformat()
        except Exception:
            start_iso = ""

        rec = {
            # Metadata
            "battery_id": battery_id,
            "cycle_number": current_discharge_cycle,
            "start_time_iso": start_iso,
            "ambient_temperature": amb_temp,
            # Hardware-Reproducible Features
            "duration_s": round(duration_s, 2),
            "v_start": round(v_start, 4),
            "v_end": round(v_end, 4),
            "v_min": round(v_min, 4),
            "v_max": round(v_max, 4),
            "v_mean": round(v_mean, 4),
            "v_drop": round(v_drop, 4),
            "v_std": round(v_std, 4),
            "voltage_slope": round(v_slope, 7),
            "v_skew": round(v_skew_val, 4),
            "dc_internal_resistance": round(dc_ir, 5),
            "i_mean": round(i_mean, 4),
            "i_min": round(i_min, 4),
            "i_max": round(i_max, 4),
            "t_start": round(t_start, 2),
            "t_end": round(t_end, 2),
            "t_min": round(t_min, 2),
            "t_max": round(t_max, 2),
            "t_mean": round(t_mean, 2),
            "temp_rise": round(temp_rise, 2),
            "temp_rise_rate": round(temp_rise_rate, 6),
            "temp_std": round(temp_std, 3),
            "energy_wh": round(energy_wh, 4),
            # Lab-Only Features
            "re_electrolyte_ohms": round(latest_re, 6) if not np.isnan(latest_re) else np.nan,
            "rct_charge_transfer_ohms": round(latest_rct, 6) if not np.isnan(latest_rct) else np.nan,
            # Targets
            "capacity_ah": round(cap, 5),
            "nominal_capacity_ah": NOMINAL_CAPACITY_AH,
            "soh_pct": round(soh_pct, 3),
            "soh_first_cycle_pct": round(soh_first_cycle_pct, 3),
            "eol_cycle_80": eol_cycle_80,
            "rul_80": rul_80,
            "eol_cycle_70": eol_cycle_70,
            "rul_70": rul_70
        }
        records.append(rec)

    return pd.DataFrame(records)

def run_feature_extraction():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    all_dfs = []
    for b_id in BENCHMARK_BATTERIES:
        df_b = extract_battery_features(b_id)
        all_dfs.append(df_b)
        print(f"  [{b_id}] Extracted {len(df_b)} cycles with {len(ALL_FEATURE_COLUMNS)} features.")

    master_df = pd.concat(all_dfs, ignore_index=True)
    
    # Save master unscaled dataset
    master_unscaled_path = os.path.join(PROCESSED_DIR, "nasa_pcoe_features_unscaled.csv")
    master_df.to_csv(master_unscaled_path, index=False)
    print(f"\n[SUCCESS] Master Unscaled Features Saved: {master_unscaled_path} ({len(master_df)} rows, {len(master_df.columns)} cols)")

    # Partition by battery identity
    train_df = master_df[master_df["battery_id"].isin(["B0005", "B0006"])].copy()
    val_df = master_df[master_df["battery_id"].isin(["B0007"])].copy()
    test_df = master_df[master_df["battery_id"].isin(["B0018"])].copy()

    train_path = os.path.join(PROCESSED_DIR, "train_features.csv")
    val_path = os.path.join(PROCESSED_DIR, "val_features.csv")
    test_path = os.path.join(PROCESSED_DIR, "test_features.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"  -> Train Features: {train_path} ({len(train_df)} rows)")
    print(f"  -> Val Features  : {val_path} ({len(val_df)} rows)")
    print(f"  -> Test Features : {test_path} ({len(test_df)} rows)")

    return master_df, train_df, val_df, test_df

if __name__ == "__main__":
    run_feature_extraction()
