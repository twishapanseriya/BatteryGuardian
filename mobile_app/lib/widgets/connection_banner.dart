import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:provider/provider.dart';
import '../providers/battery_provider.dart';
import '../services/ble_service.dart';

class ConnectionBanner extends StatelessWidget {
  const ConnectionBanner({Key? key}) : super(key: key);

  void _showScanDialog(BuildContext context, BatteryProvider provider) {
    provider.startScan();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Connect BatteryGuardian', style: TextStyle(color: Colors.white)),
        content: SizedBox(
          width: double.maxFinite,
          height: 300,
          child: StreamBuilder<List<ScanResult>>(
            stream: FlutterBluePlus.scanResults,
            builder: (context, snapshot) {
              final results = snapshot.data ?? [];
              if (results.isEmpty) {
                return const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircularProgressIndicator(color: Color(0xFF38BDF8)),
                      SizedBox(height: 16),
                      Text('Scanning for ESP32...', style: TextStyle(color: Color(0xFF94A3B8))),
                    ],
                  ),
                );
              }
              return ListView.builder(
                itemCount: results.length,
                itemBuilder: (context, index) {
                  final result = results[index];
                  final name = result.device.platformName.isNotEmpty
                      ? result.device.platformName
                      : (result.advertisementData.advName.isNotEmpty
                          ? result.advertisementData.advName
                          : 'Unknown Device');
                  final isBatteryGuardian = name.contains('BatteryGuardian');

                  return ListTile(
                    leading: Icon(
                      Icons.bluetooth,
                      color: isBatteryGuardian ? const Color(0xFF38BDF8) : const Color(0xFF64748B),
                    ),
                    title: Text(name, style: const TextStyle(color: Colors.white)),
                    subtitle: Text('${result.rssi} dBm | ${result.device.remoteId}',
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
                    onTap: () async {
                      Navigator.of(ctx).pop();
                      await provider.connect(result.device);
                    },
                  );
                },
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              provider.stopScan();
              Navigator.of(ctx).pop();
            },
            child: const Text('Cancel', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BatteryProvider>(context);
    final status = provider.connectionStatus;

    Color statusColor;
    String statusText;
    IconData statusIcon;

    switch (status) {
      case BleConnectionStatus.ready:
        statusColor = const Color(0xFF10B981);
        statusText = 'Connected to ESP32 (Live Telemetry)';
        statusIcon = Icons.bluetooth_connected;
        break;
      case BleConnectionStatus.connecting:
      case BleConnectionStatus.discoveringServices:
        statusColor = Colors.amber;
        statusText = 'Connecting to ESP32...';
        statusIcon = Icons.bluetooth_searching;
        break;
      case BleConnectionStatus.scanning:
        statusColor = const Color(0xFF38BDF8);
        statusText = 'Scanning for Devices...';
        statusIcon = Icons.bluetooth_searching;
        break;
      case BleConnectionStatus.disconnected:
      default:
        statusColor = const Color(0xFFEF4444);
        statusText = 'Disconnected from Hardware';
        statusIcon = Icons.bluetooth_disabled;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(
                color: statusColor,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (status == BleConnectionStatus.ready)
            TextButton(
              onPressed: () => provider.disconnect(),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('Disconnect', style: TextStyle(color: Color(0xFFEF4444), fontSize: 11)),
            )
          else
            ElevatedButton(
              onPressed: () => _showScanDialog(context, provider),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2563EB),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('Connect', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
            ),
        ],
      ),
    );
  }
}
