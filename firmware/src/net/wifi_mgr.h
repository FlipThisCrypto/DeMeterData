// SPDX-License-Identifier: Apache-2.0
//
// WiFi connection management.
//
// - Loads SSID + password from NVS (provisioned over USB serial).
// - Connects, reconnects on drop, exposes status.
// - If no credentials are stored, leaves WiFi off and lets the dashboard
//   push them in via the serial console.

#pragma once

#include <Arduino.h>

namespace orchard::net {

void wifi_begin();
void wifi_loop();             // call from main loop()
bool wifi_connected();
String wifi_status_string();  // for STATUS console command

// Persist new credentials and trigger a reconnect.
bool wifi_set_credentials(const String& ssid, const String& password);

// Clear stored credentials (does not disconnect — caller can REBOOT).
void wifi_clear_credentials();

}  // namespace orchard::net
