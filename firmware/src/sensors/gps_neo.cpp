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

// Baud rates to try in order. 9600 first (u-blox factory default for
// every NEO-6M/7M/8M I've seen direct from u-blox), then 38400 (the
// common HiLetgo / clone preconfigure), then the rest. NEO-M8 series
// can ship at 115200; very old or repurposed boards at 4800.
namespace {
constexpr uint32_t kCommonBauds[] = {9600, 38400, 19200, 57600, 115200, 4800};
constexpr size_t kCommonBaudCount =
    sizeof(kCommonBauds) / sizeof(kCommonBauds[0]);

// Per-rate listen window. NEO modules emit one full sentence cycle
// (GGA/GSA/GSV/RMC/VTG) per second by default, so ~1.5s is enough to
// see several `*XX\r\n` checksum frames at the right baud — and bail
// fast at the wrong baud.
constexpr uint32_t kBaudProbeMs = 1500;
}  // namespace

bool GpsNeoSensor::try_baud_(uint32_t baud) {
  gps_uart.end();
  gps_uart.begin(baud, SERIAL_8N1,
                 ORCHARD_PIN_GPS_RX, ORCHARD_PIN_GPS_TX);
  delay(50);                                  // let UART stabilize
  while (gps_uart.available()) gps_uart.read();  // drain stale buffer

  // Track delta on TinyGPS++'s passed/failed counters across THIS
  // probe — the underlying counters are cumulative across all
  // begin() attempts. A "passed checksum" sentence means the bytes
  // arrived framed correctly: `$...*XX\r\n` with the XX matching
  // the XOR of payload bytes. Valid NMEA arrives whether or not the
  // module has a satellite fix, so this baud check works on a
  // cold-started indoor module too.
  const uint32_t start_passed = gps_.passedChecksum();

  const uint32_t end_ms = millis() + kBaudProbeMs;
  while (millis() < end_ms) {
    while (gps_uart.available()) {
      gps_.encode(gps_uart.read());
    }
    delay(2);
  }
  const uint32_t got_passed = gps_.passedChecksum() - start_passed;
  Serial.printf("[gps] probe baud=%6u: passed_checksum=%u\n",
                baud, got_passed);
  // Two or more correctly-framed sentences in 1.5s = right baud.
  // (1 might be a coincidental alignment at the wrong baud.)
  return got_passed >= 2;
}

bool GpsNeoSensor::begin() {
  // Auto-detect the GPS baud rate. u-blox factory is 9600 but a lot
  // of clone modules (HiLetgo, generic AliExpress) ship preconfigured
  // for 38400 or other rates, producing garbled output at 9600. The
  // failure mode is silent + confusing for operators ("the wires are
  // right but I just see weird characters"), so we just probe.
  for (size_t i = 0; i < kCommonBaudCount; ++i) {
    if (try_baud_(kCommonBauds[i])) {
      detected_baud_ = kCommonBauds[i];
      Serial.printf("[gps] locked at %u baud\n", detected_baud_);
      return true;
    }
  }

  // Nothing produced clean NMEA. Could mean: wires disconnected, GPS
  // unpowered, GPS in UBX-binary-only mode, or just no antenna signal
  // yet (no fix is OK; *no bytes at all* is the failure we caught
  // here). Fall back to 9600 so the UART is in a sane state and any
  // future bytes get parsed. Surface that we didn't lock with
  // detected_baud_ = 0.
  gps_uart.end();
  gps_uart.begin(9600, SERIAL_8N1,
                 ORCHARD_PIN_GPS_RX, ORCHARD_PIN_GPS_TX);
  Serial.println("[gps] WARN: no clean NMEA at any tried baud rate. "
                 "Defaulting to 9600. Check wiring (TX on GPIO 18), "
                 "antenna, and that the module isn't in UBX-only mode.");
  detected_baud_ = 0;
  return true;   // keep the sensor in the registry so the GPS tile
                 // still appears in the dashboard; operator will see
                 // baud=0 and know to dig in.
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
  // Diagnostic surface — lets the dashboard tile distinguish "no fix
  // yet" (baud > 0, sentences > 0, sats > 0) from "module silent"
  // (baud == 0). Useful when an operator's first reaction to GPS not
  // working is "is my wiring right?" — the baud field answers that.
  out["baud"]                  = detected_baud_;
  out["chars_processed"]       = (uint32_t)gps_.charsProcessed();
  out["sentences_passed"]      = (uint32_t)gps_.passedChecksum();
  out["sentences_failed_csum"] = (uint32_t)gps_.failedChecksum();

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

void gps_dump_raw(uint32_t duration_ms) {
  // Drain stale bytes so we capture a fresh window.
  while (gps_uart.available()) gps_uart.read();

  const uint32_t end_ms = millis() + duration_ms;
  while (millis() < end_ms) {
    while (gps_uart.available()) {
      Serial.write((char)gps_uart.read());
    }
    delay(2);
  }
}

}  // namespace orchard::sensors

// Self-register.
static orchard::sensors::AutoRegister<orchard::sensors::GpsNeoSensor>
    _gps_register;
