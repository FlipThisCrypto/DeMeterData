# oracle/ — sensor data oracle

A FastAPI service that nodes POST signed readings to. Stores raw data in SQLite locally and exposes endpoints the dashboard and the attestation writer use.

## Why this is its own component

The oracle is the single trust boundary between "what nodes claim" and "what the system records." It verifies signatures, enforces uptime accounting, and stores the data daily attestations are computed from. It is deliberately small and replaceable — a future v2 may decentralize it.

## Planned endpoints (Phase 3)

| Endpoint                   | Method | Purpose                                     |
|----------------------------|--------|---------------------------------------------|
| `/register`                | POST   | Onboard a new node (verifies NFT credential)|
| `/readings`                | POST   | Node submits signed sensor reading          |
| `/nodes`                   | GET    | List registered nodes                       |
| `/nodes/{node_id}`         | GET    | Single node status + last seen              |
| `/readings/{node_id}`      | GET    | Recent readings for a node                  |
| `/uptime/{node_id}/{season}`| GET    | Uptime hours for a node in a given season    |

## Storage

SQLite via SQLAlchemy. Tables (planned): `nodes`, `readings`, `uptime_hours`, `seasons`, `attestations`.

Daily attestations rolled up from `uptime_hours` are written to Chia DataLayer by [../chia/](../chia/).

## Status

Phase 3 — not yet implemented. The previously-running oracle (repurposed from a different project) is being replaced because its schema didn't match the new node design.
