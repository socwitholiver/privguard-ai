"""SQLite persistence for PRIVGUARD AI audit, scan, and vault records."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config_loader import load_system_config


SYSTEM_CONFIG = load_system_config()
DB_PATH = Path(SYSTEM_CONFIG["audit"]["database_path"])


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    # SQLite runs with foreign keys disabled by default, so init_db/get_conn enable it explicitly.
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})")
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
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
        _ensure_column(conn, "scan_events", "counts_json", "TEXT NOT NULL DEFAULT '{}' ")
        _ensure_column(conn, "scan_events", "document_id", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                original_filename TEXT NOT NULL,
                original_path TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                total_sensitive_items INTEGER NOT NULL,
                counts_json TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                primary_action TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SCANNED',
                actor TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'Operations',
                department TEXT NOT NULL DEFAULT 'Operations',
                retention_days INTEGER NOT NULL DEFAULT 180,
                retention_until TEXT,
                expiry_action TEXT NOT NULL DEFAULT 'review',
                policy_name TEXT NOT NULL DEFAULT 'Default retention policy',
                lifecycle_status TEXT NOT NULL DEFAULT 'active',
                lifecycle_next_action TEXT NOT NULL DEFAULT 'Monitor lifecycle',
                archive_path TEXT NOT NULL DEFAULT '',
                archived_at TEXT,
                deleted_at TEXT
            )
            """
        )
        _ensure_column(conn, "documents", "owner", "TEXT NOT NULL DEFAULT 'Operations'")
        _ensure_column(conn, "documents", "department", "TEXT NOT NULL DEFAULT 'Operations'")
        _ensure_column(conn, "documents", "retention_days", "INTEGER NOT NULL DEFAULT 180")
        _ensure_column(conn, "documents", "retention_until", "TEXT")
        _ensure_column(conn, "documents", "expiry_action", "TEXT NOT NULL DEFAULT 'review'")
        _ensure_column(conn, "documents", "policy_name", "TEXT NOT NULL DEFAULT 'Default retention policy'")
        _ensure_column(conn, "documents", "lifecycle_status", "TEXT NOT NULL DEFAULT 'active'")
        _ensure_column(conn, "documents", "lifecycle_next_action", "TEXT NOT NULL DEFAULT 'Monitor lifecycle'")
        _ensure_column(conn, "documents", "archive_path", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "documents", "archived_at", "TEXT")
        _ensure_column(conn, "documents", "deleted_at", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(document_id) REFERENCES documents(document_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_document_type ON document_artifacts(document_id, artifact_type)"
        )
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
