#include "ble_service.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

static BLEServer *s_pServer = nullptr;
static BLECharacteristic *s_pTelemetryChar = nullptr;
static bool s_deviceConnected = false;
static bool s_oldDeviceConnected = false;

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        s_deviceConnected = true;
        Serial.println("[BLE] Client connected.");
    }

    void onDisconnect(BLEServer* pServer) {
        s_deviceConnected = false;
        Serial.println("[BLE] Client disconnected.");
    }
};

bool initBLE() {
    // 1. Initialize BLE Device Name
    BLEDevice::init(DEVICE_NAME);
    
    // 2. Create the BLE Server
    s_pServer = BLEDevice::createServer();
    s_pServer->setCallbacks(new ServerCallbacks());
    
    // 3. Create the Primary BatteryGuardian BLE Service
    BLEService *pService = s_pServer->createService(SERVICE_UUID);
    
    // 4. Create the Telemetry Characteristic (Notify & Read)
    s_pTelemetryChar = pService->createCharacteristic(
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_NOTIFY
    );
    
    // 5. Add BLE2902 Descriptor for Notification subscriptions
    s_pTelemetryChar->addDescriptor(new BLE2902());
    
    // 6. Start the Service
    pService->start();
    
    // 7. Configure and Start BLE Advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06); // functions that help with iPhone connections issue
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
    
    Serial.println("[BLE] GATT Server active and advertising.");
    return true;
}

bool isBLEConnected() {
    return s_deviceConnected;
}

bool sendBLETelemetry(const char *json_payload) {
    if (!s_deviceConnected || s_pTelemetryChar == nullptr) {
        return false;
    }
    
    s_pTelemetryChar->setValue((uint8_t*)json_payload, strlen(json_payload));
    s_pTelemetryChar->notify();
    return true;
}

void updateBLE() {
    // Auto-restart advertising upon disconnection
    if (!s_deviceConnected && s_oldDeviceConnected) {
        delay(500); // Give the bluetooth stack a chance to prepare
        s_pServer->startAdvertising();
        Serial.println("[BLE] Restarted advertising.");
        s_oldDeviceConnected = s_deviceConnected;
    }
    
    if (s_deviceConnected && !s_oldDeviceConnected) {
        s_oldDeviceConnected = s_deviceConnected;
    }
}
