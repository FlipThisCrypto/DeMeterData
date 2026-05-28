# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for Orchard View.

We don't actually open a serial port or talk to a real oracle —
both modules are monkeypatched in the fixture so the tests run
hermetically (and quickly).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dashboard.app import oracle_client, tree_serial
from dashboard.app.main import create_app


@pytest.fixture()
def client(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


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
