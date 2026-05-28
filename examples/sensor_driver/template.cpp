// SPDX-License-Identifier: Apache-2.0
//
// The Orchard sensor driver template — implementation.

#include "template.h"

#include <Wire.h>

namespace demeter::sensors {

bool TemplateSensor::begin() {
  // 1. Initialize bus if not already (the runtime calls Wire.begin() once
  //    globally, but you can probe a register here).
  // 2. Probe the device. Bail out on failure so the runtime knows the
  //    sensor isn't present.
  //
  // Example for an I2C device:
  //   Wire.beginTransmission(i2c_address());
  //   if (Wire.endTransmission() != 0) return false;
  return false;  // replace with real check
}

bool TemplateSensor::read(JsonObject& out) {
  // Sample and write fields onto `out`. Return true if read succeeded.
  //
  // Example:
  //   out["temperature_c"] = 23.4;
  //   out["humidity_pct"] = 51.2;
  return false;  // replace with real read
}

// Self-register at static init time so the runtime can find this driver
// without a central if-else chain.
//
//   static auto _registered =
//       SensorRegistry::Register<TemplateSensor>();

}  // namespace demeter::sensors
