# nft/ — Orchard Pass NFT collection

An **Orchard Pass** is the NFT credential that proves "this wallet operates a Tree in The Orchard." v1 enforces **one Orchard Pass per wallet** at registration time.

(The vision is for Orchard Passes to eventually carry tier multipliers, sensor manifests, and reputation. v1 keeps them simple — pure ownership credential. See [../docs/VISION.md](../docs/VISION.md).)

## Why an NFT?

A wallet address alone is fungible identity. An NFT is a specific, transferable token tied to a launcher coin — easy to verify on-chain, easy to transfer if the Tree operator changes hands, easy to extend later with on-chain attributes (e.g., reputation score, accumulated uptime, sensor count, geographic tag).

## Standard

We follow [CHIP-7 NFT metadata](https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0007.md) — the de-facto Chia NFT1 metadata standard.

## Planned files (Phase 6)

```
nft/
├── metadata/                # one JSON per Orchard Pass, CHIP-7-compliant
│   └── 0001.json
├── collection.json          # collection-level metadata
└── mint.py                  # script that calls wallet RPC nft_mint_nft
```

## Per-Pass metadata fields (v1 draft)

```json
{
  "format": "CHIP-0007",
  "name": "Orchard Pass #0001",
  "description": "Credential for a Tree in The Orchard — an open-source environmental DePIN on Chia.",
  "minting_tool": "orchard-mint v0.1",
  "sensitive_content": false,
  "series_number": 1,
  "series_total": 10000,
  "attributes": [
    { "trait_type": "Tree Type",      "value": "ESP32-S3 v1" },
    { "trait_type": "Network",        "value": "Chia Mainnet" },
    { "trait_type": "Generation",     "value": "Genesis" },
    { "trait_type": "Reward Token",   "value": "$JUICE" }
  ],
  "collection": {
    "name": "The Orchard — Genesis Passes",
    "id": "<collection-id-tbd>",
    "attributes": []
  }
}
```

## Reserved attributes for future versions

Per the vision, future Orchard Passes will carry richer attributes. Reserved trait names (do not reuse for unrelated meanings):

- `Tier` — Bronze / Silver / Gold / Genesis / etc.
- `Reward Multiplier` — numeric multiplier on base $JUICE accrual.
- `Sensor Manifest` — list of validated sensor types on the Tree.
- `Geographic Region` — coarse geographic tag (state/country level).
- `Reputation Score` — accrued over Seasons of validated submissions.

v1 mint script will **not** populate these. They are documented here so collection metadata stays forward-compatible.

## Status

Phase 6 — not yet implemented. Mint script will be triggered by the dashboard's "Plant a new Tree" registration wizard in Phase 4, once the collection launcher exists.
