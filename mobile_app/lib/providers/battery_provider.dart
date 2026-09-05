import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import '../models/battery_telemetry.dart';
import '../models/ml_prediction.dart';
import '../services/ble_service.dart';
import '../services/database_service.dart';
import '../services/csv_export_service.dart';
import '../services/api_service.dart';

class BatteryProvider extends ChangeNotifier {
  final BleService _bleService = BleService();
  final DatabaseService _dbService = DatabaseService();
  final CsvExportService _csvService = CsvExportService();
  final ApiService _apiService = ApiService();

  BatteryTelemetry? _latestTelemetry;
  BatteryTelemetry? get latestTelemetry => _latestTelemetry;

  MLPrediction? _latestPrediction;
  MLPrediction? get latestPrediction => _latestPrediction;

  List<BatteryTelemetry> _recentHistory = [];
  List<BatteryTelemetry> get recentHistory => _recentHistory;

  BleConnectionStatus _connectionStatus = BleConnectionStatus.disconnected;
  BleConnectionStatus get connectionStatus => _connectionStatus;

  int _totalDatabaseRecords = 0;
  int get totalDatabaseRecords => _totalDatabaseRecords;

  bool _isExporting = false;
  bool get isExporting => _isExporting;

  StreamSubscription? _telemetrySub;
  StreamSubscription? _statusSub;
  int _sampleCounter = 0;

  BatteryProvider() {
    _initSubscriptions();
    _loadInitialHistory();
  }

  void _initSubscriptions() {
    // Listen to BLE Connection Status
    _statusSub = _bleService.statusStream.listen((status) {
      _connectionStatus = status;
      notifyListeners();
    });

    // Listen to incoming Telemetry
    _telemetrySub = _bleService.telemetryStream.listen((telemetry) {
      _latestTelemetry = telemetry;
      _totalDatabaseRecords++;
      
      // Maintain sliding history buffer for live charts (max 60 samples)
      _recentHistory.add(telemetry);
      if (_recentHistory.length > 60) {
        _recentHistory.removeAt(0);
      }

      // Periodically trigger ML inference (every 5 seconds / 5 samples)
      _sampleCounter++;
      if (_sampleCounter % 5 == 0 || _latestPrediction == null) {
        _fetchMlPrediction(telemetry);
      }

      notifyListeners();
    });
  }

  Future<void> _loadInitialHistory() async {
    _recentHistory = await _dbService.getRecentTelemetry(limit: 60);
    _recentHistory = _recentHistory.reversed.toList();
    _totalDatabaseRecords = await _dbService.getRecordCount();

    if (_recentHistory.isNotEmpty) {
      _latestTelemetry = _recentHistory.last;
      _fetchMlPrediction(_latestTelemetry!);
    }
    notifyListeners();
  }

  Future<void> _fetchMlPrediction(BatteryTelemetry t) async {
    final prediction = await _apiService.getHealthPrediction(t);
    _latestPrediction = prediction;
    notifyListeners();
  }

  // BLE Actions
  Future<void> startScan() => _bleService.startScan();
  Future<void> stopScan() => _bleService.stopScan();
  Future<bool> connect(BluetoothDevice device) => _bleService.connect(device);
  Future<void> disconnect() => _bleService.disconnect();

  // Export Actions
  Future<void> exportAndShareCsv() async {
    _isExporting = true;
    notifyListeners();
    try {
      await _csvService.shareCsvFile();
    } finally {
      _isExporting = false;
      notifyListeners();
    }
  }

  // Clear Database
  Future<void> clearHistory() async {
    await _dbService.clearTelemetry();
    _recentHistory.clear();
    _totalDatabaseRecords = 0;
    notifyListeners();
  }

  @override
  void dispose() {
    _telemetrySub?.cancel();
    _statusSub?.cancel();
    super.dispose();
  }
}
