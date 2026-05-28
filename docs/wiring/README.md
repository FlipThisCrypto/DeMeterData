# docs/wiring/ — Sensor wiring reference

One Markdown file per sensor, plus a top-level pin allocation map. Tables and ASCII diagrams for now; image diagrams welcome as contributions.

## ESP32-S3 pin allocation (Freenove dev board)

> **Important:** This board is ESP32-**S3**, not the more common ESP32-WROOM. Pin numbering and behavior differ. Always cross-check against the [Freenove ESP32-S3 pinout PDF](https://store.freenove.com/products/fnk0083).

| Use                  | Pin       | Notes                                  |
|----------------------|-----------|----------------------------------------|
| I2C SDA              | GPIO 21   | Shared bus: AHT20, BMP280, BH1750      |
| I2C SCL              | GPIO 22   | Shared bus                             |
| GPS UART RX (from GPS TX) | GPIO 4    | UART1 RX                          |
| GPS UART TX (to GPS RX)   | GPIO 5    | UART1 TX                          |
| PMS5003 UART RX      | GPIO 16   | UART2 RX (planned)                     |
| PMS5003 UART TX      | GPIO 17   | UART2 TX (planned)                     |
| MQ-135 analog        | GPIO 34   | ADC1_CH6, input-only pin               |

Pin assignments are **config**, not hardcoded — see `firmware/include/pins.h` (Phase 2).

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
