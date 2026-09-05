import os
import json
import unittest
import pandas as pd

PROCESSED_DIR = "/home/Twisha/Startup/data/public/processed/nasa_pcoe"
PLOTS_DIR = os.path.join(PROCESSED_DIR, "plots")

class TestMilestone9Validation(unittest.TestCase):
    def test_split_files_exist_and_disjoint(self):
        """Verify that train, validation, and test datasets exist, have no overlap, and sum to 636."""
        train_path = os.path.join(PROCESSED_DIR, "train_cycles.csv")
        val_path = os.path.join(PROCESSED_DIR, "val_cycles.csv")
        test_path = os.path.join(PROCESSED_DIR, "test_cycles.csv")

        self.assertTrue(os.path.exists(train_path))
        self.assertTrue(os.path.exists(val_path))
        self.assertTrue(os.path.exists(test_path))

        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)

        train_cells = set(train_df['battery_id'].unique())
        val_cells = set(val_df['battery_id'].unique())
        test_cells = set(test_df['battery_id'].unique())

        # Exact expected assignments
        self.assertEqual(train_cells, {'B0005', 'B0006'})
        self.assertEqual(val_cells, {'B0007'})
        self.assertEqual(test_cells, {'B0018'})

        # Zero battery overlap check
        self.assertEqual(len(train_cells.intersection(val_cells)), 0, "Train and Val must be disjoint")
        self.assertEqual(len(train_cells.intersection(test_cells)), 0, "Train and Test must be disjoint")
        self.assertEqual(len(val_cells.intersection(test_cells)), 0, "Val and Test must be disjoint")

        # Row counts
        self.assertEqual(len(train_df), 336)
        self.assertEqual(len(val_df), 168)
        self.assertEqual(len(test_df), 132)
        self.assertEqual(len(train_df) + len(val_df) + len(test_df), 636)

    def test_validation_report_json(self):
        """Verify the machine-readable dataset validation report."""
        report_path = os.path.join(PROCESSED_DIR, "dataset_validation_report.json")
        self.assertTrue(os.path.exists(report_path))

        with open(report_path, "r") as f:
            rep = json.load(f)

        self.assertEqual(rep["milestone"], 9)
        self.assertEqual(rep["dataset_dimensions"]["total_rows"], 636)
        self.assertTrue(rep["battery_splits"]["zero_battery_overlap_verified"])
        self.assertTrue(rep["feature_target_integrity_validation"]["zero_feature_target_overlap"])

    def test_validation_plots_generated(self):
        """Verify that split and segmentation validation plots were created."""
        plot1 = os.path.join(PLOTS_DIR, "train_val_test_split_overlap_check.png")
        plot2 = os.path.join(PLOTS_DIR, "segmentation_counts_check.png")

        self.assertTrue(os.path.exists(plot1))
        self.assertTrue(os.path.exists(plot2))
        self.assertGreater(os.path.getsize(plot1), 100000)
        self.assertGreater(os.path.getsize(plot2), 100000)

if __name__ == "__main__":
    unittest.main()
