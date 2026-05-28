# SPDX-License-Identifier: Apache-2.0
"""ORM models for the Oracle.

Schema (v1):

    nodes           — every Tree that has registered
    readings        — every signed POST a Tree has submitted
    uptime_hours    — per-Tree, per-UTC-hour bucket (uniqueness keyed)
    seasons         — Season metadata (created lazily on first relevant write)
    attestations    — Phase 5: filled when we publish to DataLayer

In code we use technical names (`node`, `reading`, `season`). User-facing
copy uses brand names (Tree, Harvest, Season). See README Glossary.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Node(Base):
    """A registered Tree. Primary key is the hex node_id from firmware."""
    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signing_key_hex: Mapped[str] = mapped_column(String(64), nullable=False)

    wallet_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fw_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reading_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    readings: Mapped[list["Reading"]] = relationship(back_populates="node", cascade="all, delete-orphan")


class Reading(Base):
    """One signed POST from a Tree."""
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    # Tree-reported fields surfaced for indexing; full payload retained in payload_json.
    tree_ts_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fw_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_fix: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    sig_hex: Mapped[str] = mapped_column(String(64), nullable=False)

    node: Mapped["Node"] = relationship(back_populates="readings")


class UptimeHour(Base):
    """One row per (Tree, UTC hour). Bumping the counter is how we
    detect Trees being alive during that hour for Season uptime math.
    """
    __tablename__ = "uptime_hours"
    __table_args__ = (UniqueConstraint("node_id", "hour_utc", name="uq_uptime_node_hour"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), index=True)
    hour_utc: Mapped[str] = mapped_column(String(13), index=True)  # "YYYY-MM-DDTHH"
    reading_count: Mapped[int] = mapped_column(Integer, default=0)


class Season(Base):
    """Season metadata. v1 = UTC-day-aligned; Phase 5 swaps to Chia blocks."""
    __tablename__ = "seasons"

    season_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    block_height_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_height_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Attestation(Base):
    """Per-(node, season) attestation written to DataLayer (Phase 5)."""
    __tablename__ = "attestations"
    __table_args__ = (UniqueConstraint("node_id", "season_number", name="uq_attest_node_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.node_id"), index=True)
    season_number: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.season_number"), index=True)
    hours_online: Mapped[int] = mapped_column(Integer, nullable=False)
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    oracle_sig: Mapped[str | None] = mapped_column(String(128), nullable=True)
    written_to_datalayer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
