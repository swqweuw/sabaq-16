from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / 'instance' / 'coffeelab.sqlite3'


def open_connection(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path), timeout=8, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA busy_timeout = 8000')
    return db


@contextmanager
def database_session(path: str | Path):
    db = open_connection(path)
    try:
        yield db
    finally:
        db.close()


def initialize_database(path: str | Path = DEFAULT_DB) -> None:
    database = Path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    with database_session(database) as db:
        present = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='products'").fetchone()
        if present is None:
            db.executescript((PROJECT_ROOT / 'db' / 'schema.sql').read_text(encoding='utf-8'))
            db.executescript((PROJECT_ROOT / 'db' / 'seed.sql').read_text(encoding='utf-8'))
