# Chaff — Technical Spec

## Identity Generation

Each identity is a coherent persona:

| Field | Source | Example |
|-------|--------|---------|
| first_name | Faker, locale-matched | "Sarah" |
| last_name | Faker | "Mitchell" |
| dob | Random, age 22-55 | 1987-03-14 |
| gender | Random | "F" |
| username | Derived: first.last + 2-4 digits | sarah.mitchell847 |
| backup_email | Optional, from existing chaff accounts or ProtonMail | — |
| phone | Placeholder, filled during manual step | — |
| proxy | Assigned from proxy pool if configured | — |

Username generation must avoid patterns. Vary the format: `firstlast`, `first.last`, `flast`, `firstl` + digits. Check availability isn't feasible pre-signup; handle conflicts in the browser flow.

## Signup Flow (browser.py)

Target URL: `https://accounts.google.com/signup`

Steps:
1. Launch Patchright Chromium with stealth config (`channel="chrome"`, `headless=False`)
2. Set proxy if configured
3. Navigate to signup
4. Fill first name, last name → Next
5. Fill DOB, gender → Next
6. Select "Create your own Gmail address" → fill username
7. Fill password (generated, 16+ chars, mixed) → Next
8. **PAUSE** — phone/QR verification screen detected
9. Alert operator via Rich console: "Manual verification required. Complete in browser, then press Enter."
10. Wait for operator input
11. Detect post-verification screen (recovery email, skip, agree to terms)
12. Complete remaining steps automatically
13. Capture and store final confirmed email address
14. Close browser context

### Detection Avoidance
- Use `channel="chrome"` (real Chrome, not Chromium)
- Randomize viewport size within realistic ranges (1280-1920 x 720-1080)
- Add random delays between actions (0.5-2.5s, not uniform)
- Randomize typing speed per character
- Use residential proxy if available

### Failure Modes
- Username taken → generate new username, retry (max 3)
- CAPTCHA appears → pause for manual solve (same as verification)
- Account suspended immediately → log failure, move on
- Page structure changed → raise `FlowChangedError`, log screenshot

## Storage Schema (SQLite)

```sql
CREATE TABLE identities (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    gender TEXT,
    username TEXT NOT NULL,
    proxy_used TEXT,
    status TEXT DEFAULT 'created',  -- created | verified | warmed | burned | failed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_active TEXT,
    notes TEXT
);
```

Passwords stored as-is in SQLite (local DB, not a server). If encryption needed later, use Fernet with a master key.

## CLI Commands

```
chaff create [--count N] [--proxy URL] [--headless]
    Create N identities (default 1). Opens browser per account.

chaff list [--status STATUS] [--json]
    List stored identities, optionally filtered.

chaff warm ID
    Login to account, perform basic activity (accept terms, visit inbox).

chaff export [--format csv|json]
    Export identity table.

chaff status ID
    Show full details for one identity.
```

## Proxy Config

Optional. Set via `--proxy` flag or `~/.chaff/config.toml`:

```toml
[proxy]
server = "http://user:pass@proxy.example.com:8080"
# or rotate from a list
pool = [
    "http://user:pass@us1.proxy.com:8080",
    "http://user:pass@us2.proxy.com:8080",
]
```

## What's Out of Scope (For Now)
- Inbox monitoring / signal detection (Layer 3)
- Profile seeding on LinkedIn/Zillow (Layer 2)
- Decoy maintenance and rotation (Layer 4)
- Solving the QR verification programmatically
- Android emulator flows
