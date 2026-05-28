// SPDX-License-Identifier: Apache-2.0
//
// Base interface for Tree sensor drivers + a self-registering registry.
//
// To add a new sensor:
//   1. Subclass `Sensor`, implement `name()`, `bus_type()`, `begin()`,
//      `read(JsonObject)`.
//   2. At namespace scope in your .cpp, declare:
//        static orchard::sensors::AutoRegister<YourSensorClass> _your_reg;
//   3. Done — it'll be discovered at startup with no central registration.
//
// See examples/sensor_driver/template.{h,cpp} for a copy/paste template.

#pragma once

#include <ArduinoJson.h>
#include <memory>
#include <vector>

namespace orchard::sensors {

enum class BusType {
  kI2C,
  kUART,
  kAnalog,
  kDigital,
  kInternal,  // e.g. ESP32 die temperature
};

class Sensor {
 public:
  virtual ~Sensor() = default;

  // Short, snake_case identifier used in the JSON payload key.
  virtual const char* name() const = 0;

  // Which physical bus the sensor lives on (for auto-detection logic).
  virtual BusType bus_type() const = 0;

  // For I2C drivers, the 7-bit address (0 if not applicable).
  virtual uint8_t i2c_address() const { return 0; }

  // Initialize the sensor. Return true on success. False here means
  // the sensor isn't present (or failed to come up) and the registry
  // will skip it during sampling.
  virtual bool begin() = 0;

  // Sample the sensor; write fields into `out`. Use snake_case keys and
  // SI units (e.g. out["temperature_c"] = 23.4).
  // Return true if the read succeeded.
  virtual bool read(JsonObject out) = 0;

  // Status (set by the registry after begin()).
  bool is_active() const { return active_; }
  void set_active(bool a) { active_ = a; }

 private:
  bool active_ = false;
};

class SensorRegistry {
 public:
  static SensorRegistry& instance();

  void add(std::unique_ptr<Sensor> s);

  // Call after WiFi/Wire init. Calls begin() on every registered sensor
  // and marks each active or not based on the return value.
  void begin_all();

  // All registered sensors (even inactive ones).
  const std::vector<std::unique_ptr<Sensor>>& all() const { return sensors_; }

  // Count of sensors that returned true from begin().
  size_t active_count() const;

  // Sample every active sensor; write each sensor's data under
  // `parent[sensor->name()]`.
  void sample_all(JsonObject parent);

 private:
  SensorRegistry() = default;
  std::vector<std::unique_ptr<Sensor>> sensors_;
};

// Helper for static-init self-registration. Drop into any sensor's .cpp:
//   static orchard::sensors::AutoRegister<MyDriver> _my_driver_reg;
template <typename T>
struct AutoRegister {
  AutoRegister() {
    SensorRegistry::instance().add(std::make_unique<T>());
  }
};

}  // namespace orchard::sensors
