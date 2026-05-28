// SPDX-License-Identifier: Apache-2.0
//
// Bosch BME280 — temperature + humidity + pressure (I2C).
//
// Standard breakout boards expose the chip at address 0x76 or 0x77
// (configurable by a solder jumper labeled `ADDR` or `SDO`). We probe
// both in `begin()` and remember whichever responded.

#pragma once

#include "sensor.h"

#include <Adafruit_BME280.h>

namespace orchard::sensors {

class BME280Sensor : public Sensor {
 public:
  const char* name() const override { return "bme280"; }
  BusType bus_type() const override { return BusType::kI2C; }
  uint8_t i2c_address() const override { return active_address_; }

  bool begin() override;
  bool read(JsonObject out) override;

 private:
  Adafruit_BME280 bme_;
  uint8_t active_address_ = 0;
};

}  // namespace orchard::sensors
