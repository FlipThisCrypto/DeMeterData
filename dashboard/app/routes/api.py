# SPDX-License-Identifier: Apache-2.0
"""AJAX endpoints used by the dashboard pages.

All under `/api/...`. Pure JSON in / JSON out. The HTML pages are
mostly static; these endpoints do the work.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from .. import oracle_client, tree_serial

bp = Blueprint("api", __name__)


def _ok(data) -> tuple:
    return jsonify({"ok": True, **(data if isinstance(data, dict) else {"data": data})}), 200


def _err(msg: str, code: int = 400) -> tuple:
    return jsonify({"ok": False, "error": msg}), code


# ---------------------------------------------------------------- oracle ----

@bp.get("/oracle/status")
def oracle_status():
    try:
        info = oracle_client.root()
        return _ok({"oracle": info})
    except oracle_client.OracleError as e:
        return _err(str(e), code=502)


@bp.post("/oracle/register")
def oracle_register():
    body = request.get_json(silent=True) or {}
    try:
        result = oracle_client.register_node(
            node_id=body["node_id"],
            signing_key_hex=body["signing_key_hex"],
            label=body.get("label"),
            wallet_address=body.get("wallet_address"),
            fw_version=body.get("fw_version"),
        )
        return _ok({"register": result})
    except KeyError as e:
        return _err(f"missing field: {e.args[0]}", code=400)
    except oracle_client.OracleError as e:
        return _err(str(e), code=502)


# ---------------------------------------------------------------- serial ----

@bp.get("/serial/ports")
def serial_ports():
    ports = [{"device": p.device, "description": p.description, "hwid": p.hwid}
             for p in tree_serial.list_ports()]
    return _ok({"ports": ports})


@bp.post("/serial/identify")
def serial_identify():
    """Talk to a Tree, return its identity. Run after the user picks a port."""
    body = request.get_json(silent=True) or {}
    port = body.get("port")
    if not port:
        return _err("missing port", code=400)
    try:
        if not tree_serial.ping(port):
            return _err("no PING response — is this a Tree?", code=502)
        node_id = tree_serial.get_node_id(port)
        signing_key = tree_serial.get_signing_key(port)
        status = tree_serial.get_status(port)
        return _ok({
            "node_id": node_id,
            "signing_key_hex": signing_key,
            "status": status,
        })
    except tree_serial.TreeError as e:
        return _err(str(e), code=502)


@bp.post("/serial/wifi")
def serial_wifi():
    body = request.get_json(silent=True) or {}
    port = body.get("port"); ssid = body.get("ssid"); password = body.get("password", "")
    if not port or not ssid:
        return _err("port and ssid required", code=400)
    try:
        tree_serial.set_wifi(port, ssid, password)
        return _ok({"wifi_set": True})
    except tree_serial.TreeError as e:
        return _err(str(e), code=502)


@bp.post("/serial/oracle")
def serial_set_oracle():
    body = request.get_json(silent=True) or {}
    port = body.get("port"); url = body.get("url")
    if not port or not url:
        return _err("port and url required", code=400)
    try:
        tree_serial.set_oracle_url(port, url)
        return _ok({"oracle_url_set": url})
    except tree_serial.TreeError as e:
        return _err(str(e), code=502)


@bp.post("/serial/sample")
def serial_sample_now():
    body = request.get_json(silent=True) or {}
    port = body.get("port")
    if not port:
        return _err("port required", code=400)
    try:
        tree_serial.sample_now(port)
        return _ok({"sampled": True})
    except tree_serial.TreeError as e:
        return _err(str(e), code=502)


# --------------------------------------------------------------- live view --

@bp.get("/tree/<node_id>/latest")
def tree_latest(node_id: str):
    node_id = node_id.upper()
    try:
        node = oracle_client.get_node(node_id)
        if node is None:
            return _err("unknown node_id", code=404)
        readings = oracle_client.list_readings(node_id, limit=20)

        current_season = None
        uptime = None
        try:
            current_season = oracle_client.root().get("current_season")
            if current_season:
                uptime = oracle_client.get_uptime(node_id, current_season)
        except oracle_client.OracleError:
            pass  # uptime is nice-to-have; never break the live view for it

        # Compute "alive" heuristic: last reading within 2x sample interval.
        alive = False
        last_received_at = None
        if readings:
            last_received_at = readings[0].get("received_at")
            try:
                dt = datetime.fromisoformat(last_received_at.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - dt).total_seconds()
                alive = age < 180  # default sample interval is 60s; 3x for tolerance
            except (TypeError, ValueError, AttributeError):
                pass

        return _ok({
            "node": node,
            "readings": readings,
            "latest": readings[0] if readings else None,
            "alive": alive,
            "last_received_at": last_received_at,
            "current_season": current_season,
            "uptime": uptime,
            "server_now_utc": datetime.now(timezone.utc).isoformat(),
        })
    except oracle_client.OracleError as e:
        return _err(str(e), code=502)
