"""Audit repository helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from config_loader import load_system_config
from security.vault import ensure_vault_layout, get_vault_paths
from storage.db import get_conn, init_db


SYSTEM_CONFIG = load_system_config()
AUDIT_CONFIG = SYSTEM_CONFIG.get("audit", {})
RETENTION_CONFIG = SYSTEM_CONFIG.get("retention", {})
LOG_FILE_PATH = get_vault_paths()["logs"] / "privguard-events.jsonl"
ARCHIVE_ROOT = Path(AUDIT_CONFIG.get("archive_root", "audit activity"))
AUDIT_RETENTION_DAYS = int(RETENTION_CONFIG.get("audit_retention_days", 30))


def _append_log_line(payload: Dict[str, Any]) -> None:
    ensure_vault_layout()
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _archive_path_for(timestamp: datetime) -> Path:
    year_dir = ARCHIVE_ROOT / str(timestamp.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    return year_dir / f"{timestamp.strftime('%B')}.txt"


def archive_expired_audit_events(now: datetime | None = None) -> int:
    init_db()
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=AUDIT_RETENTION_DAYS)

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, event_type, actor, source, details_json
            FROM audit_events
            ORDER BY created_at ASC, id ASC
            """
        ).fetchall()

        expired = []
        for row in rows:
            created_at = _parse_timestamp(str(row[1]))
            if created_at <= cutoff:
                expired.append(
                    {
                        "id": row[0],
                        "created_at": created_at,
                        "event_type": row[2],
                        "actor": row[3],
                        "source": row[4],
                        "details": json.loads(row[5] or "{}"),
                    }
                )

        if not expired:
            return 0

        grouped: dict[Path, list[dict]] = defaultdict(list)
        for record in expired:
            grouped[_archive_path_for(record["created_at"])].append(record)

        for archive_path, records in grouped.items():
            with archive_path.open("a", encoding="utf-8") as handle:
                if archive_path.stat().st_size == 0:
                    month_label = records[0]["created_at"].strftime("%B %Y")
                    handle.write(f"PrivGuard Audit Archive - {month_label}\n")
                    handle.write("=" * 72 + "\n\n")
                for record in records:
                    handle.write(f"Timestamp: {record['created_at'].isoformat()}\n")
                    handle.write(f"Event: {record['event_type']}\n")
                    handle.write(f"Actor: {record['actor']}\n")
                    handle.write(f"Source: {record['source']}\n")
                    if record["details"].get("document_id"):
                        handle.write(f"Document ID: {record['details']['document_id']}\n")
                    handle.write(f"Details: {json.dumps(record['details'], ensure_ascii=True)}\n")
                    handle.write("-" * 72 + "\n")

        conn.executemany(
            "DELETE FROM audit_events WHERE id = ?",
            [(record["id"],) for record in expired],
        )

    return len(expired)


def log_audit_event(event_type: str, actor: str, source: str, details: Dict[str, Any]) -> None:
    archive_expired_audit_events()
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (event_type, actor, source, details_json)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, actor, source, json.dumps(details)),
        )
    _append_log_line(
        {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "source": source,
            "details": details,
        }
    )


def log_scan_event(
    filename: str,
    risk_level: str,
    risk_score: int,
    total_sensitive_items: int,
    source: str,
    *,
    counts: Dict[str, int] | None = None,
    document_id: str | None = None,
) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO scan_events
            (filename, risk_level, risk_score, total_sensitive_items, source, counts_json, document_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                risk_level,
                risk_score,
                total_sensitive_items,
                source,
                json.dumps(counts or {}),
                document_id,
            ),
        )


def list_recent_scan_events(limit: int = 10) -> List[dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT created_at, filename, risk_level, risk_score, total_sensitive_items, source, counts_json, document_id
            FROM scan_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "created_at": row[0],
            "filename": row[1],
            "risk_level": row[2],
            "risk_score": row[3],
            "total_sensitive_items": row[4],
            "source": row[5],
            "counts": json.loads(row[6] or "{}"),
            "document_id": row[7],
        }
        for row in rows
    ]


def summarize_scan_events(limit: int = 50) -> dict:
    events = list_recent_scan_events(limit=limit)
    risk_distribution = {"High": 0, "Medium": 0, "Low": 0}
    avg_risk_score = 0.0
    entity_totals: Dict[str, int] = {
        "national_ids": 0,
        "phone_numbers": 0,
        "emails": 0,
        "kra_pins": 0,
        "passwords": 0,
        "financial_info": 0,
        "personal_names": 0,
    }

    for entry in events:
        level = str(entry.get("risk_level", "Low"))
        if level in risk_distribution:
            risk_distribution[level] += 1
        avg_risk_score += float(entry.get("risk_score", 0))
        for key in entity_totals:
            entity_totals[key] += int(entry.get("counts", {}).get(key, 0))

    total_scans = len(events)
    return {
        "documents_scanned": total_scans,
        "average_risk_score": round(avg_risk_score / total_scans, 2) if total_scans else 0.0,
        "high_risk_ratio": round((risk_distribution["High"] / total_scans) * 100, 2) if total_scans else 0.0,
        "risk_distribution": risk_distribution,
        "entity_totals": entity_totals,
        "trend_scores": [int(entry.get("risk_score", 0)) for entry in reversed(events)],
    }


def list_recent_audit_events(limit: int = 25) -> List[dict]:
    archive_expired_audit_events()
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT created_at, event_type, actor, source, details_json
            FROM audit_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    records = []
    for row in rows:
        details = json.loads(row[4] or "{}")
        records.append(
            {
                "created_at": row[0],
                "event_type": row[1],
                "actor": row[2],
                "source": row[3],
                "details": details,
                "document_id": details.get("document_id"),
            }
        )
    return records
