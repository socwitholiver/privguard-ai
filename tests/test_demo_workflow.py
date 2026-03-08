import sqlite3

import automation.demo_workflow as demo_workflow
from detection import detect_sensitive_data


def _create_demo_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT)")
        conn.execute("CREATE TABLE scan_events (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT)")
        conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT)")
        conn.execute("CREATE TABLE document_artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT)")
        conn.execute("INSERT INTO audit_events (event_type) VALUES ('scan')")
        conn.execute("INSERT INTO scan_events (filename) VALUES ('payroll_001.txt')")
        conn.execute("INSERT INTO documents (document_id) VALUES ('PG-2026-00001')")
        conn.execute("INSERT INTO document_artifacts (document_id) VALUES ('PG-2026-00001')")
        conn.commit()


def test_ensure_demo_watch_folder_builds_sensitive_dataset(tmp_path):
    watch_folder = tmp_path / "WATCH FOLDER"

    summary = demo_workflow.ensure_demo_watch_folder(watch_folder=watch_folder, target_count=10)

    assert summary["seeded_file_count"] == 10
    assert summary["created"] == 10
    assert len(list(watch_folder.iterdir())) == 10

    payroll_text = (watch_folder / "payroll_001.txt").read_text(encoding="utf-8")
    findings = detect_sensitive_data(payroll_text)

    assert findings["national_ids"]
    assert findings["kra_pins"]
    assert findings["passwords"]
    assert findings["financial_info"]



def test_ensure_demo_watch_folder_fills_missing_files_in_sparse_legacy_folder(tmp_path):
    watch_folder = tmp_path / "WATCH FOLDER"
    watch_folder.mkdir()
    for name in ("admissions_001.txt", "payroll_001.txt", "legacy_notes.txt"):
        (watch_folder / name).write_text("legacy", encoding="utf-8")

    summary = demo_workflow.ensure_demo_watch_folder(watch_folder=watch_folder, target_count=8)

    assert summary["seeded_file_count"] == 8
    assert summary["created"] == 5
    files = list(watch_folder.iterdir())
    assert len(files) == 8
    demo_files = [path for path in files if path.name != "legacy_notes.txt"]
    assert demo_files
    assert all(path.suffix == ".txt" for path in demo_files)
def test_rebuild_demo_workspace_resets_live_demo_assets(tmp_path):
    watch_folder = tmp_path / "WATCH FOLDER"
    watch_folder.mkdir()
    (watch_folder / "legacy.txt").write_text("legacy demo file", encoding="utf-8")

    vault_root = tmp_path / "vault"
    vault_paths = {
        "root": vault_root,
        "originals": vault_root / "Originals",
        "redacted": vault_root / "Redacted",
        "encrypted": vault_root / "Encrypted",
        "reports": vault_root / "Reports",
        "keys": vault_root / "Keys",
        "logs": vault_root / "Logs",
    }
    for key, path in vault_paths.items():
        path.mkdir(parents=True, exist_ok=True)
        if key != "root":
            (path / f"{key}.txt").write_text("stale artifact", encoding="utf-8")

    audit_archive_root = tmp_path / "audit activity"
    audit_archive_root.mkdir()
    (audit_archive_root / "March.txt").write_text("old audit archive", encoding="utf-8")

    watch_state_path = tmp_path / "instance" / "watch_folder_state.json"
    watch_state_path.parent.mkdir(parents=True, exist_ok=True)
    watch_state_path.write_text('{"enabled": true}', encoding="utf-8")

    db_path = tmp_path / "instance" / "privguard_audit.db"
    _create_demo_db(db_path)

    summary = demo_workflow.rebuild_demo_workspace(
        watch_folder=watch_folder,
        target_count=15,
        vault_paths=vault_paths,
        db_path=db_path,
        watch_state_path=watch_state_path,
        audit_archive_root=audit_archive_root,
    )

    assert summary["seeded_file_count"] == 15
    assert summary["removed_watch_files"] == 1
    assert summary["watch_state_reset"] is True
    assert len(list(watch_folder.iterdir())) == 15
    assert not watch_state_path.exists()

    for key in ("originals", "redacted", "encrypted", "reports", "keys", "logs"):
        assert summary["removed_vault_files"][key] == 1
        assert list(vault_paths[key].iterdir()) == []

    assert summary["removed_audit_archive_entries"] == 1
    assert list(audit_archive_root.iterdir()) == []
    assert summary["reset_database_rows"] == {
        "audit_events": 1,
        "scan_events": 1,
        "documents": 1,
        "document_artifacts": 1,
    }

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM document_artifacts").fetchone()[0] == 0



