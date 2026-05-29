# SPDX-License-Identifier: Apache-2.0
"""Reward calculation — pure functions, no I/O.

The math is intentionally trivial in v1: ``tokens = (hours_online / 24) * daily_rate``.
Future versions will add multipliers (Pass tier, sensor diversity,
geographic scarcity, validated submissions, reputation) — they'll
slot in as additional arguments to the same function.

CAT amounts are returned in **mojos** (the on-chain integer unit).
$JUICE is a CAT with 3 decimals on Chia, so:

    1 $JUICE  = 1000 mojos
    0.1       =  100 mojos
    0.01      =   10 mojos
    0.001     =    1 mojo

The smallest unit is 0.001 $JUICE. Sub-mojo rewards round toward zero.
"""
from __future__ import annotations

CAT_MOJOS_PER_TOKEN = 1000


def juice_mojos_for_attestation(
    attestation: dict,
    *,
    daily_rate: float,
) -> int:
    """Reward (in $JUICE mojos) for a single signed attestation.

    Caller is responsible for verifying the attestation's signature
    before passing it in — this function trusts the contents.
    """
    hours = int(attestation.get("hours_online", 0))
    if hours < 0 or hours > 24:
        raise ValueError(f"hours_online out of range: {hours}")
    if daily_rate < 0:
        raise ValueError(f"daily_rate must be >= 0, got {daily_rate}")
    juice = (hours / 24.0) * float(daily_rate)
    return int(round(juice * CAT_MOJOS_PER_TOKEN))


def mojos_to_juice(mojos: int) -> float:
    """Format helper for human-readable display."""
    return mojos / CAT_MOJOS_PER_TOKEN


def aggregate_by_wallet(
    rewards: list[dict],
) -> dict[str, int]:
    """Sum mojos owed per recipient wallet.

    ``rewards`` is a list of ``{"wallet_address": str, "mojos": int}``.
    Returns ``{wallet_address: total_mojos}``. Skips entries with
    falsy or empty wallet_address (those Trees haven't bound a wallet
    yet — operator hasn't completed registration).
    """
    out: dict[str, int] = {}
    for r in rewards:
        addr = r.get("wallet_address") or ""
        if not addr:
            continue
        out[addr] = out.get(addr, 0) + int(r.get("mojos", 0))
    return out
