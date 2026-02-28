"""Audit repository helpers."""

from __future__ import annotations

import json
from typing import Any, Dict

from storage.db import get_conn, init_db


def log_audit_event(event_type: str, actor: str, source: str, details: Dict[str, Any]) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (event_type, actor, source, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, actor, source, json.dumps(details)),
        )


def log_scan_event(
    filename: str,
    risk_level: str,
    risk_score: int,
    total_sensitive_items: int,
    source: str,
) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO scan_events
            (filename, risk_level, risk_score, total_sensitive_items, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (filename, risk_level, risk_score, total_sensitive_items, source),
        )
