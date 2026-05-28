// SPDX-License-Identifier: Apache-2.0
#include "identity.h"

#include <Preferences.h>
#include <esp_random.h>
#include <mbedtls/md.h>

#include "config.h"

namespace orchard::identity {

namespace {

constexpr size_t kNodeIdBytes = 16;
constexpr const char* kNvsKeyNodeId = "node_id";
constexpr const char* kNvsKeySecret = "sign_key";

uint8_t signing_secret_[kSigningSecretLen] = {0};
String node_id_hex_;

void random_bytes(uint8_t* out, size_t len) {
  // esp_random() is hardware-backed when WiFi/BT is active. Before that,
  // it falls back to a deterministic PRNG. Mixing in micros() helps the
  // very-first-boot case.
  for (size_t i = 0; i < len; i += 4) {
    const uint32_t r = esp_random() ^ static_cast<uint32_t>(micros());
    const size_t chunk = (len - i >= 4) ? 4 : (len - i);
    memcpy(out + i, &r, chunk);
  }
}

}  // namespace

String to_hex(const uint8_t* buf, size_t len) {
  static const char* kHex = "0123456789ABCDEF";
  String s;
  s.reserve(len * 2);
  for (size_t i = 0; i < len; ++i) {
    s += kHex[(buf[i] >> 4) & 0x0f];
    s += kHex[buf[i] & 0x0f];
  }
  return s;
}

void begin() {
  Preferences prefs;
  prefs.begin(ORCHARD_NVS_NAMESPACE, /*readOnly=*/false);

  // --- node id ---
  uint8_t node_id_buf[kNodeIdBytes] = {0};
  size_t read = prefs.getBytes(kNvsKeyNodeId, node_id_buf, kNodeIdBytes);
  if (read != kNodeIdBytes) {
    random_bytes(node_id_buf, kNodeIdBytes);
    prefs.putBytes(kNvsKeyNodeId, node_id_buf, kNodeIdBytes);
    Serial.println("[identity] generated new node id");
  }
  node_id_hex_ = to_hex(node_id_buf, kNodeIdBytes);

  // --- signing secret ---
  read = prefs.getBytes(kNvsKeySecret, signing_secret_, kSigningSecretLen);
  if (read != kSigningSecretLen) {
    random_bytes(signing_secret_, kSigningSecretLen);
    prefs.putBytes(kNvsKeySecret, signing_secret_, kSigningSecretLen);
    Serial.println("[identity] generated new signing secret");
  }

  prefs.end();

  Serial.printf("[identity] node_id=%s\n", node_id_hex_.c_str());
}

const String& node_id_hex() {
  return node_id_hex_;
}

const uint8_t* signing_secret() {
  return signing_secret_;
}

void hmac_sha256(const uint8_t* data, size_t len, uint8_t out[32]) {
  const mbedtls_md_info_t* md =
      mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_hmac(md,
                  signing_secret_, kSigningSecretLen,
                  data, len,
                  out);
}

}  // namespace orchard::identity
