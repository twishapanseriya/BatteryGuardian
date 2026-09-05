/// Model representing AI-driven battery diagnostic and prognostic predictions
class MLPrediction {
  final double soh;            // State of Health (0.0 - 100.0 %)
  final int? rulCycles;        // Estimated remaining useful life (cycles)
  final int? rulLower;         // Lower confidence bound (cycles)
  final int? rulUpper;         // Upper confidence bound (cycles)
  final int healthScore;       // Unified Health Score (0 - 100)
  final String riskLevel;      // "LOW", "MEDIUM", "HIGH"
  final int weakestCell;       // 1, 2, or 3
  final double cellImbalanceMv; // Imbalance in mV
  final List<String> insights; // AI diagnostic bullet points
  final String validationStatus; // "Public Dataset Trained" / "Hardware Validated"
  final DateTime lastUpdated;

  MLPrediction({
    required this.soh,
    this.rulCycles,
    this.rulLower,
    this.rulUpper,
    required this.healthScore,
    required this.riskLevel,
    required this.weakestCell,
    required this.cellImbalanceMv,
    required this.insights,
    this.validationStatus = 'Prototype — Public Dataset Trained (NASA PCoE)',
    required this.lastUpdated,
  });

  factory MLPrediction.fromJson(Map<String, dynamic> json) {
    return MLPrediction(
      soh: (json['soh'] as num?)?.toDouble() ?? 100.0,
      rulCycles: (json['rul_cycles'] as num?)?.toInt(),
      rulLower: (json['rul_lower'] as num?)?.toInt(),
      rulUpper: (json['rul_upper'] as num?)?.toInt(),
      healthScore: (json['health_score'] as num?)?.toInt() ?? 100,
      riskLevel: json['risk'] as String? ?? 'LOW',
      weakestCell: (json['weakest_cell'] as num?)?.toInt() ?? 1,
      cellImbalanceMv: (json['cell_imbalance_mv'] as num?)?.toDouble() ?? 0.0,
      insights: (json['insights'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      validationStatus: json['validation_status'] as String? ?? 'Prototype — Public Dataset Trained (NASA PCoE)',
      lastUpdated: DateTime.now(),
    );
  }

  /// Fallback baseline heuristic calculation when offline / ML API unavailable
  factory MLPrediction.fromLocalHeuristics(double packV, double c1, double c2, double c3, double temp, double curr) {
    final imbMv = ([c1, c2, c3].reduce((a, b) => a > b ? a : b) - [c1, c2, c3].reduce((a, b) => a < b ? a : b)) * 1000.0;
    
    // Heuristic SoH estimate based on nominal retention
    double estimatedSoh = 100.0;
    if (packV < 9.5) {
      estimatedSoh = 82.0;
    } else if (imbMv > 100) {
      estimatedSoh -= (imbMv - 100) * 0.1;
    }
    estimatedSoh = estimatedSoh.clamp(0.0, 100.0);

    // Heuristic Health Score
    int score = 100;
    if (imbMv > 80) score -= ((imbMv - 80) ~/ 5);
    if (temp > 45) score -= ((temp - 45) * 2).toInt();
    if (packV < 9.0) score -= 30;
    score = score.clamp(0, 100);

    String risk = 'LOW';
    if (score < 60 || imbMv > 120 || temp > 50) {
      risk = 'HIGH';
    } else if (score < 80 || imbMv > 60 || temp > 40) {
      risk = 'MEDIUM';
    }

    int weakest = 1;
    if (c2 <= c1 && c2 <= c3) weakest = 2;
    if (c3 <= c1 && c3 <= c2) weakest = 3;

    List<String> insightsList = [];
    if (imbMv > 80) insightsList.add('Elevated cell imbalance (${imbMv.toStringAsFixed(0)} mV) detected on Cell $weakest.');
    if (temp > 45) insightsList.add('Operating temperature is elevated (${temp.toStringAsFixed(1)}°C).');
    if (insightsList.isEmpty) insightsList.add('All battery telemetry parameters operating in nominal range.');

    return MLPrediction(
      soh: estimatedSoh,
      rulCycles: null, // Transparently null when history is insufficient
      rulLower: null,
      rulUpper: null,
      healthScore: score,
      riskLevel: risk,
      weakestCell: weakest,
      cellImbalanceMv: imbMv,
      insights: insightsList,
      validationStatus: 'Local Real-Time Heuristics (ML Offline)',
      lastUpdated: DateTime.now(),
    );
  }
}
