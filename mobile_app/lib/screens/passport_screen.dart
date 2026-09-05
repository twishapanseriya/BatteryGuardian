import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/battery_provider.dart';

class PassportScreen extends StatelessWidget {
  const PassportScreen({Key? key}) : super(key: key);

  Widget _buildPassportRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
          ),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BatteryProvider>(context);
    final t = provider.latestTelemetry;
    final pred = provider.latestPrediction;

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B0F19),
        elevation: 0,
        title: const Text(
          'BATTERY DIGITAL PASSPORT',
          style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        children: [
          // Passport Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF38BDF8).withOpacity(0.4)),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF38BDF8).withOpacity(0.08),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'BATTERY ID: BG-3S-001',
                      style: TextStyle(
                        color: Color(0xFF38BDF8),
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.1,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'ACTIVE',
                        style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const Divider(color: Color(0xFF334155), height: 24),
                _buildPassportRow('Cell Chemistry', 'Li-ion (IMR-18650)'),
                _buildPassportRow('Configuration', '3S1P (Series 3-Cell)'),
                _buildPassportRow('Nominal Voltage', '11.1 V (3 x 3.7V)'),
                _buildPassportRow('Nominal Pack Capacity', '1200 mAh (13.32 Wh)'),
                _buildPassportRow('Full Charge / Cutoff', '12.60 V / 9.00 V'),
                _buildPassportRow('Discharge Load Rating', '100 Ω, 50 W (C/10)'),
                _buildPassportRow('Operating Cycle Count', '${t?.cycleNumber ?? 1}'),
                _buildPassportRow('Discharged Energy', '${(t?.dischargedMah ?? 0.0).toStringAsFixed(1)} mAh'),
                const Divider(color: Color(0xFF334155), height: 24),
                _buildPassportRow('Current State of Health (SoH)', '${(pred?.soh ?? 100.0).toStringAsFixed(1)} %',
                    valueColor: const Color(0xFF10B981)),
                _buildPassportRow(
                  'Estimated RUL',
                  pred?.rulCycles != null ? '${pred!.rulCycles} Cycles' : 'Active Baseline',
                  valueColor: const Color(0xFF38BDF8),
                ),
                _buildPassportRow('Weakest Series Cell', 'Cell ${pred?.weakestCell ?? (t?.weakestCellIndex ?? 3)}'),
                _buildPassportRow(
                  'Last Live Sync',
                  DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now()),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ML Model Transparency Box
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
                    Icon(Icons.verified_outlined, color: Color(0xFF38BDF8), size: 18),
                    SizedBox(width: 8),
                    Text(
                      'ML MODEL PROVENANCE & DISCLOSURES',
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
                _buildPassportRow('ML Training Source', 'NASA Ames PCoE Battery Aging Dataset'),
                _buildPassportRow('Reference Chemistry', 'LiCoO2 (18650 2.0Ah Benchmark)'),
                _buildPassportRow('Model Validation Status', 'Prototype — Public Domain Trained',
                    valueColor: Colors.amber),
                const SizedBox(height: 8),
                const Text(
                  'Notice: ML models are pre-trained on NASA PCoE degradation benchmarks. Real-world BatteryGuardian telemetry streams over BLE for live inference and domain-gap evaluation.',
                  style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontStyle: FontStyle.italic),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
