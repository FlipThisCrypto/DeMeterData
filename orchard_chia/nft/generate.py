# SPDX-License-Identifier: Apache-2.0
"""CHIP-7 metadata generation for the Orchard Pass collection.

Pure functions only — no network. Produces canonical JSON dictionaries
that can be written to disk and then uploaded to IPFS / a CDN /
whatever you prefer. The on-chain mint references the resulting JSON
via ``meta_uris`` and its SHA-256 by ``meta_hash``.

See: https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0007.md
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

# CHIP-7 collection.id for the on-chain genesis batch.
#
# Note on history: this is the UUID mintgarden-studio generated when
# Richard minted the genesis batch through its UI on 2026-05-30. Our
# original local generator used a different UUID, but since the chain
# is the source of truth we adopt the on-chain value here so that
# verify.py matches NFTs minted with either tool from now on.
#
# The corresponding marketplace-canonical (bech32) collection id is in
# ORCHARD_GENESIS_COLLECTION_BECH32_ID below — that's what shows up in
# mintgarden URLs and in the wallet RPC's top-level "collection.id".
ORCHARD_GENESIS_COLLECTION_ID = "96ae1978-1a69-4f1c-ad24-f5ac66d02811"
ORCHARD_GENESIS_COLLECTION_BECH32_ID = (
    "col1a56lp9zufakywlq4k5nntu3nd7k6jy2pe6ee23046ydlahmungqslvmj29"
)
# On-chain name uses ASCII hyphen (mintgarden-studio's default).
ORCHARD_GENESIS_COLLECTION_NAME = "The Orchard - Genesis Passes"
# DID of the minting account on the chain — used by oracle/payout when
# they need to cryptographically confirm a Pass was issued by us.
ORCHARD_GENESIS_CREATOR_DID = (
    "did:chia:10g777py7u3yj2uytdd7a0537ajkkdap9yk9jau5g7n27vvf3s7jqrfamq3"
)

# Collection identity art (pinned on Filebase IPFS). Marketplaces
# (MintGarden, Spacescan) read these from each Pass's metadata as
# well as from the standalone collection.json.
ORCHARD_GENESIS_BANNER_URI = (
    "https://defiant-black-skink.myfilebase.com/ipfs/"
    "QmNvG6xqzPGbH31ZS6wNomAJTSqEFsp43t7CHXaZtKxHmb"
)
ORCHARD_GENESIS_ICON_URI = (
    "https://defiant-black-skink.myfilebase.com/ipfs/"
    "QmUWhqeByfKrVAa5Ev3MRymFmhMSoTMnzDwE3Gjd4Cvray"
)
ORCHARD_GENESIS_WEBSITE = "https://fiendstudios.com/"
# Twitter is the handle alone, not the URL — matches how
# mintgarden-studio generates collection metadata. URL form causes
# some marketplaces' parsers to bail.
ORCHARD_GENESIS_TWITTER = "FiendStudios"

# How many Passes in the genesis batch.
GENESIS_TOTAL = 10

# Default minting tool ID; bump on any breaking schema change.
MINTING_TOOL = "orchard-mint v0.1"


def _collection_attributes() -> list[dict]:
    """Standard collection attributes used by both the standalone
    collection.json and each per-Pass JSON's ``collection.attributes``
    field. Including them in both maximizes marketplace compatibility:
    viewers that can't resolve the collection by id will still pull
    banner/icon from any individual NFT they see.
    """
    # Order matches the structure produced by mintgarden-studio:
    # description, icon, banner, twitter, website. Some marketplace
    # parsers are order-sensitive when discovering icon/banner.
    return [
        {
            "type": "description",
            "value": (
                "Founding credentials for The Orchard — an open-source "
                "environmental DePIN on the Chia blockchain. Each Pass "
                "is the on-chain identity of a Tree (ESP32-class sensing "
                "node). Holders operate the first Trees in the network, "
                "collecting verifiable environmental data and earning "
                "$JUICE for verified Season uptime. Ten Passes in the "
                "genesis batch."
            ),
        },
        {"type": "icon",    "value": ORCHARD_GENESIS_ICON_URI},
        {"type": "banner",  "value": ORCHARD_GENESIS_BANNER_URI},
        {"type": "twitter", "value": ORCHARD_GENESIS_TWITTER},
        {"type": "website", "value": ORCHARD_GENESIS_WEBSITE},
    ]


def build_collection_metadata() -> dict:
    """Collection-level CHIP-7 document. Lives at ``nft/collection.json``.

    This is the document the per-pass NFTs reference via their
    ``collection`` field.
    """
    return {
        "name": ORCHARD_GENESIS_COLLECTION_NAME,
        "id": ORCHARD_GENESIS_COLLECTION_ID,
        "attributes": _collection_attributes(),
    }


def build_pass_metadata(
    *,
    pass_number: int,
    series_total: int = GENESIS_TOTAL,
    name: str | None = None,
    description: str | None = None,
    extra_attributes: list[dict] | None = None,
) -> dict:
    """One CHIP-7 metadata document for Orchard Pass #pass_number."""
    if not 1 <= pass_number <= series_total:
        raise ValueError(f"pass_number must be 1..{series_total}, got {pass_number}")

    if name is None:
        name = f"Orchard Pass #{pass_number:04d}"
    if description is None:
        description = (
            f"Genesis Pass {pass_number} of {series_total} — proof of operation "
            f"for a Tree in The Orchard, an open-source environmental DePIN on Chia. "
            f"Holder operates one of the first {series_total} Trees in the network."
        )

    attributes: list[dict] = [
        {"trait_type": "Pass Number",    "value": f"{pass_number:04d}"},
        {"trait_type": "Generation",     "value": "Genesis"},
        {"trait_type": "Tier",           "value": "Founder"},
        {"trait_type": "Reward Token",   "value": "$JUICE"},
        {"trait_type": "Node Type",      "value": "ESP32-class Tree"},
        {"trait_type": "Network",        "value": "Chia Mainnet"},
    ]
    if extra_attributes:
        attributes.extend(extra_attributes)

    # Field order matches the reference produced by mintgarden-studio:
    # format, minting_tool, name, description, attributes, collection.
    # Omits sensitive_content / series_number / series_total — those
    # are CHIP-7-valid but unused by the reference; some marketplaces'
    # parsers don't expect them and fall back to image-only rendering.
    return {
        "format":       "CHIP-0007",
        "minting_tool": MINTING_TOOL,
        "name":         name,
        "description":  description,
        "attributes":   attributes,
        "collection": {
            "id":         ORCHARD_GENESIS_COLLECTION_ID,
            "name":       ORCHARD_GENESIS_COLLECTION_NAME,
            "attributes": _collection_attributes(),
        },
    }


def canonical_json(obj: dict) -> str:
    """Same canonicalization rule as DataLayer attestations — sorted
    keys, no whitespace. This is what gets hashed for ``meta_hash``."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: str | Path) -> str:
    """SHA-256 of a file's contents (no streaming gotchas for video
    files because we want the on-chain hash to match what nft.storage
    et al. compute over the same bytes)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_genesis_batch(target_dir: str | Path, total: int = GENESIS_TOTAL) -> list[Path]:
    """Write ``total`` stub metadata files into target_dir as 0001.json..NNNN.json.

    Each file is a CHIP-7 document with placeholders for the per-Pass
    video URI etc. — the operator fills those in after uploading the
    videos and editing the mint plan.
    """
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for n in range(1, total + 1):
        meta = build_pass_metadata(pass_number=n, series_total=total)
        path = target / f"{n:04d}.json"
        # Pretty-printed for human inspection. The mint-time canonical
        # form (and hash) is computed separately via canonical_json().
        path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written
