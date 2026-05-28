# SPDX-License-Identifier: Apache-2.0
"""Tree registration.

A new Tree gets its node_id and HMAC signing secret on first boot
(see firmware/src/identity.cpp). The Orchard View dashboard reads both
from the Tree over USB-serial and POSTs them here so the oracle knows
how to verify future signed submissions.

In v1 anyone can register a Tree — there is no NFT check. Phase 6 adds
an Orchard Pass verification step (must hold the credential NFT on the
declared wallet) before allowing registration.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db

router = APIRouter()

_HEX32 = re.compile(r"^[0-9A-Fa-f]{32}$")  # 16 bytes / node_id
_HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")  # 32 bytes / signing key


class RegisterRequest(BaseModel):
    node_id: str = Field(..., description="32 hex chars (16 bytes)")
    signing_key_hex: str = Field(..., description="64 hex chars (32 bytes HMAC secret)")
    wallet_address: str | None = Field(None, description="Optional Chia wallet address")
    label: str | None = Field(None, description="Optional human-readable label")
    fw_version: str | None = None

    @field_validator("node_id")
    @classmethod
    def _node_id_hex(cls, v: str) -> str:
        if not _HEX32.match(v):
            raise ValueError("node_id must be 32 hex characters")
        return v.upper()

    @field_validator("signing_key_hex")
    @classmethod
    def _key_hex(cls, v: str) -> str:
        if not _HEX64.match(v):
            raise ValueError("signing_key_hex must be 64 hex characters")
        return v.upper()


class RegisterResponse(BaseModel):
    node_id: str
    registered_at: datetime
    new: bool


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing = db.get(models.Node, req.node_id)
    if existing is not None:
        # Re-registration is allowed but only with the same signing key — a
        # different key on the same node_id would mean a different physical
        # Tree claiming the same identity. Refuse.
        if existing.signing_key_hex.upper() != req.signing_key_hex.upper():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="node_id already registered with a different signing key",
            )
        # Update mutable metadata if provided.
        if req.wallet_address is not None:
            existing.wallet_address = req.wallet_address
        if req.label is not None:
            existing.label = req.label
        if req.fw_version is not None:
            existing.fw_version = req.fw_version
        db.commit()
        db.refresh(existing)
        return RegisterResponse(node_id=existing.node_id, registered_at=existing.registered_at, new=False)

    node = models.Node(
        node_id=req.node_id,
        signing_key_hex=req.signing_key_hex,
        wallet_address=req.wallet_address,
        label=req.label,
        fw_version=req.fw_version,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return RegisterResponse(node_id=node.node_id, registered_at=node.registered_at, new=True)
