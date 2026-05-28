# chia/ — Chia integration

All Chia-blockchain-touching code: DataLayer writer, wallet RPC client, manual **$JUICE** CAT payout script. Targets the **official Chia reference wallet** RPC (default port 9256).

## Why this is its own component

Isolating blockchain-specific code makes it easy to upgrade or replace as the Chia ecosystem evolves (e.g., swapping the reference wallet for Sage, or upgrading from manual payouts to a Chialisp claim contract).

## Planned modules

```
chia/
├── config.example.yaml  # copy to config.yaml, fill in local details, do NOT commit
├── datalayer/           # write daily uptime attestations
├── wallet/              # thin client around chia-blockchain wallet RPC
└── payout/              # compute rewards, build CAT spend bundle, hand off for signing
```

## Config (`chia/config.example.yaml`)

`chia/config.yaml` is **gitignored** — operators copy the example, fill in local values, and never commit it. The token Asset ID is not a secret, but the wallet fingerprint and node certs are.

```yaml
# The Orchard — Chia configuration (example)
# Copy to chia/config.yaml and fill in.

network: mainnet

token:
  name: "JUICE"
  asset_id: "285164e6af80202d2b07fa3cc6ae47ff2906029365a83c50fcab25a56b937121"

reward:
  daily_rate: 1.0          # $JUICE per node per 24h of verified uptime
  season_blocks: 4608      # ~24h on Chia mainnet (a "Season" in The Orchard)
  accrual_unit_hours: 1    # accrue every N hours; 1 = hourly

full_node:
  host: "127.0.0.1"
  port: 8555
  cert_path: "C:/Users/<you>/.chia/mainnet/config/ssl/full_node/private_full_node.crt"
  key_path:  "C:/Users/<you>/.chia/mainnet/config/ssl/full_node/private_full_node.key"

wallet:
  host: "127.0.0.1"
  port: 9256
  fingerprint: 0           # 0 = first wallet
  cert_path: "C:/Users/<you>/.chia/mainnet/config/ssl/wallet/private_wallet.crt"
  key_path:  "C:/Users/<you>/.chia/mainnet/config/ssl/wallet/private_wallet.key"

datalayer:
  host: "127.0.0.1"
  port: 8562
  store_id: ""             # filled by the bootstrap script on first attestation write
```

## Attestation format (DataLayer)

One row per `(node_id, season)` — i.e. one record per Tree per Season:

```json
{
  "node_id": "<base32 device id>",
  "season": <integer season number>,
  "block_height_start": <chia block height>,
  "block_height_end": <chia block height>,
  "hours_online": <0..24>,
  "data_hash": "<sha256 of raw readings batch>",
  "signed_at": "<ISO8601>",
  "oracle_sig": "<ed25519 signature>"
}
```

## Payout flow (Phase 7) — Season harvest

1. For each `(node_id, season)` since last payout: look up `wallet_address` of the Tree operator.
2. Compute `tokens = (hours_online / 24) * daily_rate` (both terms config-driven).
3. Aggregate per wallet.
4. Build a single $JUICE CAT spend bundle paying every eligible wallet.
5. Output bundle JSON for review.
6. Submit via wallet RPC `push_tx`. Record `txn_id` in the oracle DB.

## Status

Phases 5 + 7 — not yet implemented.
