# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the oracle.

Verifies the end-to-end happy path (register -> sign -> POST -> retrieve)
plus the key failure cases (no sig, bad sig, unknown node).

Tests run against an in-memory SQLite DB via a FastAPI dependency
override; nothing touches the real oracle/data/orchard.db.
"""
from __future__ import annotations

import hmac
import json
import os
from hashlib import sha256

# Force a fresh in-memory DB BEFORE importing the app so settings()
# doesn't latch in a file-backed URL from the env.
os.environ["ORCHARD_ORACLE_DB_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from oracle.app.config import reset_settings_for_tests
from oracle.app.db import Base, get_db, reset_for_tests
from oracle.app.main import app

NODE_ID = "0123456789ABCDEF0123456789ABCDEF"
KEY_HEX = "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"


@pytest.fixture()
def client(monkeypatch):
    reset_settings_for_tests()
    reset_for_tests()

    # StaticPool keeps a single connection alive so all sessions see the
    # same in-memory DB (without it, each connection gets its own empty DB).
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _sign(body: bytes) -> str:
    secret = bytes.fromhex(KEY_HEX)
    return hmac.new(secret, body, sha256).hexdigest().upper()


def test_root_identifies_service(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "the-orchard-oracle"
    assert "current_season" in body


def test_register_then_list(client: TestClient):
    r = client.post(
        "/register",
        json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX, "label": "tree-A"},
    )
    assert r.status_code == 201
    assert r.json()["new"] is True

    # Re-register same node + same key is idempotent (200ish, new=False).
    r2 = client.post(
        "/register",
        json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX, "label": "tree-A-renamed"},
    )
    assert r2.status_code == 201
    assert r2.json()["new"] is False

    # Different key on same node_id => 409 conflict.
    r3 = client.post(
        "/register",
        json={"node_id": NODE_ID, "signing_key_hex": "FF" * 32, "label": "imposter"},
    )
    assert r3.status_code == 409

    listing = client.get("/nodes")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["node_id"] == NODE_ID


def test_post_reading_unknown_node(client: TestClient):
    body = json.dumps({"sensors": {}}).encode("utf-8")
    r = client.post(
        "/readings",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Orchard-Node": NODE_ID,
            "X-Orchard-Sig": _sign(body),
        },
    )
    assert r.status_code == 404


def test_post_reading_bad_signature(client: TestClient):
    # Register the Tree first.
    client.post("/register", json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX})

    body = json.dumps({"sensors": {}}).encode("utf-8")
    r = client.post(
        "/readings",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Orchard-Node": NODE_ID,
            "X-Orchard-Sig": "00" * 32,  # wrong
        },
    )
    assert r.status_code == 401


def test_post_reading_happy_path_and_retrieve(client: TestClient):
    client.post("/register", json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX})

    payload = {
        "node_id": NODE_ID,
        "fw": "0.1.0",
        "ts_ms": 12345,
        "sensors": {
            "mq135": {"adc_raw": 1820.0, "voltage_v": 1.46},
            "gps": {"fix": True, "lat": 38.0046, "lon": -85.7374, "satellites": 7},
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    r = client.post(
        "/readings",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Orchard-Node": NODE_ID,
            "X-Orchard-Sig": _sign(body),
        },
    )
    assert r.status_code == 202, r.text
    assert r.json()["id"] >= 1

    # Reading retrievable.
    r2 = client.get(f"/readings/{NODE_ID}")
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["fw_version"] == "0.1.0"
    assert rows[0]["gps_lat"] == pytest.approx(38.0046)
    assert rows[0]["gps_fix"] is True
    assert rows[0]["payload"]["sensors"]["mq135"]["adc_raw"] == 1820.0

    # Uptime bucket incremented.
    season = client.get("/").json()["current_season"]
    r3 = client.get(f"/uptime/{NODE_ID}/{season}")
    assert r3.status_code == 200
    assert r3.json()["hours_online"] == 1
    assert len(r3.json()["hour_buckets"]) == 1


def test_uptime_for_unknown_node(client: TestClient):
    r = client.get(f"/uptime/{NODE_ID}/1")
    assert r.status_code == 404
