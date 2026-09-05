#!/usr/bin/env python3
"""
BatteryGuardian AI - PC Serial Logger
Captures real-time 1 Hz telemetry from ESP32 over USB Serial, validates data integrity,
and records frames into SQLite database and streaming CSV in data/hardware/raw/.
"""

import os
import sys
import time
import json
import csv
import sqlite3
import argparse
import glob

CSV_HEADERS = [
    'timestamp',
    'battery_id',
    'cell1_voltage',
    'cell2_voltage',
    'cell3_voltage',
    'pack_voltage',
    'current',
    'power',
    'temperature1',
    'temperature2',
    'temperature3',
    'avg_temperature',
    'cell_imbalance',
    'discharged_mah',
    'charge_discharge_state',
    'cycle_number'
]

def auto_detect_port():
    """Detect available serial ports on Linux/Mac/Windows."""
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/cu.usbserial*')
    if ports:
        return ports[0]
    return '/dev/ttyUSB0'

def init_sqlite(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
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
    cur.execute('CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(timestamp)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_telemetry_cycle ON telemetry(cycle_number)')
    conn.commit()
    return conn

def parse_telemetry_line(line_str, battery_id="BG-3S-001"):
    """Parse ESP32 [TELEMETRY] JSON string into normalized data dictionary."""
    line = line_str.strip()
    if not line:
        return None
    
    # Extract JSON substring if prefixed with [TELEMETRY]
    if "[TELEMETRY]" in line:
        json_part = line.split("[TELEMETRY]", 1)[1].strip()
    elif line.startswith("{") and line.endswith("}"):
        json_part = line
    else:
        return None
        
    try:
        data = json.loads(json_part)
    except json.JSONDecodeError:
        return None

    # Verify required keys
    required_keys = ["c1", "c2", "c3", "v_pack", "curr"]
    if not all(k in data for k in required_keys):
        return None

    ts = int(data.get("ts", int(time.time())))
    c1 = float(data.get("c1", 0.0))
    c2 = float(data.get("c2", 0.0))
    c3 = float(data.get("c3", 0.0))
    v_pack = float(data.get("v_pack", c1 + c2 + c3))
    curr = float(data.get("curr", 0.0))
    pwr = float(data.get("pwr", v_pack * curr))
    t1 = float(data.get("t1", 25.0))
    t2 = float(data.get("t2", 25.0))
    t3 = float(data.get("t3", 25.0))
    avg_t = (t1 + t2 + t3) / 3.0
    imb = float(data.get("imb", max(c1, c2, c3) - min(c1, c2, c3)))
    mah = float(data.get("mah", 0.0))
    state = str(data.get("state", "IDLE"))
    cycle = int(data.get("cycle", 1))

    return {
        "timestamp": ts,
        "battery_id": battery_id,
        "cell1_voltage": c1,
        "cell2_voltage": c2,
        "cell3_voltage": c3,
        "pack_voltage": v_pack,
        "current": curr,
        "power": pwr,
        "temperature1": t1,
        "temperature2": t2,
        "temperature3": t3,
        "avg_temperature": avg_t,
        "cell_imbalance": imb,
        "discharged_mah": mah,
        "charge_discharge_state": state,
        "cycle_number": cycle
    }

def run_serial_logger(port, baud=115200, output_dir="data/hardware/raw", battery_id="BG-3S-001"):
    try:
        import serial
    except ImportError:
        print("[ERROR] pyserial is not installed. Run: pip install pyserial")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    session_id = int(time.time())
    db_path = os.path.join(output_dir, "hardware_telemetry.db")
    csv_path = os.path.join(output_dir, f"telemetry_session_{session_id}.csv")

    conn = init_sqlite(db_path)
    cur = conn.cursor()

    # Open CSV in append mode with explicit flush
    csv_file = open(csv_path, 'w', newline='')
    writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
    writer.writeheader()
    csv_file.flush()

    print(f"[LOGGER] Connecting to ESP32 on {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=2.0)
    except Exception as e:
        print(f"[ERROR] Could not open port {port}: {e}")
        return

    print(f"[LOGGER] Connected. Logging live telemetry...")
    print(f"  -> SQLite: {db_path}")
    print(f"  -> CSV   : {csv_path}")
    print("Press Ctrl+C to stop logging.\n")

    frame_count = 0
    try:
        while True:
            raw_line = ser.readline().decode('utf-8', errors='replace')
            if not raw_line:
                continue

            record = parse_telemetry_line(raw_line, battery_id=battery_id)
            if record is not None:
                # 1. Insert to SQLite
                cur.execute('''
                    INSERT INTO telemetry (
                        timestamp, battery_id, cell1_voltage, cell2_voltage, cell3_voltage,
                        pack_voltage, current, power, temperature1, temperature2, temperature3,
                        avg_temperature, cell_imbalance, discharged_mah, charge_discharge_state, cycle_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record["timestamp"], record["battery_id"], record["cell1_voltage"], record["cell2_voltage"],
                    record["cell3_voltage"], record["pack_voltage"], record["current"], record["power"],
                    record["temperature1"], record["temperature2"], record["temperature3"], record["avg_temperature"],
                    record["cell_imbalance"], record["discharged_mah"], record["charge_discharge_state"], record["cycle_number"]
                ))
                conn.commit()

                # 2. Append to CSV & Flush
                writer.writerow(record)
                csv_file.flush()

                frame_count += 1
                print(f"\r[FRAME #{frame_count:05d}] V_Pack: {record['pack_voltage']:.2f}V | C1: {record['cell1_voltage']:.3f}V | C2: {record['cell2_voltage']:.3f}V | C3: {record['cell3_voltage']:.3f}V | I: {record['current']:.3f}A | State: {record['charge_discharge_state']}", end='', flush=True)

    except KeyboardInterrupt:
        print(f"\n[LOGGER] Logging stopped by user. Total frames captured: {frame_count}")
    finally:
        ser.close()
        csv_file.close()
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BatteryGuardian AI - Serial Telemetry Logger")
    parser.add_argument("--port", type=str, default=auto_detect_port(), help="Serial port (e.g. /dev/ttyUSB0 or COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--outdir", type=str, default="data/hardware/raw", help="Output directory")
    parser.add_argument("--battery-id", type=str, default="BG-3S-001", help="Battery Identifier")
    args = parser.parse_args()

    run_serial_logger(args.port, args.baud, args.outdir, args.battery_id)
