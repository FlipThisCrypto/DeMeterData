# SPDX-License-Identifier: Apache-2.0
"""Oracle service configuration.

All settings load from environment variables (or `oracle/.env`), prefixed
with ``ORCHARD_ORACLE_`` so they don't collide with other components.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Override via env vars or oracle/.env."""

    # Default to localhost-only. `/register` accepts any caller with a
    # node_id + signing key and no auth, so a 0.0.0.0 bind would let
    # any LAN device pre-claim a node_id and lock out the real Tree.
    # If you need real Trees on the WiFi to POST signed readings to
    # this oracle, set ORCHARD_ORACLE_HOST=0.0.0.0 explicitly in your
    # `.env` AND understand that anyone on the same network can also
    # call /register.
    host: str = "127.0.0.1"
    port: int = 8000
    db_url: str = "sqlite:///./oracle/data/orchard.db"
    log_level: str = "info"

    # v1 Season math: day-aligned. Phase 5 will swap this for
    # Chia-block-aligned Seasons.
    season_genesis_date: date = date(2026, 5, 27)

    model_config = SettingsConfigDict(
        env_prefix="ORCHARD_ORACLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None


def settings() -> Settings:
    """Lazy singleton so tests can override env before the first call."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure the SQLite data directory exists if we're using one.
        if _settings.db_url.startswith("sqlite:///"):
            db_path = Path(_settings.db_url.replace("sqlite:///", "", 1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
    return _settings


def reset_settings_for_tests() -> None:
    """Tests can call this after monkeypatching the env."""
    global _settings
    _settings = None
