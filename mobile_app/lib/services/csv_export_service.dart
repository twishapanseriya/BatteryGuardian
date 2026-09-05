import 'dart:io';
import 'package:csv/csv.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../models/battery_telemetry.dart';
import 'database_service.dart';

class CsvExportService {
  final DatabaseService _dbService = DatabaseService();

  /// Headers formatted strictly for Python ML and data validation pipeline
  static const List<String> csvHeaders = [
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
  ];

  /// Convert a list of BatteryTelemetry records into standard CSV format
  String generateCsvString(List<BatteryTelemetry> records) {
    final List<List<dynamic>> rows = [];
    
    // Add header row
    rows.add(csvHeaders);

    // Add data rows
    for (final r in records) {
      rows.add([
        r.timestamp,
        r.batteryId,
        r.cell1Voltage.toStringAsFixed(3),
        r.cell2Voltage.toStringAsFixed(3),
        r.cell3Voltage.toStringAsFixed(3),
        r.packVoltage.toStringAsFixed(3),
        r.current.toStringAsFixed(3),
        r.power.toStringAsFixed(3),
        r.temperature1.toStringAsFixed(1),
        r.temperature2.toStringAsFixed(1),
        r.temperature3.toStringAsFixed(1),
        r.avgTemperature.toStringAsFixed(1),
        r.cellImbalance.toStringAsFixed(3),
        r.dischargedMah.toStringAsFixed(1),
        r.chargeDischargeState,
        r.cycleNumber
      ]);
    }

    return const ListToCsvConverter().convert(rows);
  }

  /// Export entire SQLite historical dataset to a local CSV file
  Future<File> exportDatabaseToCsvFile({String? customFileName}) async {
    final db = await _dbService.database;
    final List<Map<String, dynamic>> maps = await db.query(
      'telemetry',
      orderBy: 'timestamp ASC',
    );

    final records = maps.map((m) => BatteryTelemetry.fromMap(m)).toList();
    final csvContent = generateCsvString(records);

    final directory = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final fileName = customFileName ?? 'battery_guardian_telemetry_$timestamp.csv';
    final filePath = '${directory.path}/$fileName';

    final file = File(filePath);
    await file.writeAsString(csvContent);
    return file;
  }

  /// Trigger native OS Share dialog to send/export CSV
  Future<void> shareCsvFile() async {
    final file = await exportDatabaseToCsvFile();
    await Share.shareXFiles(
      [XFile(file.path)],
      text: 'BatteryGuardian AI Hardware Telemetry Dataset (CSV)',
    );
  }
}
