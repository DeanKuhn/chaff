import tomllib
from dataclasses import dataclass
from pathlib import Path

CHAFF_DIR = Path.home() / ".chaff"
DB_PATH = CHAFF_DIR / "chaff.db"
CONFIG_PATH = CHAFF_DIR / "config.toml"


def ensure_dirs() -> None:
    CHAFF_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    proxy_url: str | None = None
    proxy_enabled: bool = False
    headless: bool = False
    slow_mo: int = 50
    timeout: int = 30000
    locale: str = "en_US"


def load_config(path: Path | None):
    if path is None:
        return Settings()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    return Settings(**data)
