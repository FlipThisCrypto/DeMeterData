// SPDX-License-Identifier: Apache-2.0
//
// MQ-135 air-quality sensor — analog read of an exposed sensor element.
//
// MQ-135 outputs an analog voltage inversely related to overall gas
// concentration (VOCs, NH3, NOx, alcohol, smoke). We do NOT attempt to
// calibrate it to specific ppm in v1 — we report raw ADC and a coarse
// "air_quality_index" derived from running baseline. Treat values as
// relative, not absolute.

#pragma once

#include "sensor.h"

namespace orchard::sensors {

class MQ135Sensor : public Sensor {
 public:
  const char* name() const override { return "mq135"; }
  BusType bus_type() const override { return BusType::kAnalog; }

  bool begin() override;
  bool read(JsonObject out) override;

 private:
  // Simple running baseline (exponential moving average) so we can
  // report a relative AQI without per-device calibration.
  float baseline_ = 0.0f;
  bool baseline_initialized_ = false;
};

}  // namespace orchard::sensors
