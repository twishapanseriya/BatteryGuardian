#!/usr/bin/env python3
"""
BatteryGuardian AI - Milestone 10: Feature Visualization Suite
Generates correlation matrices, distribution comparisons, and hardware-feature vs SoH trajectories.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PROCESSED_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"
PLOTS_DIR = os.path.join(PROCESSED_DIR, "plots")

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 300

def plot_feature_correlation():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "nasa_pcoe_features_unscaled.csv"))
    
    features_to_corr = [
        "duration_s", "v_start", "v_end", "v_min", "v_mean", "v_drop", "v_std",
        "voltage_slope", "v_skew", "dc_internal_resistance", "i_mean",
        "t_start", "t_max", "t_mean", "temp_rise", "temp_rise_rate", "temp_std", "energy_wh",
        "soh_pct", "rul_80"
    ]
    
    corr = df[features_to_corr].corr()

    fig, ax = plt.subplots(figsize=(14, 11))
    cax = ax.matshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
    fig.colorbar(cax, shrink=0.8, pad=0.03, label='Pearson Correlation Coefficient')

    ticks = np.arange(len(features_to_corr))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels(features_to_corr, rotation=45, ha='left', fontsize=9)
    ax.set_yticklabels(features_to_corr, fontsize=9)

    # Annotate values on target columns (last 2 rows/cols)
    for i in range(len(features_to_corr)):
        for j in range(len(features_to_corr)):
            val = corr.iloc[i, j]
            if abs(val) > 0.7 or j >= len(features_to_corr) - 2 or i >= len(features_to_corr) - 2:
                color = 'white' if abs(val) > 0.65 else 'black'
                ax.text(j, i, f"{val:.2f}", ha='center', va='center', color=color, fontsize=7)

    ax.set_title("BatteryGuardian AI — Feature & Target Correlation Matrix (NASA PCoE Cohort)", pad=40, fontweight='bold', fontsize=13)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "feature_correlation_matrix.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_distributions_comparison():
    train_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "train_features.csv"))
    train_scaled = pd.read_csv(os.path.join(PROCESSED_DIR, "train_features_scaled.csv"))

    sample_features = [
        ("duration_s", "Duration (s)", "duration_s_scaled"),
        ("dc_internal_resistance", "DC Internal Resistance (Ω)", "dc_internal_resistance_scaled"),
        ("v_mean", "Mean Voltage (V)", "v_mean_scaled"),
        ("temp_rise", "Temperature Rise (°C)", "temp_rise_scaled")
    ]

    fig, axes = plt.subplots(4, 2, figsize=(12, 12))

    for idx, (feat, label, feat_scaled) in enumerate(sample_features):
        # Raw distribution
        ax_raw = axes[idx, 0]
        ax_raw.hist(train_raw[feat], bins=25, color='#2563EB', alpha=0.8, edgecolor='black', linewidth=0.5)
        ax_raw.set_title(f"Raw: {label}", fontweight='bold', fontsize=10)
        ax_raw.set_ylabel("Count")

        # Scaled distribution
        ax_scl = axes[idx, 1]
        ax_scl.hist(train_scaled[feat_scaled], bins=25, color='#059669', alpha=0.8, edgecolor='black', linewidth=0.5)
        ax_scl.set_title(f"Standard Scaled: {feat} (μ=0, σ=1)", fontweight='bold', fontsize=10)
        ax_scl.axvline(0, color='red', linestyle='--', linewidth=1, label='μ = 0')
        ax_scl.set_ylabel("Count")
        ax_scl.legend(fontsize=8)

    plt.suptitle("Feature Normalization Comparison (Raw Physical Units vs. Standardized z-Scores)", fontsize=13, fontweight='bold', y=0.995)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "feature_distributions_unscaled_vs_scaled.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_hw_features_vs_soh():
    train_df = pd.read_csv(os.path.join(PROCESSED_DIR, "train_features.csv"))
    val_df = pd.read_csv(os.path.join(PROCESSED_DIR, "val_features.csv"))
    test_df = pd.read_csv(os.path.join(PROCESSED_DIR, "test_features.csv"))

    key_features = [
        ("duration_s", "Discharge Duration (seconds)"),
        ("dc_internal_resistance", "DC Internal Resistance (Ohms)"),
        ("temp_rise", "Temperature Rise ΔT (°C)"),
        ("voltage_slope", "Voltage Drop Rate (V/s)")
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    for idx, (feat, label) in enumerate(key_features):
        ax = axes[idx // 2, idx % 2]
        ax.scatter(train_df[feat], train_df["soh_pct"], label="Train (B0005, B0006)", color="#2563EB", alpha=0.7, s=25)
        ax.scatter(val_df[feat], val_df["soh_pct"], label="Val (B0007)", color="#059669", alpha=0.7, s=25)
        ax.scatter(test_df[feat], test_df["soh_pct"], label="Test (B0018)", color="#D97706", alpha=0.7, s=25)

        ax.set_title(f"{label} vs. State of Health (SoH %)", fontweight='bold', fontsize=10)
        ax.set_xlabel(label)
        ax.set_ylabel("SoH (%)")
        ax.legend(loc='upper right', fontsize=8)

    plt.suptitle("Hardware-Reproducible Features vs. Ground-Truth SoH Across Partitions", fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "hardware_aligned_features_vs_soh.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

if __name__ == "__main__":
    os.makedirs(PLOTS_DIR, exist_ok=True)
    plot_feature_correlation()
    plot_distributions_comparison()
    plot_hw_features_vs_soh()
    print("\n[SUCCESS] Feature engineering visualizations generated successfully.")
