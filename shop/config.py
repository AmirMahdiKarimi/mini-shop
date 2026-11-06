"""Application-wide configuration."""

from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent.parent / "shop.sqlite3"
