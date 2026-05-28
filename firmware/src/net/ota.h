// SPDX-License-Identifier: Apache-2.0
//
// HTTP-driven OTA endpoint.
//
// Listens on `ORCHARD_DEVICE_HTTP_PORT` and exposes:
//   GET  /health   -> small JSON with node_id, fw version, uptime
//   POST /ota      -> binary firmware upload (Update API), then reboot
//
// The dashboard pushes new firmware here. There is intentionally no
// authentication on /ota in v1 — the dashboard talks to it on the LAN
// only. Do NOT expose this port to the open internet.

#pragma once

namespace orchard::net {

void ota_begin();
void ota_loop();  // call from main loop()

}  // namespace orchard::net
