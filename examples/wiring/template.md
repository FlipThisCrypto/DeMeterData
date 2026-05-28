# `<Sensor Name>` wiring

> Copy this file into `docs/wiring/`, rename it to match your sensor (e.g. `sht41.md`), and fill in the sections. Delete the instructional notes once filled in.

## What it measures

> 1-2 sentences. What does this sensor do? What units does it report? Typical use cases.

## Module variants

> Sensors often ship as multiple breakout-board variants. List the ones you've tested. Include vendor names and any pin differences.

| Variant       | Vendor   | Pin labels        | Notes                       |
|---------------|----------|-------------------|-----------------------------|
| `<name>`      | `<...>`  | `VCC GND SDA SCL` | `<any quirks>`              |

## Pin-by-pin wiring (Freenove ESP32-S3)

| Sensor pin | ESP32-S3 pin | Notes                       |
|------------|--------------|-----------------------------|
| VCC        | 3.3V         | Some variants accept 5V     |
| GND        | GND          |                             |
| SDA        | GPIO 21      | Shared I2C bus              |
| SCL        | GPIO 22      | Shared I2C bus              |

> For UART sensors: list TX/RX and required baud rate. Remember TX on sensor goes to RX on ESP32 (and vice versa).
>
> For analog sensors: list ADC pin (ESP32-S3 ADC1 pins only — GPIO 1–10). Note any voltage divider.

## Protocol details

> **I2C devices:** address (default + alt), required pull-up resistors.
>
> **UART devices:** baud rate, frame format, sentence/packet structure.
>
> **Analog devices:** voltage range, reference voltage, calibration curve.

## Calibration notes

> Warm-up time, drift behavior, known quirks. Anything a first-time user might trip over.

## Bring-up checklist

> Steps to confirm the sensor is alive before integrating into the firmware.

1. Wire as above.
2. Run an I2C bus scan / UART monitor / multimeter check. Expected output:

```
<paste expected output>
```

3. Load the driver. Confirm `name()` appears in the dashboard Scan page.

## Known issues

> Anything that has bitten you. Future-you will appreciate it.

## References

- Datasheet: `<link>`
- Library used: `<link>`
