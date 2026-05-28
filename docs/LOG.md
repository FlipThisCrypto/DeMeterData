# The Orchard — Development Log

> Running journal of what worked, what failed, and what we learned. Newest entries on top. Append liberally — failures are as instructive as successes. Format: a date heading, then short bullet points. Keep entries scannable.

---

## 2026-05-27 — Phase 4: Orchard View dashboard

### Successes

- **Orchard View MVP shipped.** Flask 3.1 + vanilla JS + a hand-rolled dark CSS theme (no framework deps). Three pages — home (oracle status + Tree list), Plant a Tree (provisioning wizard), live Tree view (5-second polling).
- **End-to-end provisioning wizard works.** Single-page flow: pick a COM port → identify Tree (PING/NODE_ID/KEY/STATUS over serial) → fill in label/wallet/SSID/password/oracle URL → click Provision → dashboard sequences (register with oracle, WIFI_SET, ORACLE_SET, SAMPLE_NOW), shows status per step, redirects to the live view. No page reloads, no juggling of multiple windows.
- **Live view shows the data we promised.** MQ-135 (raw ADC, voltage, baseline, deviation), GPS (fix, satellites, lat/lon, altitude, UTC), uptime hours this Season, alive/stale indicator based on age of last reading. Recent-readings table for context.
- **11 dashboard tests + 6 oracle tests = 17 passing in 1.65s.** Tests stub out `tree_serial` and `oracle_client` so they run hermetically — no actual serial port, no actual oracle process needed.

### Failures / issues (encountered and resolved)

- **Pytest module-name collision.** First all-tests run failed: both components had `tests/test_basic.py` files, and pytest's default `prepend` import mode treats `tests/` as a top-level package — so it tried to import two modules at the same dotted path. **Fix:** rename to `test_oracle.py` and `test_dashboard.py`, remove the `__init__.py` files inside both `tests/` dirs, add a root `pyproject.toml` with `--import-mode=importlib` and explicit `testpaths`. Both unique test files now found, no conflict.

### Decisions

- **Dashboard talks to the oracle via HTTP only.** No shared DB, no shared in-process imports. Means the dashboard could run on a different host than the oracle later without any code changes.
- **One serial-open per command** in `tree_serial.py`, instead of a persistent connection. Slower per-call but stateless across Flask requests — and provisioning is a once-per-Tree operation, so the latency is invisible.
- **Polling (5s) instead of SSE/WebSocket** for live updates. Adds zero infrastructure, works through any reverse proxy, fine for the 60s sample cadence. Can upgrade later if cadence drops below polling interval.
- **Brand colors:** orange (`#ff8c42`, the JUICE accent) for primary actions, fresh green (`#8fde6e`) for OK/active states. Dark background for long sessions. No CSS framework — kept the entire stylesheet small enough to read in one pass (~150 lines).

### What's deferred

- **OTA upload UI.** Use `curl -F` against the Tree's `/ota` endpoint until Phase 4.1.
- **I2C bus scan / UART signature sniff** for sensor auto-detect — requires the dashboard to take over the serial port continuously, which doesn't fit the v1 one-shot-command model.
- **Multi-Tree admin actions** (delete, rename, force re-flash) — wait until there's a real fleet.
- **Orchard Pass NFT gate on `/register`** — that's Phase 6 (oracle-side check).

### What this unlocks

- **The full v1 loop is now demonstrable in real time.** Tree (firmware) → POST → oracle → SQLite, **with a browser tab open at `/tree/<node_id>` watching it happen**. That's the "close the loop where I can see it" milestone Richard asked for.

---

## 2026-05-27 — Phase 3: Oracle service

### Successes

- **Oracle service implemented end-to-end.** FastAPI 0.136 + SQLAlchemy 2.0 + Pydantic 2.12 + pydantic-settings. All on Richard's Python 3.14 install. Endpoints: `/`, `/health`, `/register`, `/readings` (POST + GET-by-node), `/nodes`, `/nodes/{id}`, `/uptime/{node}/{season}`.
- **Six smoke tests, all passing in 1.17s.** Covers: service identification, register (new + duplicate-same-key + duplicate-different-key conflict), POST with unknown node (404), POST with bad signature (401), POST happy path → retrieve → uptime bucket increment, uptime for unknown node (404).
- **HMAC-SHA256 verification matches the Tree firmware exactly.** Server reads raw bytes via `request.body()` (no JSON re-parsing before signature check, which would have broken the bytes), computes HMAC with stored signing key, constant-time compares with the `X-Orchard-Sig` header.
- **v1 Season math is in.** Day-aligned UTC Seasons starting from a configurable genesis date (default 2026-05-27). Phase 5 will swap `seasons.py` for Chia-block-aligned Seasons — the rest of the oracle treats `(node_id, season)` as opaque.
- **`oracle/data/` auto-creates on first run.** SQLite DB file lands at `oracle/data/orchard.db`. Directory is already covered by `.gitignore`.

### Failures / issues (encountered and resolved)

- **SQLite `:memory:` connections don't share state.** First test run failed with `no such table: nodes` even though `Base.metadata.create_all()` ran. Root cause: with `sqlite:///:memory:`, *each new connection gets its own empty database*. Schema was created on one connection, sessions used a different one. **Fix:** use `StaticPool` in the test engine so all sessions reuse a single connection. Production path is unaffected (uses file-backed SQLite).
- **Python 3.14 + new packages:** worth noting — fastapi 0.136, sqlalchemy 2.0.50, pydantic 2.12 all install cleanly on 3.14 without complaints. No version pinning gymnastics needed.

### Decisions

- **No NFT check on `/register` in v1.** Anyone with a Tree's `(node_id, signing_key_hex)` pair can register. Phase 6 will add Orchard Pass verification (operator must hold the credential NFT on the declared wallet). Documented in the oracle README.
- **Reading payload stored as raw JSON text + extracted GPS columns.** Full payload preserved for forensics + future-proofing; common fields (`gps_lat/lon/fix`, `fw_version`, `tree_ts_ms`) extracted into indexable columns for queries.
- **`/readings` returns 202 Accepted, not 200.** Semantically, the server has accepted the data and queued it for storage; the Tree doesn't need to wait on durability confirmation. Matters when we eventually add async persistence.

### What this unlocks

- **End-to-end data path is live.** Tree → signed POST → oracle SQLite → retrieve. Provision the existing Tree (COM4) over serial (`WIFI_SET`, `ORACLE_SET`) and the first real reading will flow.
- **Phase 4 (Orchard View)** can start — it has real endpoints to call.
- **Phase 5 (Season attestation writer)** can start — it has real uptime data to roll up.

---

## 2026-05-27 — First living Tree 🌱

**Tree node_id: `5B9BB022649FA93D4091DA4BA40714B9`** (ESP32-WROOM-32U in the prototype enclosure, on COM4).

### Successes

- **The Orchard is alive on real hardware.** Firmware flashed successfully (995,552 bytes, 10.6s upload at 752 kbit/s, hash verified). Chip rebooted into our firmware and produced the expected first-boot output.
- **First-boot identity generation worked end-to-end.** The two `nvs_get_blob NOT_FOUND` lines for `node_id` and `sign_key` are exactly what the firmware expects on a virgin chip — `identity::begin()` then generated fresh values and stored them in NVS. The Tree's `node_id` is now permanent: `5B9BB022649FA93D4091DA4BA40714B9`.
- **Sensor registry self-registration works.** Both `MQ135Sensor` and `GpsNeoSensor` AutoRegister<> instances pushed themselves into the registry at static-init time without any central wiring. Both passed `begin()` (`active=yes`) and the registry reports `2 active sensor(s)`.
- **WiFi manager and oracle client behave correctly on a virgin Tree.** WiFi: "no creds stored; idle. Use WIFI_SET over serial." Oracle: "WiFi not connected; skipping POST." Both are the right messages — no exceptions, no crashes, no silent failures.
- **Dual-target build proven viable.** Same source tree, two PlatformIO envs (`freenove_esp32_wroom` + `freenove_esp32s3`), one of each chip family will land on a Tree as the project grows.

### Failures / issues (encountered and resolved)

- **Auto-reset wasn't working on the WROOM-32U.** First upload failed with `Wrong boot mode detected (0x13)` — DTR/RTS dance via CP210x didn't bring the chip into download mode. **Workaround:** manual BOOT-button-held + RESET-tap + BOOT-still-held, run upload, release BOOT after writing starts. Worked first try with the manual procedure.
- **Wrong board assumption.** Memory and ADR initially recorded the prototype as ESP32-**S3**. Actually it's an ESP32-**WROOM-32U** (classic ESP32 with external antenna). Caught by esptool's chip-ID check before any bytes were written to the wrong chip. Memory + LOG corrected; platformio.ini now carries both envs with WROOM as the default.
- **Banner mangled in my capture script.** First-line output came back as `=== Themware ===` because my Python `serial.read(in_waiting or 1)` loop dropped bytes during the initial boot burst (latency between `in_waiting` checks). The firmware print is correct — verified with `pio device monitor` directly. Future captures should use a single `s.read(s.in_waiting)` after a brief sleep, or just use `pio device monitor` interactively.

### What this unlocks

- **Phase 3 (oracle) is now a real need, not a stub.** The Tree is generating data and signing it; nothing to send it to until the oracle exists.
- **Provisioning workflow is real.** Operators can already drive a Tree through `WIFI_SET`, `ORACLE_SET`, `STATUS`, `SAMPLE_NOW`, `REBOOT` via the serial console. Orchard View (Phase 4) will wrap this in a UI, but the underlying machinery is proven.

### Carry-over questions (parked, not blocking)

- *Auto-reset on the WROOM board — worth investigating the CP210x DTR/RTS timing? Or just document the manual BOOT-hold procedure as the standard for this board? (For now: documented procedure is fine.)*

---

## 2026-05-27 — First flash attempt: C++17 fix landed, wrong-chip detection saved us

### Successes

- **PlatformIO toolchain bootstrap.** Fresh install on Python 3.14. `python -m platformio` works (pio.exe ended up in `%APPDATA%\Python\Python314\Scripts`, not on PATH — fine, we just use the `python -m` form). Espressif32 platform 6.13.0 + xtensa toolchain + Arduino-ESP32 v3.20017 framework downloaded and cached (~300MB, one-time).
- **First compile uncovered a real bug.** sensor.h used `std::make_unique` (C++14+) but Arduino-ESP32 v2.x defaults to gnu++11. Fix: `build_unflags = -std=gnu++11` + `build_flags = -std=gnu++17` in `platformio.ini`. After the change, full clean build succeeds — every translation unit compiles, archive links, firmware.bin gets generated. **RAM 14.5% used, Flash 30.3% used** — lots of room for more sensors and features.
- **esptool's chip-ID guard worked exactly as designed.** Caught the wrong-target situation before writing a single byte to flash. Zero bricking risk on the wrong-board attempt.

### Failures / issues

- **`std::make_unique` C++14 dependency.** Already fixed (see above). Lesson: when writing firmware that uses standard-library features, explicitly set the language standard in `platformio.ini` rather than relying on the framework's defaults — Arduino-ESP32 v2.x is conservative.
- **Wrong board on COM6.** esptool refused: `This chip is ESP32, not ESP32-S3`. The board on COM6 (Silicon Labs CP210x bridge) is a **classic ESP32**, not the Freenove ESP32-S3 we built firmware for. Our target is the S3 — the one in the prototype enclosure, using a CH343 bridge.
- **USB driver state was confusing.** WCH CH343 driver showed `Status: Unknown` initially even with `wch.cn / ch343ser.inf` registered as a system driver. Resolution wasn't a driver reinstall — it was unplug + replug the board to force re-enumeration. CH343 board has shown up at COM17 in one session and not at all in others, suggesting an intermittent USB connection (cable or socket).

### Decisions

- **Target C++17 for the firmware permanently.** Modern features (`std::make_unique`, `std::optional`, structured bindings, `if constexpr`) are worth the small compile-time overhead. Documented in `platformio.ini` comments.
- **No build env for classic ESP32 yet.** The firmware leans on USB-CDC-on-boot and S3-only behaviors. Adding a classic-ESP32 env is real work (pin remapping, no native USB) and we don't need it for v1. If a contributor wants to support classic ESP32 later, they add `[env:esp32_classic]` and gate the S3-specific bits with `#if CONFIG_IDF_TARGET_ESP32S3`. Filing as a possible v1.x add.

### Carry-over questions (parked, not blocking)

- *What's on the classic ESP32 (COM6)? Project / use case for it? Worth supporting as a non-S3 Tree variant later?*
- *CH343 enumeration intermittency — bad cable, flaky USB-C socket, or PC USB port? Try a known-good cable first; if still flaky, the board's USB-C socket may need reflowing.*

---

## 2026-05-27 — GitHub repo renamed `DeMeterData` → `the-orchard`

### Successes

- **Repo renamed in GitHub Settings** by Richard. New canonical URL: https://github.com/FlipThisCrypto/the-orchard. GitHub auto-redirects the old `DeMeterData` URL, so any existing clones, badges, or external links keep resolving.
- **Local `origin` remote updated** to the new URL via `git remote set-url`. `git fetch origin` works against the new name. No history rewrite needed.
- **Doc references swept.** README quickstart, CONTRIBUTING.md, ADR-0001, and the `project_orchard_overview` memory file now use the new URL.

### Notes

- **Earlier LOG entries are deliberately not rewritten.** When the kickoff entry says "Public GitHub at .../DeMeterData", that's the truth as of that timestamp. Editing history breaks the value of the LOG.
- **`origin/HEAD`** on the new repo still points at `main` — no remote-side cleanup needed.

---

## 2026-05-27 — Phase 2: Tree firmware (initial)

### Successes

- **Phase 2 firmware committed.** PlatformIO + Arduino-ESP32 framework, targeting `esp32-s3-devkitc-1` (closest PlatformIO board match for Freenove ESP32-S3 — pin mappings line up).
- **Modular sensor architecture working as designed.** `SensorRegistry` + static `AutoRegister<>` instances mean each driver is one `.cpp` + one registration line, no central if-else. Two active drivers landed: MQ-135 (analog air quality) and GPS NEO (UART NMEA, parsed by TinyGPSPlus).
- **Identity layer.** Per-Tree `node_id` (16 random bytes, hex-encoded) and 32-byte signing secret generated on first boot, persisted to NVS via the `Preferences` library, never transmitted over the network. Secret only ever leaves the device over the local USB-serial console (via the `KEY` command) during registration.
- **Signed POSTs.** Each `/readings` request carries `X-Orchard-Sig: HMAC-SHA256(secret, body)` using `mbedtls/md.h` (no extra crypto library).
- **Serial-console provisioning.** Line-oriented commands (`PING`, `STATUS`, `NODE_ID`, `KEY`, `WIFI_SET`, `WIFI_CLEAR`, `ORACLE_SET`, `SAMPLE_NOW`, `REBOOT`) — Orchard View (Phase 4) will drive these; meanwhile they work fine from `pio device monitor`.
- **HTTP OTA on `/ota`** + a `/health` endpoint. Dashboard pushes new firmware via a multipart POST. No auth on `/ota` — explicitly LAN-only.
- **Partition table** for 8MB flash with two 3MB OTA app slots + NVS + small SPIFFS. 4MB-flash users swap to `default.csv`.

### Decisions

- **v1 signing = HMAC-SHA256, not ed25519.** Saves ~25KB flash + one library dependency. The oracle is the v1 trust boundary per ADR-0001, so the asymmetric-key step gives v1 no security benefit. The `identity::sign(...)` interface hides the scheme so v2 can swap to ed25519 (or whatever) without touching drivers. Recorded in `firmware/README.md` and `firmware/src/identity.h`.
- **Stub drivers for AHT20 / BMP280 / BH1750 / PMS5003 deliberately not included.** No sensor wired = no honest way to test. Contributors use the existing `examples/sensor_driver/template` to add them when their hardware arrives.
- **GPS on UART1** (GPIO 4/5, baud 9600). PMS5003 reserved for UART2 (GPIO 16/17). Matches the working setup.

### Failures / open issues

- *(none yet — firmware has not been flashed to a real Tree as of this commit. First flash + bring-up will go in the next LOG entry.)*

### Carry-over questions (parked, not blocking)

- *Verify Freenove ESP32-S3 flash size (4MB vs 8MB). Default in `platformio.ini` is 8MB; adjust if the board is 4MB.*
- *Confirm GPS UART pin mapping against the actual board wiring (GPIO 4=RX, GPIO 5=TX). If the GPS already worked with the previous firmware, those are right.*

---

## 2026-05-27 — $JUICE token details + sensitive-data hygiene

### Successes

- **Read `docs/Juice Token.docx`** and extracted the full $JUICE token reference. Public-safe summary now lives at [`docs/token/JUICE.md`](token/JUICE.md). README "The token" section updated with logo, supply, Eve Coin ID.
- **Confirmed token economics anchors:**
  - Total supply: **100,000,000 JUICE** (single issuance).
  - Type: Chia CAT, mainnet.
  - Eve Coin ID: `2ff338ed6fb3161d48eed7f112d3c6077e90c517dc4534bfba8ad3975b7f5e63`.
- **Logo files added:** `docs/photos/logo.png` (transparent bg), `docs/photos/logo1.png` (dark bg), `docs/photos/Juice logo small.png`. Transparent variant wired into the README.

### Security actions taken

- **Added `docs/Juice Token.docx` to `.gitignore`.** The docx contains operator-private wallet info (wallet fingerprint, wallet id, wallet label) that should never land in a public repo. Glob patterns also catch any future `*token*.docx` and `docs/token/*-private.*`.
- **Stored operator-private $JUICE details in memory only** (`project_token_juice_private.md`). Not in the repo, not in any committed file.
- **Convention established:** `config.example.yaml` will use placeholders (`fingerprint: 0`); the real values go in `config.yaml` (gitignored).

### Failures / open issues

- *(none new this entry)*

### Lessons

- **Always scan dropped files for operator-private data before integration.** A token-creation log is the kind of file that *looks* like project docs but contains exactly the secret an attacker would want.

---

## 2026-05-27 — Vision locked, formal naming applied

### Successes

- **Vision document authored.** Captured in [VISION.md](VISION.md) and in memory at `project_vision.md`. Layered architecture (Hardware / Identity / Data / Rewards), brand naming table, long-term reward-logic factors (sensor diversity, geographic scarcity, validated submissions, reputation, Orchard Pass tier bonuses), and tokenomics direction ($JUICE fixed supply, small experimental LP first, Orchard Passes carry later utility).
- **Naming finalized — authoritative table:** Ecosystem = The Orchard, Token = $JUICE, Nodes = **Trees**, Node Clusters = **Groves**, Reward Cycles = **Seasons**, Data Collection = **Harvest**, Validators = **Keepers**, Dashboard = **Orchard View**, Sensor NFTs = **Orchard Passes**.
- **Cascade applied:** README rewritten with Glossary section + vision teaser; ADR-0001 updated (Season, Orchard Pass, $JUICE, Tree); all module READMEs updated; tasks #4-#7 renamed; memory files synced. Earlier "sapling" proposal removed everywhere (only historical mentions remain in this LOG below).
- **Resolved carryover questions:** $JUICE Asset ID (`285164e6af80202d2b07fa3cc6ae47ff2906029365a83c50fcab25a56b937121`); antenna is WiFi/BT + corded GPS (no LoRa).

### Decisions

- **Code vs brand language separation.** User-facing copy (READMEs, dashboard UI, marketing) uses Trees / Orchard Passes / Seasons. Code (variables, JSON keys, DB tables) uses `node` / `pass` / `season`. README has a Glossary mapping them.
- **Reserved Orchard Pass attributes** (`Tier`, `Reward Multiplier`, `Sensor Manifest`, `Geographic Region`, `Reputation Score`) documented in `nft/README.md` so v1 mints stay forward-compatible with vision-era features without breaking collection metadata.

### Carry-over questions (parked, not blocking)

- *GitHub repo rename `DeMeterData` → `the-orchard` (or similar)? Cosmetic, GitHub auto-redirects old URL.*
- *Local working folder rename `I:\DeMeter Data\Chia DePIN` → something Orchard-themed? Cosmetic.*
- *Commit + push approval — still pending.*

---

## 2026-05-27 — Project rename + new facts in

### Successes

- **Project renamed:** "DeMeter Data" → **"The Orchard"**. Cascaded through README, LICENSE, CONTRIBUTING, ADR-0001, and all module READMEs. Token name **$JUICE** integrated. Memory and ADR document the original name so the history isn't lost.
- **Token confirmed:** $JUICE on Chia mainnet, asset id `285164e6af80202d2b07fa3cc6ae47ff2906029365a83c50fcab25a56b937121`. Now lives in the README + docs; will live in `chia/config.example.yaml` once Phase 5 starts.
- **Antenna identification:** the larger ~4" antenna in the prototype photo is a **WiFi/Bluetooth** antenna; the corded one is the GPS antenna. No LoRa module installed.
- **Naming theme established:** project = The Orchard, token = $JUICE, nodes = "saplings" (proposed; awaiting Richard's sign-off), NFT collection = "The Orchard — Genesis Saplings" (proposed).

### Failures / open issues

- *(none new this entry)*

### Decisions

- **No LoRa pin reservation in v1.** Confirmed no LoRa module exists yet. Firmware's modular radio interface keeps LoRa addable later without reserving pins now. PMS5003 gets UART2 instead of fighting for it.
- **Sapling naming.** Proposed convention: NFT credentials are called "saplings", deployed nodes are called "trees" (mature saplings). Token harvested = $JUICE. Pending Richard's final approval.

### Carry-over questions (parked, not blocking)

- *Confirm sapling/tree naming, or pick alternative.*
- *Rename local working folder `I:\DeMeter Data\Chia DePIN` → something Orchard-themed? (Cosmetic, can wait.)*
- *Rename GitHub repo `DeMeterData` → `the-orchard` (or similar)? Old URL auto-redirects via GitHub.*

---

## 2026-05-27 — Project kickoff

### Successes

- **Hardware bring-up:** Freenove ESP32-S3 in clear enclosure, GPS (NEO series) + MQ-135 wired and powered. GPS is producing valid NMEA ($GPGSV, $GPGLL, $GPRMC) with a stable fix in Mount Washington, KY. MQ-135 readings observed.
- **Architecture decisions locked.** See [decisions/0001-v1-architecture.md](decisions/0001-v1-architecture.md).
- **Repo created.** Public GitHub at https://github.com/FlipThisCrypto/DeMeterData.
- **License chosen:** Apache 2.0 (patent grant matters for an infrastructure project).
- **Chia infra confirmed running:** full node + DataLayer service active on the same dev PC as the dashboard — RPCs available on localhost.
- **CAT token already minted** on Chia mainnet, with tokens in Richard's wallet ready for first payouts.

### Failures / open issues

- **Previous oracle was returning 500/422.** The old backend was repurposed from another project, so its schema didn't match what the ESP32 was sending. Confirmed dead — being rebuilt from scratch in Phase 3. Lesson: a small purpose-built service beats a misaligned reuse.
- **BH1750 light sensor logged "Device is not configured!"** — root cause is that it isn't wired yet, not a software bug. Will resolve when sensor is physically connected (Phase 2 wiring docs).
- **No automatic detection for analog sensors.** Confirmed that I2C devices can be enumerated (bus scan + address-to-type lookup) and UART devices can be sniffed (NMEA / PMS5003 signature detection), but analog sensors like MQ-135 require user declaration. Dashboard will include a sensor-declaration form.

### Decisions

- **v1 deployment scope:** 1–5 mains-powered WiFi nodes near Richard. Firmware kept modular for future LoRa / battery / off-grid scenarios.
- **Reward distribution v1:** manual batched CAT spend bundle from Richard's wallet, no Chialisp claim contract yet.
- **DataLayer scope v1:** daily uptime attestations only. Raw sensor data stays in the local oracle SQLite DB.
- **NFT credential:** new collection to be designed and minted. One NFT per wallet, enforced at registration time.
