// SPDX-License-Identifier: Apache-2.0
//
// The Orchard sensor driver template.
//
// Copy this file (and template.cpp) into firmware/src/sensors/, rename to
// match your sensor (e.g. sht41.h / sht41.cpp), and fill in the blanks.

#pragma once

#include <ArduinoJson.h>
#include "sensor.h"  // defines the abstract Sensor base class

namespace demeter::sensors {

class TemplateSensor : public Sensor {
 public:
  // Required: identify the sensor in dashboard / oracle payloads.
  const char* name() const override { return "template"; }

  // Required: which physical bus this sensor lives on. One of:
  //   BusType::I2C, BusType::UART, BusType::ANALOG, BusType::DIGITAL
  BusType bus_type() const override { return BusType::I2C; }

  // For I2C drivers: return the 7-bit address. The runtime uses this for
  // auto-detection (scan the bus, match address to driver). Return 0 if N/A.
  uint8_t i2c_address() const override { return 0x00; }

  // Initialize the sensor. Called once at boot. Return true on success.
  bool begin() override;

  // Sample the sensor and write fields onto `out`. Called periodically.
  // Use snake_case keys, SI units. Example: out["temperature_c"] = 23.4;
  bool read(JsonObject& out) override;
};

}  // namespace demeter::sensors
