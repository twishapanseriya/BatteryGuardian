import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/battery_provider.dart';
import '../models/battery_telemetry.dart';

class LiveMonitorScreen extends StatelessWidget {
  const LiveMonitorScreen({Key? key}) : super(key: key);

  Widget _buildChartCard(
    String title,
    String latestValue,
    String unit,
    Color color,
    List<BatteryTelemetry> history,
    double Function(BatteryTelemetry) valueExtractor,
  ) {
    List<FlSpot> spots = [];
    for (int i = 0; i < history.length; i++) {
      spots.add(FlSpot(i.toDouble(), valueExtractor(history[i])));
    }

    if (spots.isEmpty) {
      spots = [const FlSpot(0, 0)];
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title.toUpperCase(),
                style: const TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.1,
                ),
              ),
              Text(
                '$latestValue $unit',
                style: TextStyle(
                  color: color,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 130,
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (val) => const FlLine(color: Color(0xFF334155), strokeWidth: 1),
                ),
                titlesData: const FlTitlesData(show: false),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: color,
                    barWidth: 2.5,
                    isStrokeCapRound: true,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: color.withOpacity(0.12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BatteryProvider>(context);
    final history = provider.recentHistory;
    final t = provider.latestTelemetry;

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B0F19),
        elevation: 0,
        title: const Text(
          'LIVE TELEMETRY MONITOR',
          style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        children: [
          _buildChartCard(
            'Pack Voltage',
            (t?.packVoltage ?? 12.23).toStringAsFixed(2),
            'V',
            const Color(0xFF38BDF8),
            history,
            (item) => item.packVoltage,
          ),
          _buildChartCard(
            'Discharge Current',
            (t?.current ?? 0.12).toStringAsFixed(3),
            'A',
            const Color(0xFFF59E0B),
            history,
            (item) => item.current,
          ),
          _buildChartCard(
            'Cell Imbalance (ΔV)',
            ((t?.cellImbalance ?? 0.088) * 1000).toStringAsFixed(0),
            'mV',
            const Color(0xFFA855F7),
            history,
            (item) => item.cellImbalance * 1000.0,
          ),
          _buildChartCard(
            'Average Temperature',
            (t?.avgTemperature ?? 28.5).toStringAsFixed(1),
            '°C',
            const Color(0xFFEF4444),
            history,
            (item) => item.avgTemperature,
          ),
        ],
      ),
    );
  }
}
