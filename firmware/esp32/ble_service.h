#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include "config.h"

// Initialize BLE GATT Server and Advertising
bool initBLE();

// Check if a client (Flutter App) is currently connected
bool isBLEConnected();

// Broadcast structured JSON telemetry via Notify characteristic
bool sendBLETelemetry(const char *json_payload);

// Maintain BLE Advertising state
void updateBLE();

#endif // BLE_SERVICE_H
