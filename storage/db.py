"""SQLite persistence for PRIVGUARD AI audit and scan events."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config_loader import load_system_config


SYSTEM_CONFIG = load_system_config()
DB_PATH = Path(SYSTEM_CONFIG["audit"]["database_path"])


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                source TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                total_sensitive_items INTEGER NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
