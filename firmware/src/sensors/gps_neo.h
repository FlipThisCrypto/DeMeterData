// SPDX-License-Identifier: Apache-2.0
//
// NEO-6M / 7M / 8M GPS module driver.
//
// Reads NMEA sentences from a UART, parses them with TinyGPSPlus, and
// reports the latest fix when sampled. Continually consumes bytes in
// `read()` so a periodic sample cadence still picks up fresh fixes.

#pragma once

#include "sensor.h"
#include <TinyGPSPlus.h>

namespace orchard::sensors {

class GpsNeoSensor : public Sensor {
 public:
  const char* name() const override { return "gps"; }
  BusType bus_type() const override { return BusType::kUART; }

  bool begin() override;
  bool read(JsonObject out) override;

 private:
  void pump_uart_();
  TinyGPSPlus gps_;
};

}  // namespace orchard::sensors
