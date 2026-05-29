# SPDX-License-Identifier: Apache-2.0
"""Configuration for the Season attestation writer.

Loads from ``chia/config.yaml`` (operator-private; gitignored) and
falls back to defaults when fields are missing. Operators copy
``chia/config.example.yaml`` to ``chia/config.yaml`` and fill in
local node + DataLayer paths.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
SIGNING_KEY_PATH = Path(__file__).resolve().parents[1] / "data" / "oracle_signing_key.hex"


@dataclass
class FullNodeConfig:
    host: str
    port: int
    cert_path: str
    key_path: str


@dataclass
class DataLayerConfig:
    host: str
    port: int
    cert_path: str
    key_path: str
    store_id: str


@dataclass
class OracleConfig:
    url: str = "http://127.0.0.1:8000"


@dataclass
class AttestationConfig:
    # How many Seasons before the current one to attest.
    # Default: all closed Seasons (None = no limit).
    max_lookback_seasons: int | None = None
    # Skip Seasons where uptime_hours is 0 (Tree never reported during them).
    skip_empty_seasons: bool = True


@dataclass
class Config:
    network: str
    full_node: FullNodeConfig
    data_layer: DataLayerConfig
    oracle: OracleConfig
    attestation: AttestationConfig
    signing_key_hex: str


def _expand(path_str: str) -> str:
    return os.path.expandvars(os.path.expanduser(path_str))


def load() -> Config:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"chia/config.yaml not found at {CONFIG_PATH}. "
            f"Copy chia/config.example.yaml to chia/config.yaml and edit."
        )
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    fn = raw.get("full_node", {})
    dl = raw.get("datalayer", {}) or raw.get("data_layer", {})
    orcl = raw.get("oracle", {})
    att = raw.get("attestation", {}) or {}

    return Config(
        network=raw.get("network", "mainnet"),
        full_node=FullNodeConfig(
            host=fn.get("host", "127.0.0.1"),
            port=int(fn.get("port", 8555)),
            cert_path=_expand(fn.get("cert_path", "")),
            key_path=_expand(fn.get("key_path", "")),
        ),
        data_layer=DataLayerConfig(
            host=dl.get("host", "127.0.0.1"),
            port=int(dl.get("port", 8562)),
            cert_path=_expand(dl.get("cert_path", "")),
            key_path=_expand(dl.get("key_path", "")),
            store_id=dl.get("store_id", ""),
        ),
        oracle=OracleConfig(
            url=orcl.get("url", "http://127.0.0.1:8000"),
        ),
        attestation=AttestationConfig(
            max_lookback_seasons=att.get("max_lookback_seasons"),
            skip_empty_seasons=bool(att.get("skip_empty_seasons", True)),
        ),
        signing_key_hex=_load_or_make_signing_key(),
    )


def _load_or_make_signing_key() -> str:
    """Per-oracle signing key. Generated on first run, persisted locally,
    never transmitted. 32 bytes / 64 hex chars. Gitignored under chia/data/."""
    SIGNING_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SIGNING_KEY_PATH.exists():
        text = SIGNING_KEY_PATH.read_text(encoding="utf-8").strip()
        if len(text) == 64 and all(c in "0123456789abcdefABCDEF" for c in text):
            return text.upper()
    # Generate fresh.
    import secrets
    new_hex = secrets.token_hex(32).upper()
    SIGNING_KEY_PATH.write_text(new_hex + "\n", encoding="utf-8")
    return new_hex
