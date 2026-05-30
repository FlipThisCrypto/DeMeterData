# SPDX-License-Identifier: Apache-2.0
"""Orchard View configuration.

Loaded from env vars / `dashboard/.env`. Prefix ``ORCHARD_VIEW_`` so
nothing clashes with the oracle or firmware configs.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 5000

    # Where the oracle is reachable from this machine.
    oracle_url: str = "http://127.0.0.1:8000"

    # What URL we push to a Tree's `ORACLE_SET` during provisioning.
    # Should be reachable from the Tree on the LAN.
    tree_oracle_url: str = "http://192.168.1.10:8000/readings"

    serial_timeout: float = 3.0

    # Public-demo mode. When True:
    #   - The "Plant a Tree" nav link is hidden.
    #   - GET /provision returns 404.
    #   - All /api/serial/* endpoints return 404 (USB has no meaning
    #     for a remote viewer, and we don't want a leaked operator
    #     URL to expose those handlers).
    #   - POST /api/oracle/register returns 404 (registration is an
    #     operator-only flow).
    # Read-only endpoints (/, /tree/<id>, GET /api/oracle/status,
    # GET /api/tree/<id>/latest) remain available.
    # Set ORCHARD_VIEW_PUBLIC_MODE=1 (or =true) to enable.
    public_mode: bool = False

    model_config = SettingsConfigDict(
        env_prefix="ORCHARD_VIEW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_for_tests() -> None:
    global _settings
    _settings = None
