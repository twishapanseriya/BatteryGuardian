import json
import math
import unittest

class TestBatteryGuardianFirmwareMath(unittest.TestCase):
    def setUp(self):
        # Hardware constants
        self.r_top = 33000.0
        self.r_bottom = 10000.0
        self.divider_ratio = self.r_bottom / (self.r_top + self.r_bottom) # 10/43 ≈ 0.232558
        self.adc_ref = 3.30
        self.adc_max = 4095
        
        # Calibration multipliers (defaults)
        self.cal_k1 = 1.0000
        self.cal_k2 = 1.0000
        self.cal_k3 = 1.0000
        
    def test_divider_ratio_precision(self):
        """Verify the exact divider ratio and max ESP32 pin voltage."""
        self.assertAlmostEqual(self.divider_ratio, 0.232558, places=5)
        
        # Max 3S pack voltage = 12.6V
        v_pack_max = 12.60
        v_pin_max = v_pack_max * self.divider_ratio
        
        # Must be comfortably below 3.3V
        self.assertLess(v_pin_max, 3.30)
        self.assertAlmostEqual(v_pin_max, 2.9302, places=3)
        
    def test_differential_cell_voltage_derivation(self):
        """Verify that differential cell calculations correctly reconstruct individual series cell voltages."""
        # Simulated true cell voltages
        true_c1 = 4.120
        true_c2 = 4.085
        true_c3 = 4.032
        
        # Physical node voltages relative to GND
        actual_node1 = true_c1                          # 4.120 V
        actual_node2 = true_c1 + true_c2                # 8.205 V
        actual_node3 = true_c1 + true_c2 + true_c3      # 12.237 V
        
        # Simulated ADC midpoint voltages measured by ESP32
        adc_pin1 = actual_node1 * self.divider_ratio
        adc_pin2 = actual_node2 * self.divider_ratio
        adc_pin3 = actual_node3 * self.divider_ratio
        
        # Firmware reconstruction with calibration multipliers
        reconstructed_node1 = (adc_pin1 / self.divider_ratio) * self.cal_k1
        reconstructed_node2 = (adc_pin2 / self.divider_ratio) * self.cal_k2
        reconstructed_node3 = (adc_pin3 / self.divider_ratio) * self.cal_k3
        
        calc_cell1 = reconstructed_node1
        calc_cell2 = reconstructed_node2 - reconstructed_node1
        calc_cell3 = reconstructed_node3 - reconstructed_node2
        calc_pack  = reconstructed_node3
        calc_imbalance = max(calc_cell1, calc_cell2, calc_cell3) - min(calc_cell1, calc_cell2, calc_cell3)
        
        self.assertAlmostEqual(calc_cell1, true_c1, places=3)
        self.assertAlmostEqual(calc_cell2, true_c2, places=3)
        self.assertAlmostEqual(calc_cell3, true_c3, places=3)
        self.assertAlmostEqual(calc_pack, 12.237, places=3)
        self.assertAlmostEqual(calc_imbalance, 0.088, places=3)
        
    def test_per_channel_calibration_correction(self):
        """Verify that individual resistor tolerance errors can be fully nullified via calibration multipliers."""
        # Simulate hardware with 1% resistor tolerance errors
        # Divider 1 reads 1% low, Divider 2 reads 0.5% high, Divider 3 reads 1% low
        tol_1 = 0.990
        tol_2 = 1.005
        tol_3 = 0.990
        
        true_node1 = 4.100
        true_node2 = 8.200
        true_node3 = 12.300
        
        # ADC measurements affected by hardware tolerance
        adc1 = true_node1 * self.divider_ratio * tol_1
        adc2 = true_node2 * self.divider_ratio * tol_2
        adc3 = true_node3 * self.divider_ratio * tol_3
        
        # Measured without calibration -> shows false imbalance
        raw_node1 = adc1 / self.divider_ratio
        raw_node2 = adc2 / self.divider_ratio
        raw_node3 = adc3 / self.divider_ratio
        
        uncal_c1 = raw_node1
        uncal_c2 = raw_node2 - raw_node1
        uncal_c3 = raw_node3 - raw_node2
        # True cells are perfectly balanced (4.100V each), but uncalibrated reads error:
        self.assertNotAlmostEqual(uncal_c2, 4.100, places=2)
        
        # Calibration multipliers measured against reference DMM
        k1 = 1.0 / tol_1 # 1.01010
        k2 = 1.0 / tol_2 # 0.99502
        k3 = 1.0 / tol_3 # 1.01010
        
        cal_node1 = (adc1 / self.divider_ratio) * k1
        cal_node2 = (adc2 / self.divider_ratio) * k2
        cal_node3 = (adc3 / self.divider_ratio) * k3
        
        cal_c1 = cal_node1
        cal_c2 = cal_node2 - cal_node1
        cal_c3 = cal_node3 - cal_node2
        
        # Calibrated output perfectly restores true cell voltages
        self.assertAlmostEqual(cal_c1, 4.100, places=3)
        self.assertAlmostEqual(cal_c2, 4.100, places=3)
        self.assertAlmostEqual(cal_c3, 4.100, places=3)
        
    def test_coulomb_counting_integration(self):
        """Verify that trapezoidal/rectangular Coulomb counting integrates accurately under 100-ohm load."""
        current_a = 0.120
        power_w = 12.0 * 0.120 # 1.44 W
        
        discharged_mah = 0.0
        energy_wh = 0.0
        dt_hours = 1.0 / 3600.0
        
        for _ in range(10 * 3600):
            discharged_mah += (current_a * 1000.0) * dt_hours
            energy_wh += power_w * dt_hours
            
        self.assertAlmostEqual(discharged_mah, 1200.0, places=1)
        self.assertAlmostEqual(energy_wh, 14.4, places=1)

    def test_telemetry_json_payload_schema(self):
        """Verify that generated JSON string adheres to the parser schema expected by Flutter and SQLite."""
        sample_json = (
            '{"ts":1725201600,"c1":4.120,"c2":4.085,"c3":4.032,"v_pack":12.237,'
            '"curr":0.122,"pwr":1.493,"t1":28.5,"t2":28.7,"t3":29.1,'
            '"imb":0.088,"mah":14.2,"state":"DISCHARGE","cycle":1}'
        )
        
        data = json.loads(sample_json)
        required_keys = [
            "ts", "c1", "c2", "c3", "v_pack",
            "curr", "pwr", "t1", "t2", "t3",
            "imb", "mah", "state", "cycle"
        ]
        for key in required_keys:
            self.assertIn(key, data)
            
        self.assertEqual(data["state"], "DISCHARGE")
        self.assertEqual(data["cycle"], 1)
        self.assertLess(len(sample_json.encode('utf-8')), 200, "BLE payload should be < 200 bytes for single-packet MTU")

if __name__ == "__main__":
    unittest.main()
