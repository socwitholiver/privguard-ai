"""Retention and deletion policy operations."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from config_loader import load_system_config
from storage.db import get_conn, init_db


SYSTEM_CONFIG = load_system_config()
RETENTION = SYSTEM_CONFIG["retention"]


def _cleanup_files(days: int) -> Dict[str, int]:
    deleted = 0
    scanned = 0
    cutoff = datetime.now() - timedelta(days=days)
    for directory in RETENTION["cleanup_directories"]:
        path = Path(directory)
        if not path.exists():
            continue
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            scanned += 1
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            if modified < cutoff:
                try:
                    os.remove(file_path)
                    deleted += 1
                except OSError:
                    continue
    return {"files_scanned": scanned, "files_deleted": deleted}


def _cleanup_audit(days: int) -> Dict[str, int]:
    init_db()
    with get_conn() as conn:
        before = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        conn.execute(
            """
            DELETE FROM audit_events
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{days} day",),
        )
        after = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

        before_scan = conn.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0]
        conn.execute(
            """
            DELETE FROM scan_events
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{days} day",),
        )
        after_scan = conn.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0]

    return {
        "audit_deleted": int(before - after),
        "scan_events_deleted": int(before_scan - after_scan),
    }


def run_retention_cleanup() -> Dict[str, object]:
    audit_days = int(RETENTION["audit_retention_days"])
    file_days = int(RETENTION["file_retention_days"])
    file_report = _cleanup_files(file_days)
    audit_report = _cleanup_audit(audit_days)
    return {
        "audit_retention_days": audit_days,
        "file_retention_days": file_days,
        "file_cleanup": file_report,
        "audit_cleanup": audit_report,
    }
