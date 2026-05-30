# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for Orchard View.

We don't actually open a serial port or talk to a real oracle —
both modules are monkeypatched in the fixture so the tests run
hermetically (and quickly).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dashboard.app import config as dash_config
from dashboard.app import oracle_client, tree_serial
from dashboard.app.main import create_app


@pytest.fixture()
def client(monkeypatch):
    dash_config.reset_settings_for_tests()
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c
    dash_config.reset_settings_for_tests()


@pytest.fixture()
def public_client(monkeypatch):
    """Same as `client`, but with public_mode=True so operator-only
    routes (provision, serial, oracle/register) get gated to 404."""
    monkeypatch.setenv("ORCHARD_VIEW_PUBLIC_MODE", "1")
    dash_config.reset_settings_for_tests()
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c
    dash_config.reset_settings_for_tests()


def test_index_with_oracle_down(client, monkeypatch):
    def boom():
        raise oracle_client.OracleError("connection refused")
    monkeypatch.setattr(oracle_client, "root", boom)
    monkeypatch.setattr(oracle_client, "list_nodes", lambda: [])
    r = client.get("/")
    assert r.status_code == 200
    assert b"Oracle unreachable" in r.data


def test_index_with_oracle_up_no_nodes(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "root", lambda: {"version": "0.1.0", "current_season": 1, "now_utc": "2026-05-27T20:00:00+00:00"})
    monkeypatch.setattr(oracle_client, "list_nodes", lambda: [])
    r = client.get("/")
    assert r.status_code == 200
    assert b"Plant your first Tree" in r.data


def test_provision_page(client):
    r = client.get("/provision")
    assert r.status_code == 200
    assert b"Plant a Tree" in r.data
    assert b"Identify Tree" in r.data


def test_tree_page_unknown_node(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "get_node", lambda node_id: None)
    r = client.get("/tree/ABCDEF0123456789ABCDEF0123456789")
    assert r.status_code == 404


def test_tree_page_known_node(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "get_node", lambda node_id: {
        "node_id": node_id, "label": "test-tree", "fw_version": "0.1.0",
        "registered_at": "2026-05-27T20:00:00+00:00",
        "last_seen_at": None, "last_reading_at": None, "wallet_address": None,
    })
    r = client.get("/tree/ABCDEF0123456789ABCDEF0123456789")
    assert r.status_code == 200
    assert b"test-tree" in r.data


def test_api_oracle_status(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "root", lambda: {"service": "the-orchard-oracle", "current_season": 7})
    r = client.get("/api/oracle/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["oracle"]["current_season"] == 7


def test_api_serial_ports(client, monkeypatch):
    monkeypatch.setattr(tree_serial, "list_ports", lambda: [
        tree_serial.PortInfo(device="COM4", description="USB Serial", hwid="VID:PID"),
    ])
    r = client.get("/api/serial/ports")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["ports"][0]["device"] == "COM4"


def test_api_serial_identify_missing_port(client):
    r = client.post("/api/serial/identify", json={})
    assert r.status_code == 400


def test_api_serial_identify_happy(client, monkeypatch):
    monkeypatch.setattr(tree_serial, "ping", lambda port: True)
    monkeypatch.setattr(tree_serial, "get_node_id", lambda port: "5B9BB022649FA93D4091DA4BA40714B9")
    monkeypatch.setattr(tree_serial, "get_signing_key", lambda port: "AA" * 32)
    monkeypatch.setattr(tree_serial, "get_status", lambda port: {"fw": "0.1.0", "wifi": "unconfigured", "oracle": ""})
    r = client.post("/api/serial/identify", json={"port": "COM4"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["node_id"] == "5B9BB022649FA93D4091DA4BA40714B9"
    assert body["status"]["fw"] == "0.1.0"


def test_api_oracle_register_passthrough(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "register_node", lambda **kw: {"node_id": kw["node_id"], "new": True})
    r = client.post("/api/oracle/register", json={
        "node_id": "0123456789ABCDEF0123456789ABCDEF",
        "signing_key_hex": "AA" * 32,
        "label": "tree-A",
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["register"]["new"] is True


def test_api_tree_latest_unknown(client, monkeypatch):
    monkeypatch.setattr(oracle_client, "get_node", lambda node_id: None)
    r = client.get("/api/tree/ABCDEF01/latest")
    assert r.status_code == 404


# ---------------- public mode ----------------

def test_public_mode_hides_plant_a_tree_in_nav(public_client, monkeypatch):
    """The nav link disappears so visitors don't see provisioning."""
    monkeypatch.setattr(oracle_client, "root", lambda: {"version": "0.1.0", "current_season": 1, "now_utc": "2026-05-27T20:00:00+00:00"})
    monkeypatch.setattr(oracle_client, "list_nodes", lambda: [])
    r = public_client.get("/")
    assert r.status_code == 200
    # The "Plant a Tree" CTA button is rendered inside the page body
    # when there are no nodes — it's an empty-state prompt — but the
    # nav-bar link is conditional. We check that the nav link doesn't
    # appear by looking for it inside the <nav> only. Simplest proxy:
    # the page rendered, but it should not contain the provision URL
    # twice (button + nav). In public mode the body's empty-state
    # button is still there but the nav link is suppressed.
    assert r.data.count(b'href="/provision"') <= 1


def test_public_mode_blocks_provision_page(public_client):
    r = public_client.get("/provision")
    assert r.status_code == 404


def test_public_mode_blocks_oracle_register(public_client):
    r = public_client.post("/api/oracle/register", json={
        "node_id": "0123456789ABCDEF0123456789ABCDEF",
        "signing_key_hex": "AA" * 32,
    })
    assert r.status_code == 404


def test_public_mode_blocks_serial_ports(public_client):
    r = public_client.get("/api/serial/ports")
    assert r.status_code == 404


def test_public_mode_blocks_serial_identify(public_client):
    r = public_client.post("/api/serial/identify", json={"port": "COM4"})
    assert r.status_code == 404


def test_public_mode_blocks_all_serial_routes(public_client):
    for path in ["/api/serial/wifi", "/api/serial/oracle", "/api/serial/sample"]:
        r = public_client.post(path, json={"port": "COM4"})
        assert r.status_code == 404, f"expected {path} to 404 in public mode"


def test_public_mode_still_serves_index_and_tree(public_client, monkeypatch):
    """Read-only endpoints must keep working — they're the whole point
    of public mode."""
    monkeypatch.setattr(oracle_client, "root", lambda: {"version": "0.1.0", "current_season": 1, "now_utc": "2026-05-27T20:00:00+00:00"})
    monkeypatch.setattr(oracle_client, "list_nodes", lambda: [])
    r = public_client.get("/")
    assert r.status_code == 200

    monkeypatch.setattr(oracle_client, "get_node", lambda node_id: {
        "node_id": node_id, "label": "demo-tree", "fw_version": "0.1.0",
        "registered_at": "2026-05-27T20:00:00+00:00",
        "last_seen_at": None, "last_reading_at": None, "wallet_address": None,
    })
    r = public_client.get("/tree/ABCDEF0123456789ABCDEF0123456789")
    assert r.status_code == 200


def test_public_mode_oracle_status_still_works(public_client, monkeypatch):
    monkeypatch.setattr(oracle_client, "root", lambda: {"current_season": 7})
    r = public_client.get("/api/oracle/status")
    assert r.status_code == 200
    assert r.get_json()["oracle"]["current_season"] == 7


# ----- public mode response scrubbing (U1 + U2) ---------------------

_DOXX_WALLET = "xch1m3rvtj86wzzfjyk5mc7wzpr7h4zkaknm4wte7kg6afleu4f2tfxsr7nk3n"
_PRECISE_LAT = 38.054321  # 6 decimals — ~10 cm precision
_PRECISE_LON = -85.527834


def _node_with_secrets(node_id: str) -> dict:
    return {
        "node_id": node_id,
        "label": "backyard-1",
        "fw_version": "0.1.0",
        "wallet_address": _DOXX_WALLET,
        "registered_at": "2026-05-27T20:00:00+00:00",
        "last_seen_at": "2026-05-30T20:00:00+00:00",
        "last_reading_at": "2026-05-30T20:00:00+00:00",
    }


def _reading_with_gps() -> dict:
    return {
        "id": 1,
        "node_id": "ABCDEF0123456789ABCDEF0123456789",
        "received_at": "2026-05-30T20:00:00+00:00",
        "tree_ts_ms": 1234567,
        "fw_version": "0.1.0",
        "gps_lat": _PRECISE_LAT,
        "gps_lon": _PRECISE_LON,
        "gps_fix": True,
        "payload": {
            "sensors": {
                "mq135": {"adc_raw": 1234},
                "gps":   {"lat": _PRECISE_LAT, "lon": _PRECISE_LON, "fix": True},
            },
        },
    }


def test_public_mode_strips_wallet_address(public_client, monkeypatch):
    monkeypatch.setattr(oracle_client, "get_node",
                        lambda nid: _node_with_secrets(nid))
    monkeypatch.setattr(oracle_client, "list_readings",
                        lambda nid, limit: [_reading_with_gps()])
    monkeypatch.setattr(oracle_client, "root", lambda: {"current_season": 1})
    monkeypatch.setattr(oracle_client, "get_uptime",
                        lambda nid, season: {"hours": 1})

    r = public_client.get("/api/tree/ABCDEF0123456789ABCDEF0123456789/latest")
    assert r.status_code == 200
    body = r.get_json()
    # node must not include wallet_address.
    assert "wallet_address" not in body["node"]
    # raw payload of /latest must not include the literal address anywhere.
    assert _DOXX_WALLET not in r.get_data(as_text=True)


def test_public_mode_coarsens_gps_in_readings(public_client, monkeypatch):
    monkeypatch.setattr(oracle_client, "get_node",
                        lambda nid: _node_with_secrets(nid))
    monkeypatch.setattr(oracle_client, "list_readings",
                        lambda nid, limit: [_reading_with_gps()])
    monkeypatch.setattr(oracle_client, "root", lambda: {"current_season": 1})
    monkeypatch.setattr(oracle_client, "get_uptime",
                        lambda nid, season: None)

    r = public_client.get("/api/tree/ABCDEF0123456789ABCDEF0123456789/latest")
    assert r.status_code == 200
    body = r.get_json()
    reading = body["readings"][0]
    # Top-level GPS coarsened to 3 decimals (~111m).
    assert reading["gps_lat"] == round(_PRECISE_LAT, 3)
    assert reading["gps_lon"] == round(_PRECISE_LON, 3)
    # Nested payload.sensors.gps also coarsened.
    nested = reading["payload"]["sensors"]["gps"]
    assert nested["lat"] == round(_PRECISE_LAT, 3)
    assert nested["lon"] == round(_PRECISE_LON, 3)
    # "latest" mirrors readings[0] post-scrub.
    assert body["latest"]["gps_lat"] == round(_PRECISE_LAT, 3)
    # No 6-decimal coords anywhere in the raw JSON.
    assert "38.054321"  not in r.get_data(as_text=True)
    assert "-85.527834" not in r.get_data(as_text=True)


def test_private_mode_preserves_wallet_address_and_gps(client, monkeypatch):
    """Sanity: when public_mode is OFF (the operator's normal state),
    we DO want wallet_address and precise GPS to come through — that
    is the operator's own data on their own dashboard."""
    monkeypatch.setattr(oracle_client, "get_node",
                        lambda nid: _node_with_secrets(nid))
    monkeypatch.setattr(oracle_client, "list_readings",
                        lambda nid, limit: [_reading_with_gps()])
    monkeypatch.setattr(oracle_client, "root", lambda: {"current_season": 1})
    monkeypatch.setattr(oracle_client, "get_uptime",
                        lambda nid, season: None)

    r = client.get("/api/tree/ABCDEF0123456789ABCDEF0123456789/latest")
    assert r.status_code == 200
    body = r.get_json()
    assert body["node"]["wallet_address"] == _DOXX_WALLET
    assert body["readings"][0]["gps_lat"] == _PRECISE_LAT
    assert body["readings"][0]["payload"]["sensors"]["gps"]["lat"] == _PRECISE_LAT
