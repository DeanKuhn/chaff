# CLAUDE.md — Chaff

## What This Is
Semi-automated Gmail account creator for privacy decoy infrastructure. Built for Kanary's denial & deception workflow. Creates believable identities, automates the signup flow via stealth browser, pauses for manual phone/QR verification, logs credentials to local store.

## Stack
- Python 3.11+
- Patchright (stealth Playwright fork, Chromium only)
- Faker (identity generation)
- SQLite (credential + identity storage)
- Typer + Rich (CLI + terminal UI)

## Architecture
```
src/chaff/
  cli.py        — Typer CLI entrypoint
  identity.py   — fake identity generation (name, DOB, username, backup email)
  browser.py    — Patchright signup flow automation
  storage.py    — SQLite read/write for identities + credentials
  warmup.py     — post-creation account warming (login, accept terms)
  config.py     — settings, proxy config, paths
```

## Hard Rules
- Never store plaintext passwords in source code
- All credentials go to SQLite DB at `~/.chaff/chaff.db`
- Browser sessions use residential proxies when configured; never use datacenter IPs
- Patchright only — do not use vanilla Playwright or Selenium
- One account per browser context; close and recreate between runs
- All CLI commands go through Typer; no bare scripts

## Conventions
- Type hints everywhere
- Async by default (Patchright async API)
- Errors raise typed exceptions from `exceptions.py`, caught at CLI layer
- Logging via stdlib `logging`, not print statements

## Key Decisions
- SQLite over JSON: need querying (find accounts by status, age, proxy used)
- Typer over Click: less boilerplate, built-in Rich support
- Faker over hand-rolled: locale support, consistent API, less maintenance
- Pause/resume at verification via Rich prompt, not a web UI
