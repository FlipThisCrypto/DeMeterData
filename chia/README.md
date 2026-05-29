# chia/ — Chia integration

All Chia-blockchain-touching code: DataLayer attestation writer (Phase 5, ✅ implemented), wallet RPC client (Phase 7), manual **$JUICE** CAT payout script (Phase 7). Targets the **official Chia reference wallet** RPC (default port 9256).

> **Vocabulary:** the code uses `season`/`node`/`attest`. User-facing copy says **Season / Tree / Attestation**. See the [Glossary](../README.md#glossary).

## Why this is its own component

Isolating blockchain-specific code makes it easy to upgrade or replace as the Chia ecosystem evolves (e.g., swapping the reference wallet for Sage, or upgrading from manual payouts to a Chialisp claim contract). Each module here talks to one Chia surface and exposes a small Python API the rest of the project can call.

## Layout

```
chia/
├── README.md
├── requirements.txt          # requests, pydantic, pyyaml, pytest
├── config.example.yaml       # copy to config.yaml, fill in, never commit
├── data/                     # gitignored — local state (signing key, etc.)
├── datalayer/                # Phase 5 — Season attestation writer  ✅
│   ├── __main__.py           # `python -m chia.datalayer`
│   ├── main.py               # orchestrator
│   ├── config.py             # YAML loader
│   ├── oracle.py             # HTTP client to the oracle
│   ├── rpc.py                # TLS-wrapped Chia full-node + DataLayer clients
│   └── attest.py             # pure functions: build, sign, serialize
├── wallet/                   # Phase 7 — wallet RPC wrapper (stub)
├── payout/                   # Phase 7 — $JUICE batched payout (stub)
└── tests/
    └── test_datalayer.py     # 9 hermetic tests for the attest pure-functions
```

## Phase 5 — Season attestation writer

Reads each registered Tree's per-Season uptime from the oracle and writes a signed attestation to a Chia DataLayer store. Idempotent — re-running the writer only pushes records whose value changed.

### Attestation record (the value stored in DataLayer)

```json
{
  "node_id":               "5B9BB022649FA93D4091DA4BA40714B9",
  "season":                2,
  "season_start_utc":      "2026-05-28T00:00:00+00:00",
  "season_end_utc":        "2026-05-29T00:00:00+00:00",
  "hours_online":          18,
  "block_height_at_write": 8392104,
  "data_hash":             "<sha256 hex>",
  "signed_at":             "2026-05-29T00:01:42.123456+00:00",
  "oracle_sig":            "<HMAC-SHA256 hex>"
}
```

- Key in DataLayer: hex-encoded UTF-8 of `attest:<NODE_ID>:<SEASON:08d>` (e.g. `attest:5B9BB022649FA93D4091DA4BA40714B9:00000002`).
- Value: hex-encoded UTF-8 of canonical JSON (sorted keys, no whitespace).
- Signature scheme: HMAC-SHA256 with the oracle's per-instance secret (see "Signing key" below).

In v1, `data_hash` is a placeholder hash over `(node_id, season, hours_online)`. v1.1 will swap it for a Merkle root over the per-hour reading buckets, so a Keeper-class validator can request the raw data and re-verify.

### Quick start

```powershell
# 1. install deps (same .venv as oracle / dashboard is fine)
pip install -r chia/requirements.txt

# 2. copy + edit config
copy chia\config.example.yaml chia\config.yaml
# edit chia\config.yaml — update SSL cert paths, set datalayer.store_id

# 3. (one-time) create a DataLayer store and paste its id into config.yaml
chia data create_data_store -m 0.0001
# -> { "id": "<32-byte hex>", ... }

# 4. run the writer (operates on whatever closed Seasons the oracle has)
python -m chia.datalayer
```

Typical schedule: hourly via Windows Task Scheduler / cron. Daily is also fine; the writer is cheap when there's nothing to do.

### What the writer does, step by step

1. Load `chia/config.yaml` and the per-oracle signing key (auto-generated on first run; lives at `chia/data/oracle_signing_key.hex`, gitignored).
2. Hit the oracle: `GET /` to find `current_season`, `GET /nodes` for the Tree list, `GET /uptime/{node}/{season}` for each closed Season.
3. Hit the Chia full node: read `peak_height` so each attestation records the block height it was written at.
4. For each `(node, season)` with non-zero uptime: build the payload, sign it, hex-encode key+value.
5. Skip records whose existing DataLayer value already matches what we'd write (idempotency check via `get_value`).
6. Submit the remaining inserts/replaces as a single `batch_update` to DataLayer.

### Signing key

- 32 bytes of `secrets.token_hex()` generated on the writer's first run.
- Persisted at `chia/data/oracle_signing_key.hex` (gitignored).
- Never transmitted over the network.
- The same key signs every attestation this oracle ever publishes. If you nuke the file and re-run, all subsequent attestations get a new key — previously-published attestations remain verifiable against the old key, so save a backup if that matters to you.

### Test it

```powershell
pytest chia/tests/
```

9 hermetic tests cover: payload shape, sign+verify round-trip, tamper detection, wrong-key rejection, DataLayer key/value determinism, parse-back, edge cases. Tests are pure-function — no network, no Chia node required.

## Wallet & Payout (Phase 7 — stubs only)

The wallet module will wrap the Chia reference wallet RPC (port 9256) for the bits the payout script needs: `get_wallets`, `cat_spend`, `push_tx`. The payout module will read attestations from DataLayer, compute `tokens = (hours_online / 24) * daily_rate` per `(node, season)`, aggregate per wallet, build a single $JUICE CAT spend bundle, output it for review, and submit via `push_tx`.

## Status

| Phase | Module | Status |
|-------|--------|--------|
| 5     | `chia/datalayer/` | ✅ Implemented + tested |
| 6     | `nft/`           | ⬜ Not started |
| 7     | `chia/wallet/`, `chia/payout/` | ⬜ Not started |
