# SPDX-License-Identifier: Apache-2.0
"""Node directory."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db

router = APIRouter()


class NodePublic(BaseModel):
    node_id: str
    wallet_address: str | None
    label: str | None
    fw_version: str | None
    registered_at: datetime
    last_seen_at: datetime | None
    last_reading_at: datetime | None


def _to_public(n: models.Node) -> NodePublic:
    return NodePublic(
        node_id=n.node_id,
        wallet_address=n.wallet_address,
        label=n.label,
        fw_version=n.fw_version,
        registered_at=n.registered_at,
        last_seen_at=n.last_seen_at,
        last_reading_at=n.last_reading_at,
    )


@router.get("/nodes", response_model=list[NodePublic])
def list_nodes(db: Session = Depends(get_db)) -> list[NodePublic]:
    rows = db.execute(select(models.Node).order_by(models.Node.registered_at.desc())).scalars().all()
    return [_to_public(n) for n in rows]


@router.get("/nodes/{node_id}", response_model=NodePublic)
def get_node(node_id: str, db: Session = Depends(get_db)) -> NodePublic:
    node = db.get(models.Node, node_id.upper())
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown node_id")
    return _to_public(node)
