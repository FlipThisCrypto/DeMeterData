// SPDX-License-Identifier: Apache-2.0
#pragma once

// ORCHARD_FIRMWARE_VERSION is injected by platformio.ini at build time.
// Fall back to "dev" if someone builds without it.
#ifndef ORCHARD_FIRMWARE_VERSION
#define ORCHARD_FIRMWARE_VERSION "dev"
#endif

namespace orchard {
constexpr const char* kFirmwareVersion = ORCHARD_FIRMWARE_VERSION;
}  // namespace orchard
