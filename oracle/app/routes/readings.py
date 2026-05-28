# SPDX-License-Identifier: Apache-2.0
"""Reading submission + retrieval.

POST /readings is the hottest path — the Tree calls it every sample
interval. It's also the security boundary: nobody but the Tree's
registered HMAC secret can submit a valid reading.

Authentication:
    Header X-Orchard-Node: <hex node_id>
    Header X-Orchard-Sig:  <hex HMAC-SHA256 of raw body>

The raw body is the JSON the Tree firmware produced; we never reparse
and re-serialize before checking the signature (that would change the
bytes and break HMAC).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auth, models, seasons
from ..db import get_db

router = APIRouter()


class ReadingResponse(BaseModel):
    id: int
    node_id: str
    received_at: datetime
    tree_ts_ms: int | None
    fw_version: str | None
    gps_lat: float | None
    gps_lon: float | None
    gps_fix: bool | None
    payload: dict


def _bump_uptime_hour(db: Session, node_id: str, when: datetime) -> None:
    bucket = seasons.hour_bucket_for(when)
    row = (
        db.execute(
            select(models.UptimeHour).where(
                models.UptimeHour.node_id == node_id,
                models.UptimeHour.hour_utc == bucket,
            )
        )
        .scalar_one_or_none()
    )
    if row is None:
        row = models.UptimeHour(node_id=node_id, hour_utc=bucket, reading_count=1)
        db.add(row)
    else:
        row.reading_count += 1


@router.post("/readings", status_code=status.HTTP_202_ACCEPTED)
async def post_reading(
    request: Request,
    x_orchard_node: str | None = Header(default=None, alias="X-Orchard-Node"),
    x_orchard_sig: str | None = Header(default=None, alias="X-Orchard-Sig"),
    db: Session = Depends(get_db),
) -> dict:
    body_bytes = await request.body()

    try:
        node = auth.verify_reading_sig(db, x_orchard_node, x_orchard_sig, body_bytes)
    except auth.SignatureError as e:
        # Distinguish "unknown node" (404) from "bad signature" (401) for
        # operator clarity; both leak some info but the data path is local.
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "unregistered" in msg else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail=msg)

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid JSON: {e}")

    now = datetime.now(timezone.utc)
    sensors_obj = payload.get("sensors", {}) if isinstance(payload, dict) else {}
    gps = sensors_obj.get("gps", {}) if isinstance(sensors_obj, dict) else {}

    reading = models.Reading(
        node_id=node.node_id,
        received_at=now,
        tree_ts_ms=payload.get("ts_ms") if isinstance(payload, dict) else None,
        fw_version=payload.get("fw") if isinstance(payload, dict) else None,
        gps_lat=gps.get("lat") if isinstance(gps, dict) else None,
        gps_lon=gps.get("lon") if isinstance(gps, dict) else None,
        gps_fix=gps.get("fix") if isinstance(gps, dict) else None,
        payload_json=body_bytes.decode("utf-8"),
        sig_hex=x_orchard_sig.upper() if x_orchard_sig else "",
    )
    db.add(reading)

    # Touch Node state.
    node.last_reading_at = now
    node.last_seen_at = now
    if reading.fw_version:
        node.fw_version = reading.fw_version

    _bump_uptime_hour(db, node.node_id, now)

    db.commit()
    db.refresh(reading)
    return {"id": reading.id, "received_at": reading.received_at.isoformat(),
            "season": seasons.current_season()}


@router.get("/readings/{node_id}", response_model=list[ReadingResponse])
def list_readings(
    node_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ReadingResponse]:
    node_id = node_id.upper()
    if db.get(models.Node, node_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown node_id")

    rows = (
        db.execute(
            select(models.Reading)
            .where(models.Reading.node_id == node_id)
            .order_by(models.Reading.received_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    out: list[ReadingResponse] = []
    for r in rows:
        try:
            payload = json.loads(r.payload_json)
        except Exception:
            payload = {}
        out.append(
            ReadingResponse(
                id=r.id,
                node_id=r.node_id,
                received_at=r.received_at,
                tree_ts_ms=r.tree_ts_ms,
                fw_version=r.fw_version,
                gps_lat=r.gps_lat,
                gps_lon=r.gps_lon,
                gps_fix=r.gps_fix,
                payload=payload,
            )
        )
    return out
