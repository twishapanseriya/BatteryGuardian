#!/usr/bin/env python3
"""
BatteryGuardian AI - Milestone 10: Feature Normalization & Scaling Pipeline
Fits Standard and Robust Scalers EXCLUSIVELY on the Training Partition (B0005, B0006),
transforms Validation (B0007) and Holdout Test (B0018) without any data leakage,
and exports edge-compatible scaling parameters for hardware deployment.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from datetime import datetime

PROCESSED_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"

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

FEATURE_UNITS = {
    "duration_s": "seconds",
    "v_start": "Volts",
    "v_end": "Volts",
    "v_min": "Volts",
    "v_max": "Volts",
    "v_mean": "Volts",
    "v_drop": "Volts",
    "v_std": "Volts",
    "voltage_slope": "Volts/second",
    "v_skew": "dimensionless",
    "dc_internal_resistance": "Ohms",
    "i_mean": "Amperes",
    "i_min": "Amperes",
    "i_max": "Amperes",
    "t_start": "degrees Celsius",
    "t_end": "degrees Celsius",
    "t_min": "degrees Celsius",
    "t_max": "degrees Celsius",
    "t_mean": "degrees Celsius",
    "temp_rise": "degrees Celsius",
    "temp_rise_rate": "degrees Celsius/second",
    "temp_std": "degrees Celsius",
    "energy_wh": "Watt-hours"
}

METADATA_COLS = ["battery_id", "cycle_number", "start_time_iso", "ambient_temperature"]
TARGET_COLS = ["capacity_ah", "nominal_capacity_ah", "soh_pct", "soh_first_cycle_pct", "eol_cycle_80", "rul_80", "eol_cycle_70", "rul_70"]

def run_normalization():
    train_path = os.path.join(PROCESSED_DIR, "train_features.csv")
    val_path = os.path.join(PROCESSED_DIR, "val_features.csv")
    test_path = os.path.join(PROCESSED_DIR, "test_features.csv")

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    print(f"[LOAD] Train: {len(train_df)} rows, Val: {len(val_df)} rows, Test: {len(test_df)} rows")

    X_train_raw = train_df[HARDWARE_REPRODUCIBLE_FEATURES].copy()
    X_val_raw = val_df[HARDWARE_REPRODUCIBLE_FEATURES].copy()
    X_test_raw = test_df[HARDWARE_REPRODUCIBLE_FEATURES].copy()

    # 1. Fit StandardScaler STRICTLY on Training Set
    std_scaler = StandardScaler()
    std_scaler.fit(X_train_raw)

    # 2. Fit RobustScaler STRICTLY on Training Set
    rob_scaler = RobustScaler()
    rob_scaler.fit(X_train_raw)

    print("[FIT] Fitted StandardScaler and RobustScaler strictly on Training Partition (B0005, B0006).")

    # Transform partitions
    X_train_std = std_scaler.transform(X_train_raw)
    X_val_std = std_scaler.transform(X_val_raw)
    X_test_std = std_scaler.transform(X_test_raw)

    X_train_rob = rob_scaler.transform(X_train_raw)
    X_val_rob = rob_scaler.transform(X_val_raw)
    X_test_rob = rob_scaler.transform(X_test_raw)

    # Build Standard Scaled DataFrames
    def make_scaled_df(base_df, X_scaled):
        df_scaled = base_df[METADATA_COLS].copy()
        for idx, feat in enumerate(HARDWARE_REPRODUCIBLE_FEATURES):
            df_scaled[f"{feat}_scaled"] = np.round(X_scaled[:, idx], 5)
        for t_col in TARGET_COLS:
            df_scaled[t_col] = base_df[t_col]
        return df_scaled

    train_scaled_df = make_scaled_df(train_df, X_train_std)
    val_scaled_df = make_scaled_df(val_df, X_val_std)
    test_scaled_df = make_scaled_df(test_df, X_test_std)

    train_rob_df = make_scaled_df(train_df, X_train_rob)
    val_rob_df = make_scaled_df(val_df, X_val_rob)
    test_rob_df = make_scaled_df(test_df, X_test_rob)

    # Export CSVs
    train_scaled_path = os.path.join(PROCESSED_DIR, "train_features_scaled.csv")
    val_scaled_path = os.path.join(PROCESSED_DIR, "val_features_scaled.csv")
    test_scaled_path = os.path.join(PROCESSED_DIR, "test_features_scaled.csv")

    train_scaled_df.to_csv(train_scaled_path, index=False)
    val_scaled_df.to_csv(val_scaled_path, index=False)
    test_scaled_df.to_csv(test_scaled_path, index=False)

    train_rob_df.to_csv(os.path.join(PROCESSED_DIR, "train_features_scaled_robust.csv"), index=False)
    val_rob_df.to_csv(os.path.join(PROCESSED_DIR, "val_features_scaled_robust.csv"), index=False)
    test_rob_df.to_csv(os.path.join(PROCESSED_DIR, "test_features_scaled_robust.csv"), index=False)

    print(f"  -> Saved Standard Scaled Train: {train_scaled_path}")
    print(f"  -> Saved Standard Scaled Val  : {val_scaled_path}")
    print(f"  -> Saved Standard Scaled Test : {test_scaled_path}")

    # Serialize Pickled Scalers
    std_pkl_path = os.path.join(PROCESSED_DIR, "feature_scaler_standard.pkl")
    rob_pkl_path = os.path.join(PROCESSED_DIR, "feature_scaler_robust.pkl")
    with open(std_pkl_path, "wb") as f:
        pickle.dump(std_scaler, f)
    with open(rob_pkl_path, "wb") as f:
        pickle.dump(rob_scaler, f)

    # Edge / Hardware Deployment Scaling Parameters JSON
    scaler_params = {
        "scaler_type": "StandardScaler (z = (x - mean) / std)",
        "fitted_on_batteries": ["B0005", "B0006"],
        "training_samples": len(train_df),
        "feature_count": len(HARDWARE_REPRODUCIBLE_FEATURES),
        "created_at": datetime.now().isoformat(),
        "hardware_scaling_constants": {}
    }

    for idx, feat in enumerate(HARDWARE_REPRODUCIBLE_FEATURES):
        mean_val = float(std_scaler.mean_[idx])
        std_val = float(std_scaler.scale_[idx])
        min_val = float(X_train_raw[feat].min())
        max_val = float(X_train_raw[feat].max())
        med_val = float(rob_scaler.center_[idx])
        iqr_val = float(rob_scaler.scale_[idx])

        scaler_params["hardware_scaling_constants"][feat] = {
            "index": idx,
            "unit": FEATURE_UNITS.get(feat, "unknown"),
            "mean": round(mean_val, 6),
            "std": round(std_val, 6),
            "median": round(med_val, 6),
            "iqr": round(iqr_val, 6),
            "min": round(min_val, 6),
            "max": round(max_val, 6),
            "c_code_scaling_macro": f"((raw_{feat} - ({mean_val:.6f}f)) / ({std_val:.6f}f))"
        }

    params_json_path = os.path.join(PROCESSED_DIR, "feature_scaler_params.json")
    with open(params_json_path, "w") as f:
        json.dump(scaler_params, f, indent=2)
    print(f"  -> Saved Edge Hardware Scaling Parameters: {params_json_path}")

    # Machine-Readable Feature Engineering Report
    report = {
        "milestone": 10,
        "title": "BatteryGuardian AI - Feature Engineering & Normalization Report",
        "dataset_name": "NASA Ames PCoE Battery Aging Dataset",
        "total_cycles_processed": len(train_df) + len(val_df) + len(test_df),
        "partition_sizes": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df)
        },
        "total_features_extracted": len(HARDWARE_REPRODUCIBLE_FEATURES) + 2, # + 2 lab EIS
        "hardware_reproducible_features_count": len(HARDWARE_REPRODUCIBLE_FEATURES),
        "lab_only_features_count": 2,
        "hardware_features_list": HARDWARE_REPRODUCIBLE_FEATURES,
        "feature_units": FEATURE_UNITS,
        "normalization_methods": [
            "StandardScaler: z = (x - mean) / std (Zero mean, unit variance)",
            "RobustScaler: z = (x - median) / IQR (Percentile-based, outlier-resistant)"
        ],
        "leakage_checks_passed": [
            "Scalers fitted EXCLUSIVELY on training data (B0005, B0006).",
            "Zero validation or test data touched during fit.",
            "Features are purely intra-cycle; zero future-cycle lookahead.",
            "Targets (capacity, SoH, RUL) strictly excluded from feature matrix."
        ],
        "hardware_reproducibility_alignment": {
            "voltage_divider": "duration_s, v_start, v_end, v_min, v_max, v_mean, v_drop, v_std, voltage_slope, v_skew, dc_internal_resistance",
            "ina219_current_sensor": "i_mean, i_min, i_max, dc_internal_resistance, energy_wh",
            "ds18b20_temperature_probes": "t_start, t_end, t_min, t_max, t_mean, temp_rise, temp_rise_rate, temp_std",
            "mcu_timer": "duration_s, temp_rise_rate, voltage_slope",
            "c_code_deployment_ready": True
        },
        "artifacts_generated": [
            "data/public/processed/nasa_pcoe/nasa_pcoe_features_unscaled.csv",
            "data/public/processed/nasa_pcoe/train_features.csv",
            "data/public/processed/nasa_pcoe/val_features.csv",
            "data/public/processed/nasa_pcoe/test_features.csv",
            "data/public/processed/nasa_pcoe/train_features_scaled.csv",
            "data/public/processed/nasa_pcoe/val_features_scaled.csv",
            "data/public/processed/nasa_pcoe/test_features_scaled.csv",
            "data/public/processed/nasa_pcoe/feature_scaler_standard.pkl",
            "data/public/processed/nasa_pcoe/feature_scaler_robust.pkl",
            "data/public/processed/nasa_pcoe/feature_scaler_params.json"
        ]
    }

    report_path = os.path.join(PROCESSED_DIR, "feature_engineering_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  -> Saved Feature Engineering Report: {report_path}")

    return scaler_params

if __name__ == "__main__":
    run_normalization()
