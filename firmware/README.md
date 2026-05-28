# firmware/ — Tree firmware (ESP32-S3)

Modular firmware for a **Tree** — a deployed node in The Orchard. Built with PlatformIO and the Arduino-ESP32 framework, targeting the **Freenove ESP32-S3** dev board.

> **Vocabulary:** In code, the unit is a `node`; in user-facing copy, it's a **Tree**. See the [Glossary](../README.md#glossary).

## Why this is its own component

The firmware is what runs on every deployed Tree — it owns sensor sampling, WiFi, GPS parsing, signed POSTs to the oracle, and OTA updates. It must work without the dashboard or oracle being reachable (resilient buffering of readings) and must let future contributors add new sensor types without touching unrelated code.

## Structure (planned for Phase 2)

```
firmware/
├── platformio.ini       # board + framework + libs
├── include/             # shared headers
└── src/
    ├── main.cpp         # setup() / loop()
    ├── sensors/         # self-registering sensor drivers
    │   ├── sensor.h     # base interface (bus_type, begin, read)
    │   ├── mq135.cpp
    │   ├── gps_neo.cpp
    │   ├── aht20.cpp
    │   ├── bmp280.cpp
    │   ├── bh1750.cpp
    │   └── pms5003.cpp
    ├── net/
    │   ├── wifi_mgr.cpp # join, reconnect, soft-AP fallback
    │   ├── oracle.cpp   # signed POST client
    │   └── ota.cpp      # OTA update endpoint
    └── identity.cpp     # device key generation + node id
```

## Design principles

- **Self-registering sensors.** Each driver registers itself with the runtime at startup. Adding a sensor = drop in a `.cpp` + add it to the build. No central if-else chain.
- **Resilient.** Readings are buffered if the oracle is unreachable. WiFi reconnects on failure. OTA never bricks the device (uses the standard Arduino-ESP32 OTA partition table).
- **Signed.** Every POST includes an ed25519 signature over the payload + timestamp using a key generated on first boot and persisted in NVS. The private key never leaves the device.
- **Modular radios.** WiFi today. LoRa / cellular interfaces will slot into `net/` without touching sensors.

## Status

Phase 2 — not yet implemented. See [../docs/decisions/0001-v1-architecture.md](../docs/decisions/0001-v1-architecture.md).
