import os
import sys
import csv
import json
import sqlite3
import unittest

# Add root directory to sys.path for tool importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.serial_logger import parse_telemetry_line, CSV_HEADERS

class TestBatteryGuardianStorageAndExport(unittest.TestCase):
    def setUp(self):
        self.db_path = "/tmp/test_battery_guardian.db"
        self.csv_path = "/tmp/test_telemetry_export.csv"
        
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
            
        # Initialize SQLite database matching Flutter DatabaseService schema
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                battery_id TEXT NOT NULL,
                cell1_voltage REAL NOT NULL,
                cell2_voltage REAL NOT NULL,
                cell3_voltage REAL NOT NULL,
                pack_voltage REAL NOT NULL,
                current REAL NOT NULL,
                power REAL NOT NULL,
                temperature1 REAL NOT NULL,
                temperature2 REAL NOT NULL,
                temperature3 REAL NOT NULL,
                avg_temperature REAL NOT NULL,
                cell_imbalance REAL NOT NULL,
                discharged_mah REAL NOT NULL,
                charge_discharge_state TEXT NOT NULL,
                cycle_number INTEGER NOT NULL
            )
        ''')
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_ingest_esp32_telemetry_packets(self):
        """Verify that raw JSON packets emitted by ESP32 parse and insert into SQLite with 100% integrity."""
        esp32_packets = [
            '{"ts":1725201600,"c1":4.120,"c2":4.085,"c3":4.032,"v_pack":12.237,"curr":0.122,"pwr":1.493,"t1":28.5,"t2":28.7,"t3":29.1,"imb":0.088,"mah":0.0,"state":"DISCHARGE","cycle":1}',
            '{"ts":1725201601,"c1":4.119,"c2":4.084,"c3":4.031,"v_pack":12.234,"curr":0.122,"pwr":1.493,"t1":28.5,"t2":28.7,"t3":29.1,"imb":0.088,"mah":0.034,"state":"DISCHARGE","cycle":1}',
            '{"ts":1725201602,"c1":4.118,"c2":4.083,"c3":4.030,"v_pack":12.231,"curr":0.122,"pwr":1.492,"t1":28.6,"t2":28.8,"t3":29.2,"imb":0.088,"mah":0.068,"state":"DISCHARGE","cycle":1}',
        ]
        
        for p in esp32_packets:
            d = json.loads(p)
            avg_temp = (d["t1"] + d["t2"] + d["t3"]) / 3.0
            
            self.cursor.execute('''
                INSERT INTO telemetry (
                    timestamp, battery_id, cell1_voltage, cell2_voltage, cell3_voltage,
                    pack_voltage, current, power, temperature1, temperature2, temperature3,
                    avg_temperature, cell_imbalance, discharged_mah, charge_discharge_state, cycle_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d["ts"], "BG-3S-001", d["c1"], d["c2"], d["c3"],
                d["v_pack"], d["curr"], d["pwr"], d["t1"], d["t2"], d["t3"],
                avg_temp, d["imb"], d["mah"], d["state"], d["cycle"]
            ))
            
        self.conn.commit()
        
        # Verify row count
        self.cursor.execute("SELECT COUNT(*) FROM telemetry")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 3)
        
        # Verify data fields
        self.cursor.execute("SELECT cell1_voltage, pack_voltage, charge_discharge_state FROM telemetry WHERE timestamp = 1725201600")
        row = self.cursor.fetchone()
        self.assertAlmostEqual(row[0], 4.120, places=3)
        self.assertAlmostEqual(row[1], 12.237, places=3)
        self.assertEqual(row[2], "DISCHARGE")

    def test_csv_export_format_and_compatibility(self):
        """Verify that exported CSV strictly matches the schema required by Python ML pipelines."""
        for i in range(10):
            ts = 1725201600 + i
            c1 = 4.120 - (i * 0.001)
            c2 = 4.085 - (i * 0.001)
            c3 = 4.032 - (i * 0.001)
            v_pack = c1 + c2 + c3
            curr = 0.122
            pwr = v_pack * curr
            t1, t2, t3 = 28.5 + (i * 0.1), 28.7 + (i * 0.1), 29.1 + (i * 0.1)
            avg_temp = (t1 + t2 + t3) / 3.0
            imb = max(c1, c2, c3) - min(c1, c2, c3)
            mah = (curr * 1000.0) * (i / 3600.0)
            
            self.cursor.execute('''
                INSERT INTO telemetry (
                    timestamp, battery_id, cell1_voltage, cell2_voltage, cell3_voltage,
                    pack_voltage, current, power, temperature1, temperature2, temperature3,
                    avg_temperature, cell_imbalance, discharged_mah, charge_discharge_state, cycle_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "BG-3S-001", c1, c2, c3, v_pack, curr, pwr, t1, t2, t3, avg_temp, imb, mah, "DISCHARGE", 1))
        self.conn.commit()
        
        # Export to CSV
        self.cursor.execute("SELECT " + ", ".join(CSV_HEADERS) + " FROM telemetry ORDER BY timestamp ASC")
        rows = self.cursor.fetchall()
        
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
            writer.writerows(rows)
            
        # Re-open and validate CSV
        with open(self.csv_path, 'r') as f:
            reader = csv.DictReader(f)
            read_rows = list(reader)
            
        self.assertEqual(len(read_rows), 10)
        self.assertEqual(read_rows[0]['battery_id'], 'BG-3S-001')
        self.assertAlmostEqual(float(read_rows[0]['cell1_voltage']), 4.120, places=3)
        self.assertAlmostEqual(float(read_rows[9]['cell1_voltage']), 4.111, places=3)
        self.assertEqual(read_rows[0]['charge_discharge_state'], 'DISCHARGE')
        self.assertEqual(int(read_rows[0]['cycle_number']), 1)

    def test_pc_serial_logger_parser(self):
        """Verify that PC Serial Logger parses raw ESP32 serial lines cleanly without corruption."""
        raw_serial_line = '[TELEMETRY] {"ts":1725201600,"c1":4.120,"c2":4.085,"c3":4.032,"v_pack":12.237,"curr":0.122,"pwr":1.493,"t1":28.5,"t2":28.7,"t3":29.1,"imb":0.088,"mah":14.2,"state":"DISCHARGE","cycle":1}\n'
        parsed = parse_telemetry_line(raw_serial_line)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["timestamp"], 1725201600)
        self.assertAlmostEqual(parsed["cell1_voltage"], 4.120, places=3)
        self.assertAlmostEqual(parsed["pack_voltage"], 12.237, places=3)
        self.assertAlmostEqual(parsed["current"], 0.122, places=3)
        self.assertAlmostEqual(parsed["power"], 1.493, places=3)
        self.assertAlmostEqual(parsed["avg_temperature"], 28.766, places=2)
        self.assertEqual(parsed["charge_discharge_state"], "DISCHARGE")
        self.assertEqual(parsed["cycle_number"], 1)

        # Non-telemetry noise / debug lines should be safely ignored (return None)
        noise_line = ">> V_Pack: 12.24V | C1: 4.120V | C2: 4.085V\n"
        self.assertIsNone(parse_telemetry_line(noise_line))

if __name__ == "__main__":
    unittest.main()
