# dashboard/ — Orchard View (local Flask dashboard)

**Orchard View** is the local web UI you run on your PC. Connects to a USB-attached Tree and to the local oracle. Designed for the "I just plugged in my first Tree" experience: one command, one browser tab, everything visible.

## Why this is its own component

Setup tooling has different lifecycle and dependencies than the oracle (the oracle needs to be running 24/7; the dashboard is opened by a human, used, closed). Splitting them keeps each lean.

## Planned pages (Phase 4)

1. **Connect** — pick a USB serial port. Auto-detect ESP32-S3.
2. **Scan** — show I2C bus contents (auto-map known addresses to sensor types), sniff UART for known protocol signatures (NMEA, PMS5003), and surface a sensor-declaration form for analog/digital sensors that can't be auto-detected.
3. **Live** — current readings from each sensor, GPS map, uptime, last attestation.
4. **WiFi** — push SSID/password to the ESP32 over serial.
5. **OTA** — upload a new firmware binary and trigger an OTA update.
6. **Register Tree** — wizard for binding this Tree to a wallet. Verifies the wallet holds an **Orchard Pass** NFT.
7. **Admin** — list of all registered Trees, status, Season harvest history.

## Design principle: copy-paste deployable

Anyone replicating this build should be able to:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r dashboard/requirements.txt
python -m dashboard.app
```

…and have a working dashboard. No system-level dependencies beyond Python.

## Status

Phase 4 — not yet implemented. Depends on Phase 2 (firmware command surface for the WiFi / OTA / read flows) and Phase 3 (oracle endpoints).
