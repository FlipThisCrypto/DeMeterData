// SPDX-License-Identifier: Apache-2.0
#include "serial_console.h"

#include <Arduino.h>
#include <Wire.h>

#include "config.h"
#include "identity.h"
#include "oracle.h"
#include "sensors/gps_neo.h"
#include "version.h"
#include "wifi_mgr.h"

namespace orchard::net {

namespace {

String line_buf_;
SampleNowFn sample_cb_ = nullptr;

void cmd_status_(const String& /*args*/) {
  String s;
  s.reserve(256);
  s += "OK {\"fw\":\"";
  s += orchard::kFirmwareVersion;
  s += "\",\"node_id\":\"";
  s += identity::node_id_hex();
  s += "\",\"wifi\":\"";
  s += wifi_status_string();
  s += "\",\"oracle\":\"";
  s += oracle_url();
  s += "\",\"uptime_ms\":";
  s += millis();
  s += "}";
  Serial.println(s);
}

void cmd_wifi_set_(const String& args) {
  // Expects: <ssid> <password>
  // ssid cannot contain whitespace (use WIFI_SET_RAW later if needed).
  const int sp = args.indexOf(' ');
  if (sp <= 0) { Serial.println("ERR usage: WIFI_SET <ssid> <pass>"); return; }
  const String ssid = args.substring(0, sp);
  const String pass = args.substring(sp + 1);
  const bool ok = wifi_set_credentials(ssid, pass);
  Serial.println(ok ? "OK" : "ERR could not set");
}

void dispatch_(const String& line) {
  // Split COMMAND <args...>
  int sp = line.indexOf(' ');
  String cmd  = (sp < 0) ? line : line.substring(0, sp);
  String args = (sp < 0) ? ""   : line.substring(sp + 1);
  cmd.trim();
  args.trim();

  if (cmd == "PING") {
    Serial.println("OK pong");
  } else if (cmd == "STATUS") {
    cmd_status_(args);
  } else if (cmd == "NODE_ID") {
    Serial.print("OK ");
    Serial.println(identity::node_id_hex());
  } else if (cmd == "KEY") {
    Serial.print("OK ");
    Serial.println(
        identity::to_hex(identity::signing_secret(),
                         identity::kSigningSecretLen));
  } else if (cmd == "WIFI_SET") {
    cmd_wifi_set_(args);
  } else if (cmd == "WIFI_CLEAR") {
    wifi_clear_credentials();
    Serial.println("OK cleared");
  } else if (cmd == "ORACLE_SET") {
    if (args.length() == 0) { Serial.println("ERR usage: ORACLE_SET <url>"); return; }
    oracle_set_url(args);
    Serial.println("OK");
  } else if (cmd == "SAMPLE_NOW") {
    if (sample_cb_) {
      sample_cb_();
      Serial.println("OK sampling");
    } else {
      Serial.println("ERR no sample callback");
    }
  } else if (cmd == "I2C_SCAN") {
    // Probe addresses 1..126 on the default Wire bus. Prints every
    // address that ACKs. Operator runs this when an I2C sensor's
    // driver `begin()` returns false to figure out whether the
    // sensor is even on the bus.
    String result = "OK ";
    int count = 0;
    for (uint8_t addr = 1; addr < 127; ++addr) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        char buf[8];
        snprintf(buf, sizeof(buf), "0x%02X ", addr);
        result += buf;
        ++count;
      }
    }
    if (count == 0) result += "(no devices)";
    Serial.println(result);
  } else if (cmd == "GPS_RAW") {
    // Stream raw GPS UART bytes for 3 seconds. Operator runs this
    // when `satellites: 0` to confirm wiring at the UART level
    // (NMEA sentences arriving = wires good; silence = wires wrong,
    // GPS unpowered, or antenna unplugged).
    Serial.println("OK gps_raw_start");
    orchard::sensors::gps_dump_raw(3000);
    Serial.println("OK gps_raw_end");
  } else if (cmd == "REBOOT") {
    Serial.println("OK rebooting");
    Serial.flush();
    delay(200);
    ESP.restart();
  } else if (cmd.length() == 0) {
    // ignore empty
  } else {
    Serial.println("ERR unknown");
  }
}

}  // namespace

void console_begin() {
  Serial.begin(ORCHARD_CONSOLE_BAUD);
  delay(50);
  Serial.println();
  Serial.println("=== The Orchard — Tree firmware ===");
  Serial.printf("fw=%s node_id=%s\n",
                orchard::kFirmwareVersion,
                identity::node_id_hex().c_str());
  Serial.println("Type 'STATUS' for current state, 'PING' to test.");
}

void console_loop() {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      String l = line_buf_;
      l.trim();
      line_buf_ = "";
      if (l.length() > 0) dispatch_(l);
    } else {
      if (line_buf_.length() < 512) line_buf_ += c;
    }
  }
}

void console_set_sample_callback(SampleNowFn fn) {
  sample_cb_ = fn;
}

}  // namespace orchard::net
