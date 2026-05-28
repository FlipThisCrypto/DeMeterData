# The Orchard — Development Log

> Running journal of what worked, what failed, and what we learned. Newest entries on top. Append liberally — failures are as instructive as successes. Format: a date heading, then short bullet points. Keep entries scannable.

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
