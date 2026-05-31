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


# ---------------- Phase 6.5: Orchard Pass gating ----------------

# Real-looking values pulled from the on-chain Genesis collection so
# anyone reading these tests can see them on MintGarden if they want
# to cross-reference.
PASS_OWNER_ADDR = "xch1m3rvtj86wzzfjyk5mc7wzpr7h4zkaknm4wte7kg6afleu4f2tfxsr7nk3n"
PASS_OWNER_NFT_BECH32 = "nft1n00ugdl737xc6ht4yjdc3cer047lcz9actdxfzpxyat3tsu72z0q46g56z"
NON_OWNER_ADDR = "xch1nobody00000000000000000000000000000000000000000000000000zz0t"


@pytest.fixture()
def fake_indexer(monkeypatch):
    """Stub the on-chain Pass-ownership lookup with a controllable
    in-memory fake. Lets us exercise the /register Pass gate without a
    real MintGarden round-trip — tests stay hermetic.
    """
    from oracle.app import pass_verify
    pass_verify.clear_cache()

    state = {
        PASS_OWNER_ADDR: [{
            "nft_coin_id":    PASS_OWNER_NFT_BECH32,
            "launcher_id":    "f" * 64,
            "name":           "Orchard Pass #0001",
            "edition_number": 1,
            "owner_address":  PASS_OWNER_ADDR,
        }],
        NON_OWNER_ADDR: [],
    }
    err = {"raise": None}

    def fake_list(address: str):
        if err["raise"] is not None:
            from orchard_chia.nft.verify import IndexerError
            raise IndexerError(err["raise"])
        return list(state.get(address, []))

    monkeypatch.setattr(
        "orchard_chia.nft.verify.list_passes_by_address", fake_list)

    yield {
        "state":     state,
        "fail_with": lambda msg: err.__setitem__("raise", msg),
        "succeed":   lambda: err.__setitem__("raise", None),
    }

    pass_verify.clear_cache()


def test_register_without_wallet_skips_pass_gate(client: TestClient, fake_indexer):
    """Legacy registration without a wallet still works and leaves the
    Pass binding null — backward compatible with pre-6.5 nodes."""
    r = client.post(
        "/register",
        json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX, "label": "legacy"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["new"] is True
    assert body["pass_nft_id"] is None
    assert body["pass_verified_at"] is None


def test_register_with_pass_holder_wallet_binds_nft(client: TestClient, fake_indexer):
    """Valid wallet holding a Pass: registration succeeds and the
    bech32 nft_id is bound to the Tree."""
    r = client.post(
        "/register",
        json={
            "node_id":        NODE_ID,
            "signing_key_hex": KEY_HEX,
            "wallet_address": PASS_OWNER_ADDR,
            "label":          "operator-1",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["new"] is True
    assert body["pass_nft_id"] == PASS_OWNER_NFT_BECH32
    assert body["pass_verified_at"] is not None

    # GET /nodes/<id> surfaces the binding.
    r2 = client.get(f"/nodes/{NODE_ID}")
    assert r2.status_code == 200
    assert r2.json()["pass_nft_id"] == PASS_OWNER_NFT_BECH32


def test_register_with_non_holder_wallet_returns_403(client: TestClient, fake_indexer):
    """Wallet that doesn't hold a Pass: registration rejected with 403.
    No partial node row left behind."""
    r = client.post(
        "/register",
        json={
            "node_id":        NODE_ID,
            "signing_key_hex": KEY_HEX,
            "wallet_address": NON_OWNER_ADDR,
        },
    )
    assert r.status_code == 403
    assert "does not hold an Orchard Pass" in r.json()["detail"]

    # No node was created.
    assert client.get(f"/nodes/{NODE_ID}").status_code == 404
    assert client.get("/nodes").json() == []


def test_register_with_malformed_wallet_returns_422(client: TestClient, fake_indexer):
    """Pydantic validator rejects bad xch1 syntax before we ever
    touch the indexer."""
    r = client.post(
        "/register",
        json={
            "node_id":        NODE_ID,
            "signing_key_hex": KEY_HEX,
            "wallet_address": "not-an-xch-address",
        },
    )
    assert r.status_code == 422


def test_register_with_indexer_down_returns_503(client: TestClient, fake_indexer):
    """Indexer error -> 503 Service Unavailable. We refuse to register
    without proof when proof was requested; operator should retry."""
    fake_indexer["fail_with"]("MintGarden 500: bad gateway")
    r = client.post(
        "/register",
        json={
            "node_id":        NODE_ID,
            "signing_key_hex": KEY_HEX,
            "wallet_address": PASS_OWNER_ADDR,
        },
    )
    assert r.status_code == 503
    assert "indexer error" in r.json()["detail"]
    assert client.get(f"/nodes/{NODE_ID}").status_code == 404


def test_reregister_changing_wallet_rebinds_pass(client: TestClient, fake_indexer):
    """Operator initially registered without a wallet, later attaches
    one. Re-register updates wallet_address and binds the Pass."""
    # First register: no wallet.
    client.post(
        "/register",
        json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX},
    )
    # Re-register with the Pass-holding wallet.
    r = client.post(
        "/register",
        json={
            "node_id":        NODE_ID,
            "signing_key_hex": KEY_HEX,
            "wallet_address": PASS_OWNER_ADDR,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["new"] is False
    assert body["pass_nft_id"] == PASS_OWNER_NFT_BECH32


def test_pass_verify_cache_hit(client: TestClient, fake_indexer, monkeypatch):
    """The cache prevents a flapping operator from generating one
    MintGarden call per retry within the TTL window."""
    from oracle.app import pass_verify
    pass_verify.clear_cache()

    calls = {"n": 0}
    original = pass_verify.nft_verify.list_passes_by_address

    def counting(address: str):
        calls["n"] += 1
        return original(address)

    monkeypatch.setattr(
        "orchard_chia.nft.verify.list_passes_by_address", counting)

    # Two registrations of two different nodes from the same wallet.
    for nid in [NODE_ID, "FEDCBA9876543210FEDCBA9876543210"]:
        r = client.post(
            "/register",
            json={
                "node_id":        nid,
                "signing_key_hex": KEY_HEX,
                "wallet_address": PASS_OWNER_ADDR,
            },
        )
        assert r.status_code == 201, r.text
    # Cache hit on the second call.
    assert calls["n"] == 1


# ---------------- Phase 5.5: chain attestation tracking ----------------

def test_record_attestation_unknown_node_404(client: TestClient):
    """POST /attestations rejects unknown node_id to prevent orphan rows."""
    r = client.post("/attestations", json={
        "node_id": "DEADBEEFDEADBEEFDEADBEEFDEADBEEF0",
        "season_number": 2,
        "hours_online": 24,
        "data_hash": "a" * 64,
        "oracle_sig": "b" * 64,
        "dl_tx_id":   "0x" + "c" * 64,
        "dl_key_hex": "61747465737400000",
    })
    assert r.status_code == 404


def test_record_attestation_happy_then_idempotent(client: TestClient):
    """First POST creates, second POST for same (node, season) updates."""
    # Need a node first.
    client.post("/register",
                json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX})

    body = {
        "node_id":               NODE_ID,
        "season_number":         3,
        "hours_online":          24,
        "data_hash":             "a" * 64,
        "oracle_sig":            "b" * 64,
        "dl_tx_id":              "0x" + "c" * 64,
        "dl_key_hex":            "61747465737400000",
        "block_height_at_write": 8804917,
    }
    r1 = client.post("/attestations", json=body)
    assert r1.status_code == 201, r1.text
    j1 = r1.json()
    assert j1["season_number"] == 3
    assert j1["dl_tx_id"] == body["dl_tx_id"]
    assert j1["hours_online"] == 24

    # Re-post with new tx_id (re-run scenario) — same row, updated chain pointer.
    body["dl_tx_id"] = "0x" + "d" * 64
    r2 = client.post("/attestations", json=body)
    assert r2.status_code == 201
    j2 = r2.json()
    assert j2["dl_tx_id"] == body["dl_tx_id"]
    # Idempotency: only ONE row exists for (node, season), not two.
    rAll = client.get(f"/attestations/{NODE_ID}")
    assert rAll.status_code == 200
    assert len([row for row in rAll.json() if row["season_number"] == 3]) == 1

    # GET /attestations/<id>/latest returns it.
    rL = client.get(f"/attestations/{NODE_ID}/latest")
    assert rL.status_code == 200
    assert rL.json()["season_number"] == 3


def test_latest_attestation_none_when_empty(client: TestClient):
    """A registered node with no attestations yet returns null."""
    client.post("/register",
                json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX})
    r = client.get(f"/attestations/{NODE_ID}/latest")
    assert r.status_code == 200
    assert r.json() is None


def test_list_attestations_newest_first(client: TestClient):
    client.post("/register",
                json={"node_id": NODE_ID, "signing_key_hex": KEY_HEX})
    for s in [2, 5, 3, 4]:
        client.post("/attestations", json={
            "node_id":      NODE_ID,
            "season_number": s,
            "hours_online":  24,
            "data_hash":     "a" * 64,
            "oracle_sig":    "b" * 64,
            "dl_tx_id":      "0x" + f"{s:064d}",
            "dl_key_hex":    f"00{s:04d}",
        })
    r = client.get(f"/attestations/{NODE_ID}")
    assert r.status_code == 200
    rows = r.json()
    assert [row["season_number"] for row in rows] == [5, 4, 3, 2]
