"""Background folder watch service for PrivGuard auto-protect."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict

from config_loader import load_system_config


SYSTEM_CONFIG = load_system_config()
WATCH_CONFIG = SYSTEM_CONFIG.get("watch_folder", {})
STATE_PATH = Path(WATCH_CONFIG.get("state_path", "instance/watch_folder_state.json"))
POLL_SECONDS = float(WATCH_CONFIG.get("poll_seconds", 3))
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".webp",
}
IGNORED_PREFIXES = ("~$", ".")
IGNORED_SUFFIXES = (".tmp", ".part")

_STATE_LOCK = threading.Lock()
_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()
_PROCESSOR: Callable[[Path], dict | None] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> Dict[str, object]:
    return {
        "enabled": False,
        "path": "",
        "configured_by": None,
        "configured_at": None,
        "last_scan_at": None,
        "last_processed_at": None,
        "last_file": None,
        "last_document_id": None,
        "last_error": None,
        "processed": {},
        "seen": {},
    }


def _load_state() -> Dict[str, object]:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
    state = _default_state()
    state.update(data)
    return state


def _save_state(state: Dict[str, object]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _state_view(state: Dict[str, object]) -> dict:
    public_state = dict(state)
    public_state.pop("processed", None)
    public_state.pop("seen", None)
    public_state["running"] = bool(_THREAD and _THREAD.is_alive())
    return public_state


def get_watch_folder_state() -> dict:
    with _STATE_LOCK:
        return _state_view(_load_state())


def configure_watch_folder(folder_path: str, actor: str) -> dict:
    resolved = Path(folder_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError("Watch folder must be an existing directory.")

    with _STATE_LOCK:
        state = _load_state()
        if str(resolved) != str(state.get("path") or ""):
            state["processed"] = {}
            state["seen"] = {}
        state["enabled"] = True
        state["path"] = str(resolved)
        state["configured_by"] = actor
        state["configured_at"] = _utc_now()
        state["last_error"] = None
        _save_state(state)
        return _state_view(state)


def disable_watch_folder(actor: str | None = None) -> dict:
    with _STATE_LOCK:
        state = _load_state()
        state["enabled"] = False
        state["configured_by"] = actor or state.get("configured_by")
        state["last_error"] = None
        _save_state(state)
    stop_watch_folder_runner()
    return get_watch_folder_state()


def stop_watch_folder_runner() -> None:
    global _THREAD
    _STOP_EVENT.set()
    thread = _THREAD
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=max(POLL_SECONDS, 1.0))
    _THREAD = None
    _STOP_EVENT.clear()


def ensure_watch_folder_running(processor: Callable[[Path], dict | None]) -> dict:
    global _PROCESSOR, _THREAD
    _PROCESSOR = processor
    state = _load_state()
    if not state.get("enabled"):
        return _state_view(state)
    if _THREAD and _THREAD.is_alive():
        return _state_view(state)

    _STOP_EVENT.clear()
    _THREAD = threading.Thread(target=_run_loop, name="privguard-folder-watch", daemon=True)
    _THREAD.start()
    return get_watch_folder_state()


def _watchable_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    name = path.name
    if suffix not in SUPPORTED_EXTENSIONS:
        return False
    if any(name.startswith(prefix) for prefix in IGNORED_PREFIXES):
        return False
    if any(name.endswith(suffix_name) for suffix_name in IGNORED_SUFFIXES):
        return False
    return path.is_file()


def _set_last_error(message: str) -> None:
    with _STATE_LOCK:
        state = _load_state()
        state["last_error"] = message
        state["last_scan_at"] = _utc_now()
        _save_state(state)


def _run_loop() -> None:
    while not _STOP_EVENT.is_set():
        state_changed = False
        with _STATE_LOCK:
            state = _load_state()

        if not state.get("enabled"):
            time.sleep(POLL_SECONDS)
            continue

        folder_text = str(state.get("path") or "").strip()
        if not folder_text:
            _set_last_error("Watch folder path is empty.")
            time.sleep(POLL_SECONDS)
            continue

        folder = Path(folder_text)
        if not folder.exists() or not folder.is_dir():
            _set_last_error("Watch folder is unavailable.")
            time.sleep(POLL_SECONDS)
            continue

        seen = dict(state.get("seen") or {})
        processed = dict(state.get("processed") or {})

        for entry in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if not _watchable_file(entry):
                continue

            try:
                stats = entry.stat()
            except FileNotFoundError:
                continue

            signature = f"{stats.st_mtime_ns}:{stats.st_size}"
            path_key = str(entry.resolve())

            if seen.get(path_key) != signature:
                seen[path_key] = signature
                state_changed = True
                continue
            if processed.get(path_key) == signature:
                continue
            if _PROCESSOR is None:
                continue

            try:
                result = _PROCESSOR(entry) or {}
                processed[path_key] = signature
                state["last_processed_at"] = _utc_now()
                state["last_file"] = entry.name
                state["last_document_id"] = result.get("document_id")
                state["last_error"] = None
                state_changed = True
            except Exception as exc:
                state["last_error"] = str(exc)
                state_changed = True

        state["seen"] = seen
        state["processed"] = processed
        state["last_scan_at"] = _utc_now()

        if state_changed:
            with _STATE_LOCK:
                _save_state(state)
        elif not STATE_PATH.exists():
            with _STATE_LOCK:
                _save_state(state)

        time.sleep(POLL_SECONDS)
