// SPDX-License-Identifier: Apache-2.0
//
// Pin allocation for the v1 Tree (Freenove ESP32-S3 + sensors).
//
// Cross-check against the Freenove ESP32-S3 pinout PDF before flashing.
// All pins here are configurable at build time via `-D ORCHARD_PIN_*`
// flags in platformio.ini if you need to relocate.

#pragma once

// --- I2C bus (shared by AHT20, BMP280, BH1750 when added) -----------
#ifndef ORCHARD_PIN_I2C_SDA
#define ORCHARD_PIN_I2C_SDA  21
#endif
#ifndef ORCHARD_PIN_I2C_SCL
#define ORCHARD_PIN_I2C_SCL  22
#endif

// --- GPS NEO module on UART1 (confirmed working) --------------------
#ifndef ORCHARD_PIN_GPS_RX        // ESP32 RX  <- GPS TX
#define ORCHARD_PIN_GPS_RX   4
#endif
#ifndef ORCHARD_PIN_GPS_TX        // ESP32 TX  -> GPS RX
#define ORCHARD_PIN_GPS_TX   5
#endif

// --- PMS5003 on UART2 (when added) ----------------------------------
#ifndef ORCHARD_PIN_PMS_RX
#define ORCHARD_PIN_PMS_RX   16
#endif
#ifndef ORCHARD_PIN_PMS_TX
#define ORCHARD_PIN_PMS_TX   17
#endif

// --- MQ-135 analog (ADC1_CH6 on ESP32-S3 — input only) --------------
#ifndef ORCHARD_PIN_MQ135_ADC
#define ORCHARD_PIN_MQ135_ADC  34
#endif

// --- Status LED (Freenove S3 onboard) -------------------------------
#ifndef ORCHARD_PIN_STATUS_LED
#define ORCHARD_PIN_STATUS_LED  48
#endif
