from datetime import datetime, timezone

import storage.audit_repo as audit_repo
import storage.db as db


def test_archive_expired_audit_events_writes_month_file_and_clears_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "instance" / "audit.db")
    monkeypatch.setattr(audit_repo, "ARCHIVE_ROOT", tmp_path / "audit activity")
    monkeypatch.setattr(audit_repo, "AUDIT_RETENTION_DAYS", 30)
    db.init_db()

    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (created_at, event_type, actor, source, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-03-01 10:00:00", "scan", "tester", "web", '{"document_id": "PG-2026-00001"}'),
        )
        conn.execute(
            """
            INSERT INTO audit_events (created_at, event_type, actor, source, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-04-10 10:00:00", "scan", "tester", "web", '{"document_id": "PG-2026-00002"}'),
        )

    archived = audit_repo.archive_expired_audit_events(now=datetime(2026, 4, 15, tzinfo=timezone.utc))

    assert archived == 1
    archive_path = tmp_path / "audit activity" / "2026" / "March.txt"
    assert archive_path.exists()
    archive_text = archive_path.read_text(encoding="utf-8")
    assert "PrivGuard Audit Archive - March 2026" in archive_text
    assert "PG-2026-00001" in archive_text

    with db.get_conn() as conn:
        rows = conn.execute("SELECT details_json FROM audit_events ORDER BY id ASC").fetchall()

    assert len(rows) == 1
    assert "PG-2026-00002" in rows[0][0]
