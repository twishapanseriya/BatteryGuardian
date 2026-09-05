import 'dart:async';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/battery_telemetry.dart';

class DatabaseService {
  static final DatabaseService _instance = DatabaseService._internal();
  static Database? _database;

  factory DatabaseService() => _instance;
  DatabaseService._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'battery_guardian.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
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
    ''');
    
    // Create index on timestamp and cycle_number for high performance queries
    await db.execute('CREATE INDEX idx_telemetry_ts ON telemetry(timestamp)');
    await db.execute('CREATE INDEX idx_telemetry_cycle ON telemetry(cycle_number)');
  }

  /// Insert raw telemetry record into SQLite
  Future<int> insertTelemetry(BatteryTelemetry telemetry) async {
    final db = await database;
    return await db.insert(
      'telemetry',
      telemetry.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Get the latest N telemetry frames
  Future<List<BatteryTelemetry>> getRecentTelemetry({int limit = 100}) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'telemetry',
      orderBy: 'timestamp DESC',
      limit: limit,
    );
    return maps.map((m) => BatteryTelemetry.fromMap(m)).toList();
  }

  /// Get telemetry within a timestamp range
  Future<List<BatteryTelemetry>> getTelemetryRange(int startTs, int endTs) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'telemetry',
      where: 'timestamp >= ? AND timestamp <= ?',
      whereArgs: [startTs, endTs],
      orderBy: 'timestamp ASC',
    );
    return maps.map((m) => BatteryTelemetry.fromMap(m)).toList();
  }

  /// Get all telemetry for a given cycle
  Future<List<BatteryTelemetry>> getCycleTelemetry(int cycle) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'telemetry',
      where: 'cycle_number = ?',
      whereArgs: [cycle],
      orderBy: 'timestamp ASC',
    );
    return maps.map((m) => BatteryTelemetry.fromMap(m)).toList();
  }

  /// Get total count of recorded telemetry frames
  Future<int> getRecordCount() async {
    final db = await database;
    final count = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM telemetry'),
    );
    return count ?? 0;
  }

  /// Clear all stored telemetry records
  Future<int> clearTelemetry() async {
    final db = await database;
    return await db.delete('telemetry');
  }
}
