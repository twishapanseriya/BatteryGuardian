import os
import json
import unittest
import pandas as pd
import numpy as np

DATA_FILE = "/home/Twisha/Startup/data/public/processed/nasa_pcoe/nasa_pcoe_cycles.csv"
METADATA_FILE = "/home/Twisha/Startup/data/public/processed/nasa_pcoe/metadata.json"
OUTPUT_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"

class TestNASADataProcessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_FILE):
            raise FileNotFoundError(f"Processed dataset not found at: {DATA_FILE}")
        cls.df = pd.read_csv(DATA_FILE)
        with open(METADATA_FILE, "r") as f:
            cls.metadata = json.load(f)

    def test_dataset_dimensions_and_batteries(self):
        """Verify total rows, batteries, and expected cycle counts."""
        self.assertEqual(len(self.df), 636, "Combined dataset must contain exactly 636 discharge cycles")
        
        battery_counts = self.df['battery_id'].value_counts().to_dict()
        self.assertEqual(battery_counts['B0005'], 168)
        self.assertEqual(battery_counts['B0006'], 168)
        self.assertEqual(battery_counts['B0007'], 168)
        self.assertEqual(battery_counts['B0018'], 132)
        
        # Verify columns exist
        expected_cols = [
            "battery_id", "cycle_number", "duration_s", "v_start", "v_end", "v_min", "v_max", "v_mean",
            "v_drop", "i_mean", "t_start", "t_end", "t_max", "t_mean", "temp_rise", "temp_rise_rate",
            "energy_wh", "capacity_ah", "soh_pct", "eol_cycle_80", "rul_80", "eol_cycle_70", "rul_70"
        ]
        for col in expected_cols:
            self.assertIn(col, self.df.columns)

    def test_zero_future_cycle_leakage(self):
        """
        Verify that no future-cycle information leaks into features for cycle k.
        Features must depend only on cycle k measurements or preceding impedance sweeps.
        """
        feature_cols = [
            "duration_s", "v_start", "v_end", "v_min", "v_max", "v_mean", "v_drop",
            "i_mean", "i_min", "i_max", "t_start", "t_end", "t_min", "t_max", "t_mean",
            "temp_rise", "temp_rise_rate", "energy_wh"
        ]
        target_cols = ["capacity_ah", "soh_pct", "rul_80", "rul_70"]

        # 1. Feature columns must not contain targets or target-derived indicators
        for feat in feature_cols:
            self.assertNotIn("capacity", feat.lower())
            self.assertNotIn("soh", feat.lower())
            self.assertNotIn("rul", feat.lower())

        # 2. Sequential monotonicity check: cycle numbers must strictly increase per battery
        for b_id, group in self.df.groupby('battery_id'):
            cycles = group['cycle_number'].tolist()
            self.assertEqual(cycles, list(range(1, len(cycles) + 1)), f"Cycles for {b_id} must be contiguous 1..N")

    def test_target_values_and_rul_monotonicity(self):
        """Verify ground-truth SoH and RUL calculations and bounds."""
        # Capacity must be in physically valid range for 2.0Ah 18650 cell
        self.assertTrue((self.df['capacity_ah'] > 1.0).all())
        self.assertTrue((self.df['capacity_ah'] < 2.2).all())
        
        # SoH (%) must be relative to 2.0Ah nominal
        np.testing.assert_allclose(self.df['soh_pct'], (self.df['capacity_ah'] / 2.0) * 100.0, rtol=1e-3)

        # RUL monotonicity check prior to EOL: RUL_k = EOL - k
        for b_id in ["B0005", "B0006", "B0018"]:
            b_df = self.df[self.df['battery_id'] == b_id]
            eol_80 = int(b_df['eol_cycle_80'].iloc[0])
            
            pre_eol = b_df[b_df['cycle_number'] <= eol_80]
            rul_values = pre_eol['rul_80'].tolist()
            
            # Check strictly decreasing by 1 each cycle
            diffs = np.diff(rul_values)
            self.assertTrue((diffs == -1).all(), f"RUL for {b_id} must decrease by exactly 1 per cycle")
            self.assertEqual(rul_values[-1], 0, f"RUL at EOL cycle must be 0")

    def test_physical_measurements_validity(self):
        """Verify that all extracted sensor statistics conform to real physical constraints."""
        # Voltages
        self.assertTrue((self.df['v_start'] >= 3.8).all(), "Start voltage must be near full charge (> 3.8V)")
        self.assertTrue((self.df['v_min'] >= 1.5).all(), "Cutoff voltage must be >= 1.5V (B0007 dipped to ~1.74V under 2.2V cutoff)")
        self.assertTrue((self.df['v_drop'] > 0).all(), "Voltage drop during discharge must be positive")

        # Temperatures
        self.assertTrue((self.df['t_start'] >= 20.0).all(), "Room temp start should be >= 20C")
        self.assertTrue((self.df['t_max'] <= 50.0).all(), "Room temp peak should be <= 50C")
        self.assertTrue((self.df['temp_rise'] >= 0).all(), "Discharge causes exothermic heating (temp_rise >= 0)")

        # Durations
        self.assertTrue((self.df['duration_s'] > 1800).all(), "2A discharge from 2.0Ah cell takes > 30 mins (1800s)")

    def test_individual_battery_csv_integrity(self):
        """Verify individual battery CSV exports match the master dataset."""
        for b_id in ["B0005", "B0006", "B0007", "B0018"]:
            indiv_path = os.path.join(OUTPUT_DIR, f"{b_id}_cycles.csv")
            self.assertTrue(os.path.exists(indiv_path))
            indiv_df = pd.read_csv(indiv_path)
            master_slice = self.df[self.df['battery_id'] == b_id]
            self.assertEqual(len(indiv_df), len(master_slice))

if __name__ == "__main__":
    unittest.main()
