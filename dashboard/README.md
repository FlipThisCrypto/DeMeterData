# dashboard/ — Orchard View (local Flask dashboard)

**Orchard View** is the local web UI you run on your PC. It does two things:

1. **Plant a Tree** — walks you through end-to-end provisioning of a newly-flashed Tree: pick its USB-serial port, identify it, register it with the oracle, push WiFi credentials and oracle URL, trigger the first sample. Everything happens in a single page with live status per step.
2. **Live Tree view** — polls the oracle every few seconds and shows the latest signed reading from a Tree: MQ-135 air quality, GPS fix + coordinates, recent readings table, and uptime in the current Season.

> **Vocabulary:** Trees, Seasons, Orchard Passes. Code uses `node`/`season`/`pass`. See the [Glossary](../README.md#glossary).

## Pages

| URL              | What                                                              |
|------------------|-------------------------------------------------------------------|
| `/`              | Home — oracle status + list of registered Trees                   |
| `/provision`     | Wizard: identify a Tree over USB, configure it, send it to work   |
| `/tree/<node>`   | Live view for a Tree (5s polling)                                 |
| `/api/...`       | JSON endpoints used by the pages (see `app/routes/api.py`)        |

## Quick start

Run from the repo root:

```bash
# 1. Install (in the same .venv as the oracle is fine)
pip install -r dashboard/requirements.txt

# 2. (Optional) override defaults
cp dashboard/.env.example dashboard/.env
# edit dashboard/.env — point ORCHARD_VIEW_TREE_ORACLE_URL at your LAN IP
# so a Tree on WiFi can reach the oracle.

# 3. Run (the oracle should already be running in another terminal)
python -m dashboard.app
# -> http://127.0.0.1:5000/
```

Open the URL in any browser. If the oracle is running at `http://127.0.0.1:8000` (the default), the home page will say "Oracle: Connected"; if not, it'll show the start command for the oracle.

## Closing the loop with a real Tree

1. Flash the firmware (`firmware/`) and plug the Tree into USB. (See [firmware/README.md](../firmware/README.md).)
2. Start the oracle (`python -m oracle.app.main`).
3. Start Orchard View (`python -m dashboard.app`).
4. Open `http://127.0.0.1:5000/provision` and click **Plant a Tree**.
5. Pick the Tree's COM port, click **Identify Tree** — node_id, fw version, and current status come back.
6. Fill in WiFi SSID / password, optional label / wallet address, and the oracle URL (must be reachable from the Tree on the LAN — not `127.0.0.1`).
7. Click **Provision Tree**. The dashboard walks the four steps: register with oracle → push WiFi → push oracle URL → SAMPLE_NOW. Each step shows status in real time.
8. You're redirected to `/tree/<node_id>`. The live view starts polling the oracle every 5 seconds. The first signed reading should land within ~30 seconds (Tree boots, joins WiFi, sends).

## Smoke tests

```bash
pytest dashboard/tests/
```

Tests cover: home page with oracle up and down, provision page renders, tree page 404 vs found, the API endpoints with the oracle and serial layers mocked.

## What's deliberately not in v1

- **OTA upload UI.** You can push firmware via `curl -F` against the Tree's `/ota` endpoint for now; the dashboard wrapper is a v1.1 polish.
- **I2C bus scan / UART signature sniff.** Auto-detection requires the dashboard to take over the Tree's serial port at length — better delivered when the Orchard View talks to the Tree continuously rather than one-shot.
- **Orchard Pass NFT verification at registration time.** That's Phase 6 — the oracle will gate `/register` on it then.
- **Multi-Tree admin actions (delete, rename, force-reflash).** Coming after Phase 7 / when there's actually a fleet to manage.

## Status

Phase 4 implemented: provisioning wizard, live view, registered-Trees listing, all wired to the oracle. Closes the v1 data loop visually.
