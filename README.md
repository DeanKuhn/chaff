# Chaff

> **chaff** /tʃæf/ *noun* — strips of metal foil or similar material released in the air to confuse enemy radar. A countermeasure designed to obscure the real signal with noise.

Chaff is an automated identity factory for privacy defense, built to create believable Gmail-backed decoy personas at scale, seed them across the platforms data brokers scrape, and monitor their inboxes as sensors that detect when and how personal data gets harvested.

Designed for [Kanary's](https://www.kanary.com) denial & deception strategy, Chaff is the first layer of a larger system: flood the data broker graph with convincing noise until the real signal is impossible to isolate.

## Why this exists

Google replaced SMS verification with QR-based phone verification for Gmail signup, breaking existing automated account creation pipelines. SMS API services (5sim, sms-activate, etc.) only support receiving codes, while Google's new flow requires sending an SMS to a Google short code. This means that a physical device or SIM card is needed.

This is the bottleneck blocking Kanary's denial & deception workflow. Creating decoy identities by hand is slow and inefficient, and still requires constant SMS swapping, routing through different IPs, changing device fingerprint, and more. Chaff automates everything around the verification step: identity generation, form filling, anti-detection, and post-creation warmup. Additionally, Chaff handles verification through a physical Android phone over ADB (with opportunity for a dedicated modem), cutting creation time significantly.

## How it works

1. **Identity Generation** - Faker produces a coherent persona (with the option to enter first and last name manually): name, DOB, gender. A randomized username derived from the produced persona (typically a combination of first name + last name + digits) is then created and used in Gmail creation.
2. **Stealth Browser Session** - Patchright launches a real Chrome instance with a randomized device fingerprint (viewport, screen resolution, color scheme, etc). The program mimics real human typing speed and delays. A residential proxy can be used if configured.
3. **Automated Signup** - The Patchright script fills the Google signup forms automatically, detecting optional forms and handling username conflicts.
4. **QR Verification** - When presented with the QR code, Chaff screenshots it, decodes the URL, opens the page, and intercepts the response, extracting the short code and message body.
5. **SMS via ADB** - The script then sends the required SMS from a physical Android phone connected over USB (also configurable for larger volume with a dedicated modem). The script has been tested with Termux. If the phone does not have Termux installed, it falls back to a raw telephony API call via `service call isms` (untested).
6. **Post Creation Warmup** - Immediately after account creation, Chaff will browse several Google properties (YouTube, Gmail, Drive) in the same session. Accounts that skip this step get flagged and disabled within seconds.
7. **Storage** - All fake persona identities, credentials, and custom device profiles are stored in a local SQLite database at ~/.chaff/chaff.db.

## Architecture

```
src/chaff/
  cli.py          — Typer CLI entrypoint, all commands route through here
  identity.py     — Fake persona generation (name, DOB, username, backup email)
  browser.py      — Patchright signup flow automation + post-creation warmup
  fingerprint.py  — Device profile generation and management (viewport, screen res, color scheme)
  sms.py          — SMS sending abstraction (ADB/Termux backend, extensible for modem)
  storage.py      — SQLite read/write for identities, credentials, and device profiles
  warmup.py       — Standalone account warming (login, browse Google properties)
  gmail.py        — Gmail API auth + verification code fetching for recovery email
  config.py       — Settings, proxy config, file paths
  utils.py        — Shared helpers (delays, human-like timing)
  exceptions.py   — Typed exceptions, caught at CLI layer
```

The flow is linear: `cli` → `identity` → `browser` (which calls `fingerprint`, `sms`, and `utils` internally) → `storage`. `warmup` and `gmail` are used for post-creation account maintenance.

## Install

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Android phone with Termux + Termux:API installed, connected via USB
- ADB installed and device authorized (`adb devices` shows your phone)
- Residential proxy recommended (home IP burns fast)

### Setup

```bash
git clone https://github.com/deankuhn/chaff.git
cd chaff
uv sync
patchright install chrome
```

### Gmail API Setup (optional, for recovery email verification)

The warmup flow can fetch verification codes from a recovery Gmail inbox automatically. To enable this:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project
2. Enable the **Gmail API** for that project
3. Create an **OAuth 2.0 Client ID** (Desktop application type)
4. Download the credentials JSON and save it to `~/.chaff/client_secret.json`
5. On first run of `chaff warmup`, a browser window will open for OAuth consent — the resulting token is saved to `~/.chaff/token.json` automatically

## Usage

```bash
# Create one account (opens browser, pauses at verification)
chaff create

# Create 3 accounts through a proxy
chaff create --count 3 --proxy http://user:pass@proxy:8080

# Create with a specific locale and backup email
chaff create --locale en_GB --backup-email backup@gmail.com

# List all accounts
chaff list

# List by status
chaff list --status created
```

### Warmup

Newly created accounts need activity to survive — Google flags accounts that create and immediately go silent. The warmup command logs into an account, handles any verification prompts (fetching codes from the recovery email via Gmail API if configured), and browses Google properties to build a usage history.

```bash
# Warm a specific account
chaff warmup --email user@gmail.com

# Warm all accounts with a given status
chaff warmup --status created

# Update an account's status manually
chaff update --cred-id 1 --status burned
```

## Roadmap

Chaff is Layer 1 of a four-layer system:

| Layer | What | Status |
|-------|------|--------|
| **1. Identity Factory** | Generate personas, automate Gmail signup, warm accounts | **Active** — core flow works end-to-end |
| **2. Deployment** | Seed decoys on platforms data brokers scrape (LinkedIn, property sites, public records) | Planned |
| **3. Inbox Monitoring** | Poll decoy inboxes as sensors — classify scraper noise vs. broker harvesting vs. targeted probes | Planned |
| **4. Coordination** | Keep decoys alive, sync with client movements, detect and rotate burned identities | Planned |

### Near-term priorities
- **SMS scaling** — GSM modem support for SIM rotation (physical SIMs exhaust at ~4 accounts per number)
- **Proxy management** — Residential proxy pool rotation with geo-matching to fingerprint
- **Account survival** — Longer warmup sequences, scheduled re-warming, activity patterns that mimic real users

### Longer-term
- Programmatic data broker graph mapping (which platforms feed which brokers)
- Inbox signal classification via Gmail API push notifications
- Multi-client coordination with minimal analyst intervention
