# Directory Structure (delete this file once scaffolded)

```
chaff/
├── CLAUDE.md
├── SPEC.md
├── README.md
├── pyproject.toml
├── src/
│   └── chaff/
│       ├── __init__.py
│       ├── cli.py          # Typer app, all commands
│       ├── identity.py     # Faker-based persona generation
│       ├── browser.py      # Patchright signup flow
│       ├── storage.py      # SQLite CRUD
│       ├── warmup.py       # Post-creation account warming
│       ├── config.py       # Settings, paths, proxy config
│       └── exceptions.py   # Typed exceptions
└── tests/
    ├── test_identity.py
    └── test_storage.py
```
