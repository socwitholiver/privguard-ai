"""Signed audit export utilities."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config_loader import load_system_config
from security.keys import get_or_create_signing_key
from storage.db import get_conn, init_db


SYSTEM_CONFIG = load_system_config()
EXPORT_DIR = Path(SYSTEM_CONFIG["export"]["export_dir"])


def _fetch_audit_events(limit: int = 1000) -> List[Dict[str, object]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, event_type, actor, source, details_json
            FROM audit_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    events = []
    for row in rows:
        events.append(
            {
                "id": row[0],
                "created_at": row[1],
                "event_type": row[2],
                "actor": row[3],
                "source": row[4],
                "details": json.loads(row[5]),
            }
        )
    return events


def export_signed_audit(limit: int = 1000) -> Dict[str, str]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = _fetch_audit_events(limit=limit)
    payload = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "event_count": len(events),
        "events": events,
    }
    serialized = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = EXPORT_DIR / f"audit_export_{timestamp}.json"
    sig_path = EXPORT_DIR / f"audit_export_{timestamp}.sig"
    export_path.write_bytes(serialized)

    key = get_or_create_signing_key()
    signature = hmac.new(key, serialized, hashlib.sha256).hexdigest()
    sig_path.write_text(signature, encoding="utf-8")
    return {"export_file": str(export_path), "signature_file": str(sig_path)}
