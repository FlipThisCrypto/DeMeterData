// SPDX-License-Identifier: Apache-2.0
#include "gps_neo.h"

#include <Arduino.h>
#include <HardwareSerial.h>
#include "config.h"
#include "pins.h"

namespace orchard::sensors {

// We claim UART1 for the GPS. UART0 stays free for USB-CDC console;
// UART2 is reserved for PMS5003 later.
static HardwareSerial gps_uart(1);

bool GpsNeoSensor::begin() {
  gps_uart.begin(ORCHARD_GPS_BAUD,
                 SERIAL_8N1,
                 ORCHARD_PIN_GPS_RX,
                 ORCHARD_PIN_GPS_TX);
  // No way to definitively probe the GPS at begin() — return true and
  // let the application decide if a sat fix is required. The dashboard
  // surfaces fix status from the sample data.
  return true;
}

void GpsNeoSensor::pump_uart_() {
  while (gps_uart.available()) {
    gps_.encode(gps_uart.read());
  }
}

bool GpsNeoSensor::read(JsonObject out) {
  pump_uart_();

  // Always report sat count and fix flag, even without a fix.
  out["satellites"]  = gps_.satellites.isValid() ? gps_.satellites.value() : 0;
  out["fix"]         = gps_.location.isValid();
  out["fix_age_ms"]  = gps_.location.isValid() ? gps_.location.age() : 0;

  if (gps_.location.isValid()) {
    out["lat"] = gps_.location.lat();
    out["lon"] = gps_.location.lng();
  }
  if (gps_.altitude.isValid()) {
    out["alt_m"] = gps_.altitude.meters();
  }
  if (gps_.speed.isValid()) {
    out["speed_kmh"] = gps_.speed.kmph();
  }
  if (gps_.date.isValid() && gps_.time.isValid()) {
    char iso[32];
    snprintf(iso, sizeof(iso),
             "%04d-%02d-%02dT%02d:%02d:%02dZ",
             gps_.date.year(),
             gps_.date.month(),
             gps_.date.day(),
             gps_.time.hour(),
             gps_.time.minute(),
             gps_.time.second());
    out["utc"] = iso;
  }
  return true;
}

}  // namespace orchard::sensors

// Self-register.
static orchard::sensors::AutoRegister<orchard::sensors::GpsNeoSensor>
    _gps_register;
