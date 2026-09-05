import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import '../models/battery_telemetry.dart';
import 'database_service.dart';

enum BleConnectionStatus {
  disconnected,
  scanning,
  connecting,
  connected,
  discoveringServices,
  ready
}

class BleService {
  static final BleService _instance = BleService._internal();
  factory BleService() => _instance;
  BleService._internal();

  // Confirmed BatteryGuardian BLE UUIDs
  static final Guid serviceUuid = Guid("4fafc201-1fb5-459e-8fcc-c5c9c331914b");
  static final Guid telemetryCharUuid = Guid("beb5483e-36e1-4688-b7f5-ea07361b26a8");

  final DatabaseService _dbService = DatabaseService();

  BluetoothDevice? _connectedDevice;
  BluetoothCharacteristic? _telemetryCharacteristic;
  StreamSubscription? _valueSubscription;
  StreamSubscription? _connectionSubscription;

  final _statusController = StreamController<BleConnectionStatus>.broadcast();
  Stream<BleConnectionStatus> get statusStream => _statusController.stream;
  BleConnectionStatus _currentStatus = BleConnectionStatus.disconnected;
  BleConnectionStatus get currentStatus => _currentStatus;

  final _telemetryController = StreamController<BatteryTelemetry>.broadcast();
  Stream<BatteryTelemetry> get telemetryStream => _telemetryController.stream;

  List<ScanResult> _scanResults = [];
  List<ScanResult> get scanResults => _scanResults;

  void _setStatus(BleConnectionStatus status) {
    _currentStatus = status;
    _statusController.add(status);
  }

  /// Start scanning for BatteryGuardian ESP32
  Future<void> startScan({Duration timeout = const Duration(seconds: 15)}) async {
    if (_currentStatus == BleConnectionStatus.connecting || 
        _currentStatus == BleConnectionStatus.connected || 
        _currentStatus == BleConnectionStatus.ready) {
      return;
    }

    _setStatus(BleConnectionStatus.scanning);
    _scanResults.clear();

    FlutterBluePlus.scanResults.listen((results) {
      _scanResults = results;
    });

    try {
      await FlutterBluePlus.startScan(
        withServices: [serviceUuid],
        timeout: timeout,
      );
    } catch (e) {
      debugPrint('[BLE] Scan error: $e');
      _setStatus(BleConnectionStatus.disconnected);
    }
  }

  /// Stop active scan
  Future<void> stopScan() async {
    await FlutterBluePlus.stopScan();
    if (_currentStatus == BleConnectionStatus.scanning) {
      _setStatus(BleConnectionStatus.disconnected);
    }
  }

  /// Connect to specific BLE Device
  Future<bool> connect(BluetoothDevice device) async {
    _setStatus(BleConnectionStatus.connecting);
    await stopScan();

    try {
      await device.connect(
        timeout: const Duration(seconds: 15),
        autoConnect: false,
      );
      _connectedDevice = device;
      _setStatus(BleConnectionStatus.connected);

      // Listen for disconnection events
      _connectionSubscription?.cancel();
      _connectionSubscription = device.connectionState.listen((state) {
        if (state == BluetoothConnectionState.disconnected) {
          debugPrint('[BLE] Device disconnected.');
          _cleanUpConnection();
        }
      });

      // Request MTU 256 for atomic JSON packets (>150 bytes)
      try {
        await device.requestMtu(256);
        debugPrint('[BLE] MTU 256 requested successfully.');
      } catch (mtuErr) {
        debugPrint('[BLE] MTU request note: $mtuErr');
      }

      // Discover Services
      _setStatus(BleConnectionStatus.discoveringServices);
      final services = await device.discoverServices();

      for (final service in services) {
        if (service.uuid == serviceUuid) {
          for (final characteristic in service.characteristics) {
            if (characteristic.uuid == telemetryCharUuid) {
              _telemetryCharacteristic = characteristic;
              await _subscribeToTelemetry(characteristic);
              _setStatus(BleConnectionStatus.ready);
              return true;
            }
          }
        }
      }

      debugPrint('[BLE] Telemetry characteristic not found in services.');
      return false;
    } catch (e) {
      debugPrint('[BLE] Connection error: $e');
      _cleanUpConnection();
      return false;
    }
  }

  /// Subscribe to GATT Notify events
  Future<void> _subscribeToTelemetry(BluetoothCharacteristic characteristic) async {
    await characteristic.setNotifyValue(true);
    _valueSubscription?.cancel();

    _valueSubscription = characteristic.lastValueStream.listen((value) async {
      if (value.isEmpty) return;

      try {
        final jsonString = utf8.decode(value);
        final telemetry = BatteryTelemetry.fromEsp32Json(jsonString);

        // 1. Emit to UI Stream
        _telemetryController.add(telemetry);

        // 2. Automatically record raw sample in SQLite
        await _dbService.insertTelemetry(telemetry);
      } catch (e) {
        debugPrint('[BLE] Telemetry decode error: $e | Raw: ${utf8.decode(value, allowMalformed: true)}');
      }
    });
  }

  /// Disconnect and release resources
  Future<void> disconnect() async {
    if (_connectedDevice != null) {
      await _connectedDevice!.disconnect();
    }
    _cleanUpConnection();
  }

  void _cleanUpConnection() {
    _valueSubscription?.cancel();
    _valueSubscription = null;
    _connectionSubscription?.cancel();
    _connectionSubscription = null;
    _telemetryCharacteristic = null;
    _connectedDevice = null;
    _setStatus(BleConnectionStatus.disconnected);
  }
}
