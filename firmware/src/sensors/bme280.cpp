// SPDX-License-Identifier: Apache-2.0
#include "bme280.h"

#include <Arduino.h>
#include <math.h>

namespace orchard::sensors {

bool BME280Sensor::begin() {
  // Try both common addresses; remember which one took.
  if (bme_.begin(0x76)) {
    active_address_ = 0x76;
  } else if (bme_.begin(0x77)) {
    active_address_ = 0x77;
  } else {
    return false;
  }
  // Weather-station-friendly settings: 1x oversampling on each channel,
  // no IIR filter, 1Hz standby. Adafruit defaults to NORMAL mode after
  // begin() which is what we want — the chip auto-samples continuously.
  bme_.setSampling(Adafruit_BME280::MODE_NORMAL,
                   Adafruit_BME280::SAMPLING_X1,   // temp
                   Adafruit_BME280::SAMPLING_X1,   // pressure
                   Adafruit_BME280::SAMPLING_X1,   // humidity
                   Adafruit_BME280::FILTER_OFF,
                   Adafruit_BME280::STANDBY_MS_1000);
  return true;
}

bool BME280Sensor::read(JsonObject out) {
  const float t = bme_.readTemperature();        // Celsius
  const float h = bme_.readHumidity();           // %
  const float p_pa = bme_.readPressure();        // Pa
  if (isnan(t) || isnan(h) || isnan(p_pa)) {
    return false;
  }
  out["temperature_c"] = t;
  out["humidity_pct"]  = h;
  out["pressure_hpa"]  = p_pa / 100.0f;
  out["i2c_addr"]      = active_address_;
  return true;
}

}  // namespace orchard::sensors

// Self-register so the driver shows up in the registry without any
// central #include / wiring.
static orchard::sensors::AutoRegister<orchard::sensors::BME280Sensor>
    _bme280_register;
