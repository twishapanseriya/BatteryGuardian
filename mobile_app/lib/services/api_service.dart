import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/battery_telemetry.dart';
import '../models/ml_prediction.dart';

class ApiService {
  // Configurable backend URL (Default: local development endpoint)
  String baseUrl;

  ApiService({this.baseUrl = 'http://127.0.0.1:8000'});

  /// Send real-time telemetry feature vector to FastAPI for SoH/RUL inference
  Future<MLPrediction> getHealthPrediction(BatteryTelemetry t) async {
    final url = Uri.parse('$baseUrl/predict');
    
    final body = json.encode({
      'cell1_voltage': t.cell1Voltage,
      'cell2_voltage': t.cell2Voltage,
      'cell3_voltage': t.cell3Voltage,
      'pack_voltage': t.packVoltage,
      'current': t.current,
      'temperature': t.avgTemperature,
      'discharged_mah': t.dischargedMah,
      'cycle': t.cycleNumber,
    });

    try {
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return MLPrediction.fromJson(data);
      } else {
        debugPrint('[API] Prediction error status: ${response.statusCode}');
        return MLPrediction.fromLocalHeuristics(
          t.packVoltage, t.cell1Voltage, t.cell2Voltage, t.cell3Voltage, t.avgTemperature, t.current
        );
      }
    } catch (e) {
      debugPrint('[API] Prediction request failed: $e. Falling back to local heuristics.');
      return MLPrediction.fromLocalHeuristics(
        t.packVoltage, t.cell1Voltage, t.cell2Voltage, t.cell3Voltage, t.avgTemperature, t.current
      );
    }
  }
}
