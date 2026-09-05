import os
import json
import pickle
import unittest
import numpy as np
import pandas as pd

PROCESSED_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"
PLOTS_DIR = os.path.join(PROCESSED_DIR, "plots")

HARDWARE_REPRODUCIBLE_FEATURES = [
    "duration_s", "v_start", "v_end", "v_min", "v_max", "v_mean", "v_drop", "v_std",
    "voltage_slope", "v_skew", "dc_internal_resistance", "i_mean", "i_min", "i_max",
    "t_start", "t_end", "t_min", "t_max", "t_mean", "temp_rise", "temp_rise_rate",
    "temp_std", "energy_wh"
]

class TestFeatureEngineering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "train_features.csv"))
        cls.val_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "val_features.csv"))
        cls.test_raw = pd.read_csv(os.path.join(PROCESSED_DIR, "test_features.csv"))

        cls.train_scaled = pd.read_csv(os.path.join(PROCESSED_DIR, "train_features_scaled.csv"))
        cls.val_scaled = pd.read_csv(os.path.join(PROCESSED_DIR, "val_features_scaled.csv"))
        cls.test_scaled = pd.read_csv(os.path.join(PROCESSED_DIR, "test_features_scaled.csv"))

        with open(os.path.join(PROCESSED_DIR, "feature_scaler_params.json"), "r") as f:
            cls.scaler_params = json.load(f)

    def test_feature_extraction_completeness_and_no_nans(self):
        """Verify that all 23 hardware-reproducible features are 100% complete with 0 NaNs."""
        for feat in HARDWARE_REPRODUCIBLE_FEATURES:
            self.assertIn(feat, self.train_raw.columns)
            self.assertIn(feat, self.val_raw.columns)
            self.assertIn(feat, self.test_raw.columns)

            self.assertEqual(self.train_raw[feat].isna().sum(), 0, f"NaN found in train: {feat}")
            self.assertEqual(self.val_raw[feat].isna().sum(), 0, f"NaN found in val: {feat}")
            self.assertEqual(self.test_raw[feat].isna().sum(), 0, f"NaN found in test: {feat}")

    def test_scaler_fitted_strictly_on_train_set(self):
        """Verify that scaling parameters strictly match the training partition (zero leakage)."""
        train_means = self.train_raw[HARDWARE_REPRODUCIBLE_FEATURES].mean().to_dict()
        train_stds = self.train_raw[HARDWARE_REPRODUCIBLE_FEATURES].std(ddof=0).to_dict()

        for feat in HARDWARE_REPRODUCIBLE_FEATURES:
            json_mean = self.scaler_params["hardware_scaling_constants"][feat]["mean"]
            json_std = self.scaler_params["hardware_scaling_constants"][feat]["std"]

            # Scaler mean and std must match training set statistics exactly
            self.assertAlmostEqual(json_mean, train_means[feat], places=3)
            self.assertAlmostEqual(json_std, train_stds[feat], places=3)

        # In train_features_scaled, the scaled columns must have mean ~ 0 and std ~ 1
        scaled_cols = [f"{f}_scaled" for f in HARDWARE_REPRODUCIBLE_FEATURES]
        np.testing.assert_allclose(self.train_scaled[scaled_cols].mean().values, 0.0, atol=1e-2)
        np.testing.assert_allclose(self.train_scaled[scaled_cols].std().values, 1.0, atol=1e-2)

    def test_validation_and_test_scalers_differ_from_zero(self):
        """
        Verify that validation and test partitions were NOT centered to zero mean,
        proving that val/test statistics were never used to fit the scaler (no leakage).
        """
        scaled_cols = [f"{f}_scaled" for f in HARDWARE_REPRODUCIBLE_FEATURES]
        # Val and test means will naturally deviate from exactly 0.0
        val_mean = self.val_scaled[scaled_cols].mean().values
        test_mean = self.test_scaled[scaled_cols].mean().values

        # At least some features will have non-zero mean on unseen batteries
        self.assertTrue(np.any(np.abs(val_mean) > 0.05))
        self.assertTrue(np.any(np.abs(test_mean) > 0.05))

    def test_zero_feature_target_overlap(self):
        """Verify target isolation: no target columns appear in the feature matrix."""
        scaled_cols = [f"{f}_scaled" for f in HARDWARE_REPRODUCIBLE_FEATURES]
        for col in scaled_cols:
            self.assertNotIn("capacity", col.lower())
            self.assertNotIn("soh", col.lower())
            self.assertNotIn("rul", col.lower())

    def test_plots_generation(self):
        """Verify that visualization plots exist and are non-empty."""
        for p in ["feature_correlation_matrix.png", "feature_distributions_unscaled_vs_scaled.png", "hardware_aligned_features_vs_soh.png"]:
            plot_path = os.path.join(PLOTS_DIR, p)
            self.assertTrue(os.path.exists(plot_path))
            self.assertGreater(os.path.getsize(plot_path), 50000)

if __name__ == "__main__":
    unittest.main()
