// SPDX-License-Identifier: Apache-2.0
//
// Per-Tree identity: a stable node_id and a signing secret, persisted to
// NVS on first boot.
//
// v1 signing scheme: HMAC-SHA256 with a 32-byte secret shared between
// the Tree and the oracle (registered at provisioning time, never
// transmitted over the network in plaintext after registration).
//
// v2 (future): swap to ed25519. The interface below stays the same.

#pragma once

#include <Arduino.h>
#include <cstdint>

namespace orchard::identity {

// Initialize / load identity from NVS. Generates a fresh node_id and
// signing secret on first boot. Idempotent.
void begin();

// Hex-encoded node id (16 bytes -> 32 hex chars).
const String& node_id_hex();

// Raw 32-byte HMAC secret. Used by the oracle client to sign payloads.
// DO NOT print this casually — it's the device's private key.
const uint8_t* signing_secret();
constexpr size_t kSigningSecretLen = 32;

// Compute HMAC-SHA256 over `data` using the device signing secret.
// `out` must be 32 bytes.
void hmac_sha256(const uint8_t* data, size_t len, uint8_t out[32]);

// Hex-encode a buffer into a String (uppercase, no separators).
String to_hex(const uint8_t* buf, size_t len);

}  // namespace orchard::identity
