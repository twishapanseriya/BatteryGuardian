import 'package:flutter/material.dart';

class CellVoltageCard extends StatelessWidget {
  final double cell1;
  final double cell2;
  final double cell3;
  final double imbalance;
  final int weakestCell;

  const CellVoltageCard({
    Key? key,
    required this.cell1,
    required this.cell2,
    required this.cell3,
    required this.imbalance,
    required this.weakestCell,
  }) : super(key: key);

  Widget _buildCellBar(String label, double voltage, bool isWeakest) {
    // 3S Li-ion nominal 2.5V - 4.2V scale
    final percentage = ((voltage - 2.5) / (4.2 - 2.5)).clamp(0.0, 1.0);
    final color = isWeakest && (imbalance > 0.08) ? Colors.amber : const Color(0xFF38BDF8);

    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isWeakest && (imbalance > 0.08) ? Colors.amber.withOpacity(0.5) : const Color(0xFF334155),
          ),
        ),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (isWeakest && (imbalance > 0.08))
                  const Padding(
                    padding: EdgeInsets.only(left: 4),
                    child: Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 14),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '${voltage.toStringAsFixed(2)} V',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: percentage,
                minHeight: 6,
                backgroundColor: const Color(0xFF1E293B),
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
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
              const Text(
                'INDIVIDUAL CELL VOLTAGES',
                style: TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.1,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: (imbalance > 0.08) ? Colors.amber.withOpacity(0.15) : const Color(0xFF10B981).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'ΔV: ${(imbalance * 1000).toStringAsFixed(0)} mV',
                  style: TextStyle(
                    color: (imbalance > 0.08) ? Colors.amber : const Color(0xFF10B981),
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              _buildCellBar('Cell 1', cell1, weakestCell == 1),
              _buildCellBar('Cell 2', cell2, weakestCell == 2),
              _buildCellBar('Cell 3', cell3, weakestCell == 3),
            ],
          ),
        ],
      ),
    );
  }
}
