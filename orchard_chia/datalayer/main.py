# SPDX-License-Identifier: Apache-2.0
"""Season attestation writer — orchestrator.

Pulls per-Tree per-Season uptime from the oracle, builds and signs an
attestation record for every closed Season, and writes those records
to a Chia DataLayer store. Idempotent: re-running this re-writes only
records whose value changed since last time.

Run: ``python -m chia.datalayer``

Typical schedule: hourly via cron / Windows Task Scheduler, or on
demand when you want to push a fresh attestation. v1 has no
persistent watermark — re-runs are cheap and safe.
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone

from . import attest, config
from .oracle import OracleClient, OracleError
from .rpc import ChiaRpcError, DataLayerRpc, FullNodeRpc


def main() -> int:
    try:
        cfg = config.load()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not cfg.data_layer.store_id:
        print(
            "ERROR: chia/config.yaml -> datalayer.store_id is empty.\n"
            "Create a store first:\n"
            "    chia data create_data_store -m 0.0001\n"
            "Then put the returned `id` value into config.yaml.",
            file=sys.stderr,
        )
        return 2

    oracle = OracleClient(cfg.oracle.url)
    fn = FullNodeRpc(
        cfg.full_node.host, cfg.full_node.port,
        cfg.full_node.cert_path, cfg.full_node.key_path,
    )
    dl = DataLayerRpc(
        cfg.data_layer.host, cfg.data_layer.port,
        cfg.data_layer.cert_path, cfg.data_layer.key_path,
    )

    print(f"[orchard.attest] oracle:    {cfg.oracle.url}")
    print(f"[orchard.attest] datalayer: {cfg.data_layer.host}:{cfg.data_layer.port}")
    print(f"[orchard.attest] store_id:  {cfg.data_layer.store_id}")

    try:
        current_season = oracle.current_season()
    except OracleError as e:
        print(f"ERROR: oracle unreachable: {e}", file=sys.stderr)
        return 3
    print(f"[orchard.attest] current_season: {current_season} (closed: 1..{current_season - 1})")

    if current_season < 2:
        print("[orchard.attest] No closed Seasons yet. Nothing to attest.")
        return 0

    try:
        nodes = oracle.list_nodes()
    except OracleError as e:
        print(f"ERROR: oracle list_nodes failed: {e}", file=sys.stderr)
        return 3
    print(f"[orchard.attest] registered Trees: {len(nodes)}")
    if not nodes:
        return 0

    try:
        block_height = fn.peak_height()
    except ChiaRpcError as e:
        print(f"ERROR: chia full-node unreachable: {e}", file=sys.stderr)
        return 4
    print(f"[orchard.attest] chia peak height: {block_height}")

    # Determine Season range to process.
    first_season = 1
    if cfg.attestation.max_lookback_seasons is not None:
        first_season = max(1, current_season - cfg.attestation.max_lookback_seasons)

    changelist: list[dict] = []
    stats = Counter()
    lower_lookback = cfg.attestation.max_lookback_seasons or "all"
    print(f"[orchard.attest] lookback: seasons {first_season}..{current_season - 1} ({lower_lookback})")

    for node in nodes:
        node_id = node["node_id"]
        for season in range(first_season, current_season):
            try:
                uptime = oracle.get_uptime(node_id, season)
            except OracleError as e:
                print(f"  WARN: oracle uptime {node_id[:8]}.. season={season}: {e}", file=sys.stderr)
                stats["error"] += 1
                continue
            if uptime is None:
                stats["no_data"] += 1
                continue
            hours = int(uptime.get("hours_online", 0))
            if hours == 0 and cfg.attestation.skip_empty_seasons:
                stats["empty"] += 1
                continue

            payload = attest.build_attestation_payload(
                node_id=node_id,
                season=season,
                hours_online=hours,
                season_start_utc=uptime["season_start_utc"],
                season_end_utc=uptime["season_end_utc"],
                block_height_at_write=block_height,
                data_hash=attest.data_hash_for_uptime(node_id, season, hours),
                signed_at=datetime.now(timezone.utc),
            )
            signed = attest.sign_payload(payload, cfg.signing_key_hex)

            key_hex = attest.datalayer_key_for(node_id, season)
            value_hex = attest.datalayer_value_for(signed)

            try:
                existing_hex = dl.get_value(cfg.data_layer.store_id, key_hex)
            except ChiaRpcError as e:
                print(f"  WARN: datalayer get_value failed: {e}", file=sys.stderr)
                existing_hex = None

            if existing_hex == value_hex:
                stats["unchanged"] += 1
                continue

            if existing_hex is not None:
                # DataLayer batch_update supports delete-then-insert for replaces.
                changelist.append({"action": "delete", "key": key_hex})
            changelist.append({"action": "insert", "key": key_hex, "value": value_hex})
            stats["written"] += 1
            print(
                f"  + node={node_id[:8]}.. season={season:>4} "
                f"hours={hours:>2} signed sig={signed['oracle_sig'][:10]}.."
            )

    if not changelist:
        print(f"[orchard.attest] Nothing to update ({dict(stats)})")
        return 0

    print(f"[orchard.attest] sending {len(changelist)} changelist items to DataLayer ...")
    try:
        result = dl.batch_update(cfg.data_layer.store_id, changelist)
    except ChiaRpcError as e:
        print(f"ERROR: DataLayer batch_update failed: {e}", file=sys.stderr)
        return 5
    txn_id = result.get("tx_id") or result.get("transaction_id") or "<unknown>"
    print(f"[orchard.attest] DataLayer batch_update accepted. tx_id={txn_id}")
    print(f"[orchard.attest] stats: {dict(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
