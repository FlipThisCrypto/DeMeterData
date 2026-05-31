# docs/wiring/ — Sensor wiring reference

One Markdown file per sensor, plus a top-level pin allocation map. Tables and ASCII diagrams for now; image diagrams welcome as contributions.

> 📖 **If you're bringing up your first Tree**, use [`docs/OPERATOR_QUICKSTART.md`](../OPERATOR_QUICKSTART.md) instead — it has the pin map for the actual v1 prototype board (WROOM-32U) and an end-to-end bring-up procedure. This directory exists as the canonical per-sensor reference for adding more sensors later.

## Pin allocation — Classic ESP32 (WROOM-32 / WROOM-32U, v1 prototype)

This is the board in the v1 enclosure. Defaults from `firmware/include/pins.h` are **overridden** for this env via build flags in `firmware/platformio.ini`.

| Use                       | Pin       | Notes                                                                 |
|---------------------------|-----------|-----------------------------------------------------------------------|
| I2C SDA                   | GPIO 21   | Shared bus: BME280, AHT20, BMP280, BH1750                             |
| I2C SCL                   | GPIO 22   | Shared bus                                                            |
| GPS UART RX (from GPS TX) | GPIO 18   | Overridden in `platformio.ini` — not the pins.h default (4)           |
| GPS UART TX (to GPS RX)   | GPIO 19   | Overridden in `platformio.ini` — not the pins.h default (5)           |
| MQ-135 analog             | GPIO 34   | ADC1_CH6, input-only pin                                              |
| Status LED                | GPIO 2    | Freenove WROOM convention                                             |

## Pin allocation — ESP32-S3 (Freenove S3 dev board, optional)

| Use                       | Pin       | Notes                                  |
|---------------------------|-----------|----------------------------------------|
| I2C SDA                   | GPIO 21   | Shared bus                             |
| I2C SCL                   | GPIO 22   | Shared bus                             |
| GPS UART RX (from GPS TX) | GPIO 4    | UART1 RX                               |
| GPS UART TX (to GPS RX)   | GPIO 5    | UART1 TX                               |
| PMS5003 UART RX           | GPIO 16   | UART2 RX (driver planned)              |
| PMS5003 UART TX           | GPIO 17   | UART2 TX (driver planned)              |
| MQ-135 analog             | GPIO 34   | ADC1_CH6, input-only pin               |
| Status LED                | GPIO 48   | Freenove S3 onboard RGB                |

Pin assignments are **config**, not hardcoded — see `firmware/include/pins.h` for defaults and `firmware/platformio.ini` for per-board overrides via `-D ORCHARD_PIN_*` build flags.

## Per-sensor wiring files (planned)

- `mq135.md` — analog air quality sensor
- `neo-gps.md` — NEO-6M / 7M / 8M GPS module with active antenna
- `aht20.md` — temperature + humidity I2C combo
- `bmp280.md` — pressure I2C
- `bh1750.md` — ambient light I2C
- `pms5003.md` — PM2.5 particulate UART sensor

## How to add a new sensor wiring doc

Use the template at [../../examples/wiring/template.md](../../examples/wiring/template.md). Include:

1. **What it measures** and typical use cases.
2. **Module variants** (some sensors ship as multiple breakout boards with different pinouts).
3. **Pin-by-pin wiring table** against the Freenove ESP32-S3.
4. **I2C address** (if applicable) or **UART baud rate** and **frame format**.
5. **Calibration notes** — what readings mean, warm-up time, known quirks.
6. **Bring-up checklist** — copy/paste commands to confirm the sensor is alive (e.g., I2C scan output that should appear).
