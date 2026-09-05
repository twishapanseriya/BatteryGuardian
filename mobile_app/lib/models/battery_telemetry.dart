import 'dart:convert';

/// Data model representing a single timestamped telemetry frame from BatteryGuardian ESP32.
class BatteryTelemetry {
  final int? id;
  final int timestamp; // Epoch timestamp (seconds)
  final String batteryId;
  final double cell1Voltage; // V
  final double cell2Voltage; // V
  final double cell3Voltage; // V
  final double packVoltage;  // V
  final double current;      // A
  final double power;        // W
  final double temperature1; // °C
  final double temperature2; // °C
  final double temperature3; // °C
  final double avgTemperature; // °C
  final double cellImbalance; // V (max - min)
  final double dischargedMah; // mAh
  final String chargeDischargeState; // "IDLE", "DISCHARGE", "CHARGE"
  final int cycleNumber;

  BatteryTelemetry({
    this.id,
    required this.timestamp,
    this.batteryId = 'BG-3S-001',
    required this.cell1Voltage,
    required this.cell2Voltage,
    required this.cell3Voltage,
    required this.packVoltage,
    required this.current,
    required this.power,
    required this.temperature1,
    required this.temperature2,
    required this.temperature3,
    required this.avgTemperature,
    required this.cellImbalance,
    required this.dischargedMah,
    required this.chargeDischargeState,
    required this.cycleNumber,
  });

  /// Factory constructor to parse raw JSON emitted by ESP32 over BLE
  factory BatteryTelemetry.fromEsp32Json(String jsonStr, {String batteryId = 'BG-3S-001'}) {
    final Map<String, dynamic> data = json.decode(jsonStr);
    
    final c1 = (data['c1'] as num?)?.toDouble() ?? 0.0;
    final c2 = (data['c2'] as num?)?.toDouble() ?? 0.0;
    final c3 = (data['c3'] as num?)?.toDouble() ?? 0.0;
    
    final t1 = (data['t1'] as num?)?.toDouble() ?? 25.0;
    final t2 = (data['t2'] as num?)?.toDouble() ?? 25.0;
    final t3 = (data['t3'] as num?)?.toDouble() ?? 25.0;
    
    final avgT = (t1 + t2 + t3) / 3.0;

    return BatteryTelemetry(
      timestamp: (data['ts'] as num?)?.toInt() ?? (DateTime.now().millisecondsSinceEpoch ~/ 1000),
      batteryId: batteryId,
      cell1Voltage: c1,
      cell2Voltage: c2,
      cell3Voltage: c3,
      packVoltage: (data['v_pack'] as num?)?.toDouble() ?? (c1 + c2 + c3),
      current: (data['curr'] as num?)?.toDouble() ?? 0.0,
      power: (data['pwr'] as num?)?.toDouble() ?? 0.0,
      temperature1: t1,
      temperature2: t2,
      temperature3: t3,
      avgTemperature: avgT,
      cellImbalance: (data['imb'] as num?)?.toDouble() ?? _calcImbalance(c1, c2, c3),
      dischargedMah: (data['mah'] as num?)?.toDouble() ?? 0.0,
      chargeDischargeState: data['state'] as String? ?? 'IDLE',
      cycleNumber: (data['cycle'] as num?)?.toInt() ?? 1,
    );
  }

  static double _calcImbalance(double c1, double c2, double c3) {
    final maxV = [c1, c2, c3].reduce((curr, next) => curr > next ? curr : next);
    final minV = [c1, c2, c3].reduce((curr, next) => curr < next ? curr : next);
    return maxV - minV;
  }

  /// Identifies the weakest (lowest voltage) cell (1, 2, or 3)
  int get weakestCellIndex {
    if (cell1Voltage <= cell2Voltage && cell1Voltage <= cell3Voltage) return 1;
    if (cell2Voltage <= cell1Voltage && cell2Voltage <= cell3Voltage) return 2;
    return 3;
  }

  /// Convert to SQLite Map
  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'timestamp': timestamp,
      'battery_id': batteryId,
      'cell1_voltage': cell1Voltage,
      'cell2_voltage': cell2Voltage,
      'cell3_voltage': cell3Voltage,
      'pack_voltage': packVoltage,
      'current': current,
      'power': power,
      'temperature1': temperature1,
      'temperature2': temperature2,
      'temperature3': temperature3,
      'avg_temperature': avgTemperature,
      'cell_imbalance': cellImbalance,
      'discharged_mah': dischargedMah,
      'charge_discharge_state': chargeDischargeState,
      'cycle_number': cycleNumber,
    };
  }

  /// Factory constructor from SQLite Map
  factory BatteryTelemetry.fromMap(Map<String, dynamic> map) {
    return BatteryTelemetry(
      id: map['id'] as int?,
      timestamp: map['timestamp'] as int,
      batteryId: map['battery_id'] as String,
      cell1Voltage: (map['cell1_voltage'] as num).toDouble(),
      cell2Voltage: (map['cell2_voltage'] as num).toDouble(),
      cell3Voltage: (map['cell3_voltage'] as num).toDouble(),
      packVoltage: (map['pack_voltage'] as num).toDouble(),
      current: (map['current'] as num).toDouble(),
      power: (map['power'] as num).toDouble(),
      temperature1: (map['temperature1'] as num).toDouble(),
      temperature2: (map['temperature2'] as num).toDouble(),
      temperature3: (map['temperature3'] as num).toDouble(),
      avgTemperature: (map['avg_temperature'] as num).toDouble(),
      cellImbalance: (map['cell_imbalance'] as num).toDouble(),
      dischargedMah: (map['discharged_mah'] as num).toDouble(),
      chargeDischargeState: map['charge_discharge_state'] as String,
      cycleNumber: map['cycle_number'] as int,
    );
  }

  /// Convert to JSON string
  Map<String, dynamic> toJson() => toMap();
}
