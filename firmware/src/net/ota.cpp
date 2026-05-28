// SPDX-License-Identifier: Apache-2.0
#include "ota.h"

#include <Arduino.h>
#include <Update.h>
#include <WebServer.h>
#include <WiFi.h>

#include "config.h"
#include "identity.h"
#include "version.h"

namespace orchard::net {

namespace {

WebServer server_(ORCHARD_DEVICE_HTTP_PORT);
bool started_ = false;

void handle_health_() {
  String body;
  body.reserve(192);
  body += "{\"node_id\":\"";
  body += identity::node_id_hex();
  body += "\",\"fw\":\"";
  body += orchard::kFirmwareVersion;
  body += "\",\"uptime_ms\":";
  body += millis();
  body += "}";
  server_.send(200, "application/json", body);
}

void handle_ota_upload_() {
  HTTPUpload& upload = server_.upload();
  if (upload.status == UPLOAD_FILE_START) {
    Serial.printf("[ota] starting update, name=%s\n", upload.filename.c_str());
    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
      Update.printError(Serial);
    }
  } else if (upload.status == UPLOAD_FILE_WRITE) {
    if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
      Update.printError(Serial);
    }
  } else if (upload.status == UPLOAD_FILE_END) {
    if (Update.end(/*evenIfRemaining=*/true)) {
      Serial.printf("[ota] update OK, %u bytes\n", upload.totalSize);
    } else {
      Update.printError(Serial);
    }
  }
}

void handle_ota_done_() {
  if (Update.hasError()) {
    server_.send(500, "text/plain", "OTA failed");
  } else {
    server_.send(200, "text/plain", "OK; rebooting");
    delay(500);
    ESP.restart();
  }
}

}  // namespace

void ota_begin() {
  if (started_) return;
  server_.on("/health", HTTP_GET, handle_health_);
  server_.on("/ota", HTTP_POST, handle_ota_done_, handle_ota_upload_);
  server_.begin();
  started_ = true;
  Serial.printf("[ota] http server listening on :%d\n",
                ORCHARD_DEVICE_HTTP_PORT);
}

void ota_loop() {
  if (!started_) {
    if (WiFi.status() == WL_CONNECTED) ota_begin();
    return;
  }
  server_.handleClient();
}

}  // namespace orchard::net
