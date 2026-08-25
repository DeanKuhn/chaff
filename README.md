# Chaff

> **chaff** /tʃæf/ *noun* — strips of metal foil or similar material released in the air to confuse enemy radar. A countermeasure designed to obscure the real signal with noise.

Semi-automated Gmail account creator for privacy decoy infrastructure.

Creates believable fake identities, automates the Google signup flow via stealth browser, pauses for manual verification, and stores credentials locally. Designed as the identity factory layer for [Kanary's](https://www.kanary.com) denial & deception privacy strategy.

## Install

```bash
git clone https://github.com/yourorg/chaff.git
cd chaff
pip install -e .
patchright install chrome
```

## Usage

```bash
# Create one account (opens browser, pauses for verification)
chaff create

# Create 5 accounts with a proxy
chaff create --count 5 --proxy http://user:pass@proxy:8080

# List created accounts
chaff list

# Warm an account (login, basic activity)
chaff warm 1
```

## How It Works

1. Generates a coherent fake identity (name, DOB, username)
2. Launches a stealth Chrome session via Patchright
3. Fills the Gmail signup form automatically
4. Pauses at phone/QR verification for manual completion
5. Finishes signup and logs credentials to `~/.chaff/chaff.db`

## Context

Built from insights shared at HOPE 26 by Kanary's CEO. Google's move from SMS to QR-based verification broke automated account creation pipelines. This tool accepts that constraint — it automates everything *around* the verification step to cut per-account creation time from ~10 minutes to ~2-3 minutes.

## Disclaimer

This tool is for authorized privacy research and defensive security purposes. Creating Google accounts via automation may violate Google's Terms of Service. Use responsibly and in accordance with applicable laws.
