"""Repeatable demo workflow helpers for PrivGuard AI."""

from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path
from typing import Callable

from config_loader import BASE_DIR, load_system_config
from security.vault import ensure_vault_layout
from storage.db import DB_PATH

SYSTEM_CONFIG = load_system_config()
DEMO_CONFIG = SYSTEM_CONFIG.get("demo", {})
AUDIT_CONFIG = SYSTEM_CONFIG.get("audit", {})
WATCH_CONFIG = SYSTEM_CONFIG.get("watch_folder", {})

DEFAULT_SYNTHETIC_FILE_COUNT = max(1, int(DEMO_CONFIG.get("synthetic_file_count", 500)))


def _resolve_project_path(raw_path: str, fallback: str) -> Path:
    path = Path(str(raw_path or fallback))
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


DEFAULT_DEMO_WATCH_FOLDER = _resolve_project_path(
    str(DEMO_CONFIG.get("watch_folder_dir", "WATCH FOLDER")),
    "WATCH FOLDER",
)
DEFAULT_WATCH_STATE_PATH = _resolve_project_path(
    str(WATCH_CONFIG.get("state_path", "instance/watch_folder_state.json")),
    "instance/watch_folder_state.json",
)
DEFAULT_AUDIT_ARCHIVE_ROOT = _resolve_project_path(
    str(AUDIT_CONFIG.get("archive_root", "audit activity")),
    "audit activity",
)
DEFAULT_DB_PATH = _resolve_project_path(str(DB_PATH), "instance/privguard_audit.db")

PEOPLE = [
    ("Amina Njeri", "0712345678", "amina.njeri@uhuru.co.ke", "23456789", "A123456789B"),
    ("Kevin Mutua", "0723456789", "kevin.mutua@baraka.co.ke", "24567890", "A234567890C"),
    ("Faith Wanjiku", "0734567890", "faith.wanjiku@tumaini.org", "25678901", "A345678901D"),
    ("Brian Otieno", "0745678901", "brian.otieno@harvest.co.ke", "26789012", "A456789012E"),
    ("Mercy Chebet", "0756789012", "mercy.chebet@jambo.co.ke", "27890123", "A567890123F"),
    ("John Mwangi", "0767890123", "john.mwangi@pendo.co.ke", "28901234", "A678901234G"),
    ("Linet Achieng", "0778901234", "linet.achieng@afya.or.ke", "29012345", "A789012345H"),
    ("Peter Kiptoo", "0789012345", "peter.kiptoo@elimu.co.ke", "30123456", "A890123456J"),
    ("Naomi Atieno", "0711122233", "naomi.atieno@county.go.ke", "31234567", "A901234567K"),
    ("David Kiprono", "0722233344", "david.kiprono@safiri.co.ke", "32345678", "B012345678L"),
]


def _person(index: int) -> tuple[str, str, str, str, str]:
    return PEOPLE[(index - 1) % len(PEOPLE)]


def _account_number(index: int) -> str:
    return f"01{index:04d}22334455{(index % 90) + 10:02d}"


def _batch_code(index: int) -> str:
    return f"PG-DEMO-{index:04d}"


def _admission_content(index: int, serial: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"Student Admission Packet {serial}",
            f"Batch: {_batch_code(index)}",
            f"Student Name: {name}",
            f"Guardian Phone: {phone}",
            f"Guardian Email: {email}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Fee Account: {_account_number(index)}",
            f"Medical Login Code: school-{serial}-secure",
            f"Amount Due: KES {125000 + (serial * 250)}",
        ]
    )


def _bank_content(index: int, serial: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            "field,value",
            f"batch,{_batch_code(index)}",
            f"customer,{name}",
            f"national_id,{national_id}",
            f"kra_pin,{kra_pin}",
            f"phone,{phone}",
            f"email,{email}",
            f"account,{_account_number(index)}",
            f"salary,KES {180000 + (serial * 3700)}",
            f"password,bank-{serial}-reset",
        ]
    )


def _contract_content(index: int, serial: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"# Vendor Contract {serial}",
            f"Batch: {_batch_code(index)}",
            f"Vendor Name: {name}",
            f"Contact Phone: {phone}",
            f"Contact Email: {email}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Bank Account: {_account_number(index)}",
            f"Secret Key: contract-{serial}-vault",
            f"Payment Amount: KES {240000 + (serial * 1100)}",
        ]
    )


def _county_content(index: int, serial: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"[2026-03-08] Intake batch {_batch_code(index)} opened",
            f"Client Name: {name}",
            f"Phone: {phone}",
            f"Email: {email}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Payment Account: {_account_number(index)}",
            f"Password: county-{serial}-access",
            f"Balance: KES {87500 + (serial * 640)}",
            f"[2026-03-08] Intake batch {_batch_code(index)} closed",
        ]
    )


def _payroll_content(index: int, serial: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"Payroll Report {serial}",
            f"Batch: {_batch_code(index)}",
            f"Employee Name: {name}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Phone: {phone}",
            f"Email: {email}",
            f"Salary Account: {_account_number(index)}",
            f"Monthly Salary: KES {42000 + (serial * 475)}",
            f"Passcode: PAY-{serial}-SECURE-2026",
        ]
    )


TEMPLATES: list[tuple[str, str, Callable[[int, int], str]]] = [
    ("admissions", "txt", _admission_content),
    ("bank", "txt", _bank_content),
    ("contract", "txt", _contract_content),
    ("county", "txt", _county_content),
    ("payroll", "txt", _payroll_content),
]


def get_demo_watch_folder_path() -> Path:
    return DEFAULT_DEMO_WATCH_FOLDER


def get_demo_target_count() -> int:
    return DEFAULT_SYNTHETIC_FILE_COUNT


def _clear_directory(path: Path) -> int:
    if not path.exists():
        return 0
    removed = 0
    for entry in list(path.iterdir()):
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
        removed += 1
    return removed


def _seed_demo_documents(folder: Path, target_count: int) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    existing = {entry.name for entry in folder.iterdir() if entry.is_file()}
    total_files = len(existing)
    created = 0
    candidate_index = 1
    template_count = len(TEMPLATES)

    while total_files < target_count:
        template_name, suffix, builder = TEMPLATES[(candidate_index - 1) % template_count]
        serial = ((candidate_index - 1) // template_count) + 1
        filename = f"{template_name}_{serial:03d}.{suffix}"
        if filename not in existing:
            (folder / filename).write_text(builder(candidate_index, serial), encoding="utf-8")
            existing.add(filename)
            total_files += 1
            created += 1
        candidate_index += 1

    return created


def ensure_demo_watch_folder(
    *,
    watch_folder: Path | None = None,
    target_count: int | None = None,
) -> dict:
    folder = (watch_folder or get_demo_watch_folder_path()).resolve()
    target = max(1, int(target_count or get_demo_target_count()))
    folder.mkdir(parents=True, exist_ok=True)
    current_files = [entry for entry in folder.iterdir() if entry.is_file()]
    created = 0
    if len(current_files) < target:
        created = _seed_demo_documents(folder, target)
    file_count = len([entry for entry in folder.iterdir() if entry.is_file()])
    return {
        "watch_folder": str(folder),
        "target_count": target,
        "seeded_file_count": file_count,
        "created": created,
    }


def _reset_database_tables(db_path: Path) -> dict[str, int]:
    counts = {
        "audit_events": 0,
        "scan_events": 0,
        "documents": 0,
        "document_artifacts": 0,
    }
    if not db_path.exists():
        return counts

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        for table in counts:
            if table not in tables:
                continue
            counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            conn.execute(f"DELETE FROM {table}")
        if "sqlite_sequence" in tables:
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('audit_events', 'scan_events', 'documents', 'document_artifacts')"
            )
        conn.commit()
    return counts


def rebuild_demo_workspace(
    *,
    watch_folder: Path | None = None,
    target_count: int | None = None,
    vault_paths: dict[str, Path] | None = None,
    db_path: Path | None = None,
    watch_state_path: Path | None = None,
    audit_archive_root: Path | None = None,
) -> dict:
    folder = (watch_folder or get_demo_watch_folder_path()).resolve()
    target = max(1, int(target_count or get_demo_target_count()))
    paths = vault_paths or ensure_vault_layout()
    runtime_db_path = (db_path or DEFAULT_DB_PATH).resolve()
    runtime_watch_state_path = (watch_state_path or DEFAULT_WATCH_STATE_PATH).resolve()
    runtime_audit_archive_root = (audit_archive_root or DEFAULT_AUDIT_ARCHIVE_ROOT).resolve()

    removed_watch_files = _clear_directory(folder)
    folder.mkdir(parents=True, exist_ok=True)

    removed_vault_files: dict[str, int] = {}
    for key, path in paths.items():
        if key == "root":
            continue
        path.mkdir(parents=True, exist_ok=True)
        removed_vault_files[key] = _clear_directory(path)

    removed_archive_entries = _clear_directory(runtime_audit_archive_root)
    reset_tables = _reset_database_tables(runtime_db_path)

    watch_state_reset = False
    if runtime_watch_state_path.exists():
        runtime_watch_state_path.unlink()
        watch_state_reset = True

    created = _seed_demo_documents(folder, target)
    return {
        "watch_folder": str(folder),
        "target_count": target,
        "seeded_file_count": created,
        "removed_watch_files": removed_watch_files,
        "removed_vault_files": removed_vault_files,
        "removed_audit_archive_entries": removed_archive_entries,
        "reset_database_rows": reset_tables,
        "watch_state_reset": watch_state_reset,
    }




