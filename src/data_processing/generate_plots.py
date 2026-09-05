#!/usr/bin/env python3
"""
BatteryGuardian AI - NASA PCoE Degradation Visualizer
Generates high-resolution data-integrity and degradation trajectory plots for
benchmark cells B0005, B0006, B0007, and B0018.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DATA_FILE = "/home/Twisha/Startup/data/public/processed/nasa_pcoe/nasa_pcoe_cycles.csv"
PLOTS_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe/plots"

# Set publication style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 300

BATTERY_COLORS = {
    'B0005': '#2563EB', # Royal Blue
    'B0006': '#DC2626', # Crimson Red
    'B0007': '#059669', # Emerald Green
    'B0018': '#D97706', # Amber Orange
}

def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Missing processed data file: {DATA_FILE}")
    return pd.read_csv(DATA_FILE)

def plot_capacity_vs_cycle(df):
    plt.figure(figsize=(10, 6))
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        plt.plot(b_df['cycle_number'], b_df['capacity_ah'], label=f"{b_id} (Actual)", color=color, linewidth=2.0, alpha=0.9)
    
    # EOL Thresholds
    plt.axhline(y=1.60, color='#6B7280', linestyle='--', linewidth=1.5, label='Standard EOL (80% / 1.60 Ah)')
    plt.axhline(y=1.40, color='#111827', linestyle=':', linewidth=1.8, label='NASA EOL (70% / 1.40 Ah)')

    plt.title("NASA Ames PCoE Battery Aging — Discharge Capacity vs. Cycle Number", pad=12, fontweight='bold')
    plt.xlabel("Discharge Cycle Number")
    plt.ylabel("Measured Discharge Capacity (Ah)")
    plt.ylim(1.10, 2.15)
    plt.xlim(0, 175)
    plt.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.95)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "capacity_vs_cycle.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_soh_vs_cycle(df):
    plt.figure(figsize=(10, 6))
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        plt.plot(b_df['cycle_number'], b_df['soh_pct'], label=f"{b_id} (SoH %)", color=color, linewidth=2.0, alpha=0.9)
    
    plt.axhline(y=80.0, color='#6B7280', linestyle='--', linewidth=1.5, label='80% SoH Threshold')
    plt.axhline(y=70.0, color='#111827', linestyle=':', linewidth=1.8, label='70% SoH Threshold (NASA EOL)')

    plt.title("NASA Ames PCoE Battery Aging — State of Health (SoH %) Degradation Trajectories", pad=12, fontweight='bold')
    plt.xlabel("Discharge Cycle Number")
    plt.ylabel("State of Health — SoH (%) [Ref: 2.0 Ah Nominal]")
    plt.ylim(55.0, 105.0)
    plt.xlim(0, 175)
    plt.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.95)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "soh_vs_cycle.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_temperature_rise_vs_cycle(df):
    plt.figure(figsize=(10, 6))
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        plt.plot(b_df['cycle_number'], b_df['temp_rise'], label=f"{b_id} (ΔT)", color=color, linewidth=1.8, alpha=0.85)

    plt.title("NASA Ames PCoE Battery Aging — Discharge Temperature Rise (ΔT) vs. Cycle", pad=12, fontweight='bold')
    plt.xlabel("Discharge Cycle Number")
    plt.ylabel("Temperature Rise ΔT (°C)")
    plt.xlim(0, 175)
    plt.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.95)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "temperature_rise_vs_cycle.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_discharge_duration_vs_cycle(df):
    plt.figure(figsize=(10, 6))
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        plt.plot(b_df['cycle_number'], b_df['duration_s'] / 60.0, label=f"{b_id} Duration", color=color, linewidth=1.8, alpha=0.85)

    plt.title("NASA Ames PCoE Battery Aging — Discharge Duration (Minutes) vs. Cycle", pad=12, fontweight='bold')
    plt.xlabel("Discharge Cycle Number")
    plt.ylabel("Discharge Duration (Minutes)")
    plt.xlim(0, 175)
    plt.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.95)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "discharge_duration_vs_cycle.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

def plot_multipanel_dashboard(df):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    # Panel 1: Discharge Capacity
    ax1 = axes[0, 0]
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        ax1.plot(b_df['cycle_number'], b_df['capacity_ah'], label=b_id, color=color, linewidth=1.8)
    ax1.axhline(1.60, color='#6B7280', linestyle='--', label='80% EOL (1.60 Ah)')
    ax1.axhline(1.40, color='#111827', linestyle=':', label='70% EOL (1.40 Ah)')
    ax1.set_title("(A) Discharge Capacity Degradation", fontweight='bold')
    ax1.set_xlabel("Cycle Number")
    ax1.set_ylabel("Capacity (Ah)")
    ax1.legend(loc='upper right', fontsize=9)

    # Panel 2: State of Health (SoH %)
    ax2 = axes[0, 1]
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        ax2.plot(b_df['cycle_number'], b_df['soh_pct'], label=b_id, color=color, linewidth=1.8)
    ax2.axhline(80.0, color='#6B7280', linestyle='--', label='80% SoH')
    ax2.axhline(70.0, color='#111827', linestyle=':', label='70% SoH')
    ax2.set_title("(B) State of Health (SoH %) Retention", fontweight='bold')
    ax2.set_xlabel("Cycle Number")
    ax2.set_ylabel("SoH (%)")
    ax2.legend(loc='upper right', fontsize=9)

    # Panel 3: Temperature Rise
    ax3 = axes[1, 0]
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        ax3.plot(b_df['cycle_number'], b_df['temp_rise'], label=b_id, color=color, linewidth=1.6)
    ax3.set_title("(C) Discharge Temperature Rise (ΔT)", fontweight='bold')
    ax3.set_xlabel("Cycle Number")
    ax3.set_ylabel("Temp Rise (°C)")
    ax3.legend(loc='upper left', fontsize=9)

    # Panel 4: Discharge Duration
    ax4 = axes[1, 1]
    for b_id, color in BATTERY_COLORS.items():
        b_df = df[df['battery_id'] == b_id]
        ax4.plot(b_df['cycle_number'], b_df['duration_s'] / 60.0, label=b_id, color=color, linewidth=1.6)
    ax4.set_title("(D) Discharge Duration Fade", fontweight='bold')
    ax4.set_xlabel("Cycle Number")
    ax4.set_ylabel("Duration (Minutes)")
    ax4.legend(loc='upper right', fontsize=9)

    plt.suptitle("BatteryGuardian AI — NASA Ames PCoE Benchmark Battery Aging Dashboard", fontsize=15, fontweight='bold', y=0.99)
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "degradation_dashboard.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[PLOT] Generated: {out_path}")

if __name__ == "__main__":
    os.makedirs(PLOTS_DIR, exist_ok=True)
    data = load_data()
    plot_capacity_vs_cycle(data)
    plot_soh_vs_cycle(data)
    plot_temperature_rise_vs_cycle(data)
    plot_discharge_duration_vs_cycle(data)
    plot_multipanel_dashboard(data)
    print("\n[SUCCESS] All data-integrity degradation plots generated successfully.")
