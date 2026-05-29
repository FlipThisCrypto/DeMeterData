// SPDX-License-Identifier: Apache-2.0
//
// USB-serial provisioning console.
//
// Line-oriented commands the Orchard View dashboard uses to set up a
// Tree before it can reach the oracle. Each command is one line, ends
// with \n, and gets a one-line `OK ...` or `ERR ...` reply.
//
// Commands (case-sensitive):
//   PING                       -> "OK pong"
//   STATUS                     -> "OK <json blob>"
//   NODE_ID                    -> "OK <hex>"
//   KEY                        -> "OK <hex 32-byte signing secret>"
//                                 (printed in plaintext over the local
//                                 USB link. NEVER over the network.)
//   WIFI_SET <ssid> <password> -> "OK" (saves and reconnects)
//   WIFI_CLEAR                 -> "OK"
//   ORACLE_SET <url>           -> "OK"
//   SAMPLE_NOW                 -> "OK" (samples sensors + POSTs now)
//   I2C_SCAN                   -> "OK 0xXX 0xYY ..."  (every responding
//                                 I2C address) or "OK (no devices)"
//   GPS_RAW                    -> "OK gps_raw_start" then 3 seconds of
//                                 raw GPS UART bytes streamed inline,
//                                 then "OK gps_raw_end"
//   REBOOT                     -> "OK rebooting"  (then reboots)
//
// Any unknown command -> "ERR unknown".

#pragma once

namespace orchard::net {

void console_begin();
void console_loop();

// Optional: callback used to trigger an immediate sample+POST from
// console (lets us avoid a circular dep between this module and main).
using SampleNowFn = void (*)();
void console_set_sample_callback(SampleNowFn fn);

}  // namespace orchard::net
