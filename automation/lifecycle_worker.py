"""Background lifecycle automation for PrivGuard retention actions."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Callable

from config_loader import load_system_config
from storage.document_repo import get_document, list_documents

SYSTEM_CONFIG = load_system_config()
LIFECYCLE_CONFIG = SYSTEM_CONFIG.get("lifecycle", {})
SCAN_SECONDS = int(LIFECYCLE_CONFIG.get("scan_seconds", 60))
AUTO_ARCHIVE_EXPIRED = bool(LIFECYCLE_CONFIG.get("auto_archive_expired", True))
AUTO_DELETE_ARCHIVED = bool(LIFECYCLE_CONFIG.get("auto_delete_archived", False))

_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()
_RUNTIME = {"last_run_at": None, "running": False, "actions": 0}


def lifecycle_state() -> dict:
    return dict(_RUNTIME)


def stop_lifecycle_runner() -> None:
    global _THREAD
    _STOP_EVENT.set()
    if _THREAD and _THREAD.is_alive() and _THREAD is not threading.current_thread():
        _THREAD.join(timeout=max(SCAN_SECONDS, 1))
    _THREAD = None
    _RUNTIME["running"] = False
    _STOP_EVENT.clear()


def ensure_lifecycle_runner(archive_cb: Callable[[str], None], delete_cb: Callable[[str], None]) -> dict:
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return lifecycle_state()
    _STOP_EVENT.clear()
    _THREAD = threading.Thread(
        target=_run_loop,
        args=(archive_cb, delete_cb),
        name="privguard-lifecycle-runner",
        daemon=True,
    )
    _THREAD.start()
    _RUNTIME["running"] = True
    return lifecycle_state()


def _run_loop(archive_cb: Callable[[str], None], delete_cb: Callable[[str], None]) -> None:
    while not _STOP_EVENT.is_set():
        actions = 0
        for document in list_documents(limit=500):
            current = get_document(document["document_id"])
            if not current:
                continue
            lifecycle_status = str(current.get("lifecycle_status") or "active").lower()
            deleted = bool(current.get("deleted_at"))
            archived = bool(current.get("archived_at"))
            if deleted:
                continue
            retention_until = str(current.get("retention_until") or "").strip()
            if not retention_until:
                continue
            try:
                due = datetime.fromisoformat(retention_until.replace("Z", "+00:00"))
            except ValueError:
                continue
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if due > now:
                continue
            expiry_action = str(current.get("expiry_action") or "review")
            if AUTO_ARCHIVE_EXPIRED and not archived and expiry_action in {"archive", "archive_or_delete"}:
                archive_cb(current["document_id"])
                actions += 1
                continue
            if AUTO_DELETE_ARCHIVED and archived and expiry_action == "archive_or_delete":
                delete_cb(current["document_id"])
                actions += 1
        _RUNTIME["last_run_at"] = datetime.now(timezone.utc).isoformat()
        _RUNTIME["actions"] = actions
        _RUNTIME["running"] = True
        time.sleep(SCAN_SECONDS)
