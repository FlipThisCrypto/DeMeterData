# SPDX-License-Identifier: Apache-2.0
"""Orchard Pass ownership verification.

Used by the oracle's ``/register`` endpoint (Phase 6.5, deferred) and
the payout script (Phase 7) to gate operator actions on holding a
Pass.

v1 limitation: this works only when the operator's wallet and the
oracle's wallet daemon are on the same machine (same key set). True
cross-machine ownership verification needs a Chia NFT indexer such as
Spacescan / Mintgarden, or a signed-challenge flow. Documented in the
README; will be a Phase 6.5 follow-up.
"""
from __future__ import annotations

from typing import Iterable

from .generate import ORCHARD_GENESIS_COLLECTION_ID
from ..wallet.rpc import WalletRpc, WalletRpcError


def _iter_owned_nfts(rpc: WalletRpc, wallet_id: int,
                     batch: int = 50) -> Iterable[dict]:
    """Page through every NFT this wallet owns."""
    start = 0
    while True:
        items = rpc.nft_get_nfts(wallet_id=wallet_id, start_index=start, num=batch)
        if not items:
            return
        for it in items:
            yield it
        if len(items) < batch:
            return
        start += len(items)


def _nft_collection_id(nft_info: dict) -> str | None:
    """CHIP-7 collection.id field, dug out of whatever shape the wallet
    RPC returned. Tolerant of small shape differences across releases.
    """
    # Modern Chia wallet returns metadata_url-resolved fields directly.
    coll = nft_info.get("collection") or {}
    if isinstance(coll, dict):
        cid = coll.get("id")
        if cid:
            return str(cid)
    # Some versions surface the parsed metadata under metadata_json.
    md = nft_info.get("metadata_json") or {}
    if isinstance(md, dict):
        coll = md.get("collection") or {}
        if isinstance(coll, dict):
            cid = coll.get("id")
            if cid:
                return str(cid)
    return None


def wallet_holds_pass(rpc: WalletRpc, *, nft_wallet_id: int,
                     collection_id: str = ORCHARD_GENESIS_COLLECTION_ID,
                     ) -> bool:
    """Return True if any NFT in ``nft_wallet_id`` belongs to
    ``collection_id``.

    Raises WalletRpcError if the wallet daemon is unreachable; caller
    should treat that as "could not verify" and decide policy (deny vs
    allow-when-uncheckable) at the call site.
    """
    for nft in _iter_owned_nfts(rpc, nft_wallet_id):
        if _nft_collection_id(nft) == collection_id:
            return True
    return False


def list_owned_passes(rpc: WalletRpc, *, nft_wallet_id: int,
                     collection_id: str = ORCHARD_GENESIS_COLLECTION_ID,
                     ) -> list[dict]:
    """Like wallet_holds_pass but returns all matching NFT records."""
    out: list[dict] = []
    for nft in _iter_owned_nfts(rpc, nft_wallet_id):
        if _nft_collection_id(nft) == collection_id:
            out.append(nft)
    return out
