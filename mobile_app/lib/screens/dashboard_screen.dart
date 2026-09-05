import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/battery_provider.dart';
import '../widgets/health_score_gauge.dart';
import '../widgets/cell_voltage_card.dart';
import '../widgets/parameter_tile.dart';
import '../widgets/connection_banner.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BatteryProvider>(context);
    final t = provider.latestTelemetry;
    final pred = provider.latestPrediction;

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19), // Deep dark space background
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B0F19),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF38BDF8).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.bolt, color: Color(0xFF38BDF8), size: 20),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'BATTERYGUARDIAN AI',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.1,
                  ),
                ),
                Text(
                  'Hardware Telemetry & Predictive Health',
                  style: TextStyle(color: Color(0xFF64748B), fontSize: 10),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.share, color: Color(0xFF38BDF8)),
            tooltip: 'Export CSV',
            onPressed: () => provider.exportAndShareCsv(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => await provider.exportAndShareCsv(),
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          children: [
            // 1. Connection Status Banner
            const ConnectionBanner(),
            const SizedBox(height: 16),

            // 2. Health Score & AI Risk Gauge
            HealthScoreGauge(
              score: pred?.healthScore ?? 100,
              riskLevel: pred?.riskLevel ?? 'LOW',
            ),
            const SizedBox(height: 16),

            // 3. AI Prognostics Summary (SoH & RUL)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'AI PROGNOSTICS (SOH & RUL)',
                        style: TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.1,
                        ),
                      ),
                      Icon(Icons.psychology, color: Color(0xFF38BDF8), size: 18),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('State of Health (SoH)',
                                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                            const SizedBox(height: 4),
                            Text(
                              '${(pred?.soh ?? 100.0).toStringAsFixed(1)} %',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(width: 1, height: 40, color: const Color(0xFF334155)),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Remaining Useful Life (RUL)',
                                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                            const SizedBox(height: 4),
                            Text(
                              pred?.rulCycles != null
                                  ? '${pred!.rulLower ?? pred.rulCycles! - 30}–${pred.rulUpper ?? pred.rulCycles! + 30} cyc'
                                  : 'Active Baseline',
                              style: const TextStyle(
                                color: Color(0xFF38BDF8),
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Validation: ${pred?.validationStatus ?? "Public Dataset Baseline"}',
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 10, fontStyle: FontStyle.italic),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 4. Individual Cell Voltages Card
            CellVoltageCard(
              cell1: t?.cell1Voltage ?? 4.12,
              cell2: t?.cell2Voltage ?? 4.08,
              cell3: t?.cell3Voltage ?? 4.03,
              imbalance: t?.cellImbalance ?? 0.09,
              weakestCell: pred?.weakestCell ?? (t?.weakestCellIndex ?? 3),
            ),
            const SizedBox(height: 16),

            // 5. Parameter Grid (Pack V, Current, Temp, Energy)
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.5,
              children: [
                ParameterTile(
                  title: 'Pack Voltage',
                  value: (t?.packVoltage ?? 12.23).toStringAsFixed(2),
                  unit: 'V',
                  icon: Icons.electric_meter,
                  accentColor: const Color(0xFF38BDF8),
                ),
                ParameterTile(
                  title: 'Discharge Current',
                  value: (t?.current ?? 0.12).toStringAsFixed(3),
                  unit: 'A',
                  icon: Icons.speed,
                  accentColor: const Color(0xFFF59E0B),
                ),
                ParameterTile(
                  title: 'Battery Temp (Avg)',
                  value: (t?.avgTemperature ?? 28.5).toStringAsFixed(1),
                  unit: '°C',
                  icon: Icons.thermostat,
                  accentColor: const Color(0xFFEF4444),
                ),
                ParameterTile(
                  title: 'Discharged Energy',
                  value: (t?.dischargedMah ?? 14.2).toStringAsFixed(1),
                  unit: 'mAh',
                  icon: Icons.battery_charging_full,
                  accentColor: const Color(0xFF10B981),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 6. AI Insights / Diagnostic Warnings
            if (pred != null && pred.insights.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.lightbulb_outline, color: Colors.amber, size: 18),
                        SizedBox(width: 8),
                        Text(
                          'AI DIAGNOSTIC INSIGHTS',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...pred.insights.map(
                      (insight) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 14)),
                            Expanded(
                              child: Text(
                                insight,
                                style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
