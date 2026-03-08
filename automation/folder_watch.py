"""Background folder watch service for PrivGuard auto-protect."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict

from config_loader import load_system_config

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover - optional dependency fallback
    FileSystemEventHandler = object  # type: ignore[assignment]
    Observer = None

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
_OBSERVER = None
_RUNTIME_MODE = "idle"
_RUNNING_PATH = ""


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
        "current_file": None,
        "current_started_at": None,
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


def _set_runtime_mode(mode: str) -> None:
    global _RUNTIME_MODE
    _RUNTIME_MODE = mode


def _progress_snapshot(state: Dict[str, object]) -> dict:
    folder_text = str(state.get("path") or "").strip()
    if not folder_text:
        return {
            "supported_total": 0,
            "processed_count": 0,
            "pending_count": 0,
            "progress_percent": 0,
            "estimated_completion": "Select a folder to begin monitoring.",
        }

    folder = Path(folder_text)
    if not folder.exists() or not folder.is_dir():
        return {
            "supported_total": 0,
            "processed_count": 0,
            "pending_count": 0,
            "progress_percent": 0,
            "estimated_completion": "Watch folder is unavailable.",
        }

    entries = [entry for entry in folder.iterdir() if _watchable_file(entry)]
    processed = dict(state.get("processed") or {})
    processed_count = 0
    for entry in entries:
        try:
            stats = entry.stat()
        except FileNotFoundError:
            continue
        signature = f"{stats.st_mtime_ns}:{stats.st_size}"
        if processed.get(str(entry.resolve())) == signature:
            processed_count += 1

    supported_total = len(entries)
    pending_count = max(supported_total - processed_count, 0)
    progress_percent = int((processed_count / supported_total) * 100) if supported_total else 0
    if supported_total == 0:
        estimated = "No supported files detected yet."
    elif pending_count == 0:
        estimated = "Scan backlog complete. Monitoring for new files."
    elif pending_count == 1:
        estimated = "1 file remaining in the queue."
    else:
        estimated = f"{pending_count} files remaining in the queue."

    return {
        "supported_total": supported_total,
        "processed_count": processed_count,
        "pending_count": pending_count,
        "progress_percent": progress_percent,
        "estimated_completion": estimated,
    }


def _state_view(state: Dict[str, object]) -> dict:
    public_state = dict(state)
    public_state.pop("processed", None)
    public_state.pop("seen", None)
    public_state.update(_progress_snapshot(state))
    public_state["running"] = bool((_THREAD and _THREAD.is_alive()) or (_OBSERVER is not None))
    public_state["mode"] = _RUNTIME_MODE
    return public_state


def get_watch_folder_state() -> dict:
    with _STATE_LOCK:
        return _state_view(_load_state())


def configure_watch_folder(folder_path: str, actor: str, *, reset_progress: bool = False) -> dict:
    resolved = Path(folder_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError("Watch folder must be an existing directory.")

    with _STATE_LOCK:
        state = _load_state()
        if reset_progress or str(resolved) != str(state.get("path") or ""):
            state["processed"] = {}
            state["seen"] = {}
        state["enabled"] = True
        state["path"] = str(resolved)
        state["configured_by"] = actor
        state["configured_at"] = _utc_now()
        state["last_error"] = None
        state["current_file"] = None
        state["current_started_at"] = None
        _save_state(state)
        return _state_view(state)


def disable_watch_folder(actor: str | None = None) -> dict:
    with _STATE_LOCK:
        state = _load_state()
        state["enabled"] = False
        state["configured_by"] = actor or state.get("configured_by")
        state["last_error"] = None
        state["current_file"] = None
        state["current_started_at"] = None
        _save_state(state)
    stop_watch_folder_runner()
    return get_watch_folder_state()


def stop_watch_folder_runner() -> None:
    global _THREAD, _OBSERVER, _RUNNING_PATH
    _STOP_EVENT.set()
    thread = _THREAD
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=max(POLL_SECONDS, 1.0))
    _THREAD = None
    if _OBSERVER is not None:
        try:
            _OBSERVER.stop()
            _OBSERVER.join(timeout=max(POLL_SECONDS, 1.0))
        except Exception:
            pass
    _OBSERVER = None
    _RUNNING_PATH = ""
    _STOP_EVENT.clear()
    _set_runtime_mode("idle")


def ensure_watch_folder_running(
    processor: Callable[[Path], dict | None],
    *,
    force_restart: bool = False,
) -> dict:
    global _PROCESSOR, _THREAD, _OBSERVER, _RUNNING_PATH
    _PROCESSOR = processor
    state = _load_state()
    if not state.get("enabled"):
        _set_runtime_mode("idle")
        return _state_view(state)

    folder = Path(str(state.get("path") or "")).expanduser()
    resolved_path = str(folder.resolve()) if folder.exists() else str(folder)
    runner_active = _OBSERVER is not None or (_THREAD and _THREAD.is_alive())
    if runner_active and (_RUNNING_PATH != resolved_path or force_restart):
        stop_watch_folder_runner()
        runner_active = False
    if runner_active:
        return _state_view(state)

    if Observer is not None and folder.exists() and folder.is_dir():
        handler = _WatchdogHandler()
        observer = Observer()
        observer.schedule(handler, str(folder), recursive=False)
        observer.daemon = True
        observer.start()
        _OBSERVER = observer
        _RUNNING_PATH = resolved_path
        _set_runtime_mode("event")
        scan_thread = threading.Thread(
            target=_run_scan_pass,
            kwargs={"require_stable_seen": False},
            name="privguard-folder-watch-initial-scan",
            daemon=True,
        )
        scan_thread.start()
        return get_watch_folder_state()

    _STOP_EVENT.clear()
    _THREAD = threading.Thread(target=_run_loop, name="privguard-folder-watch", daemon=True)
    _THREAD.start()
    _RUNNING_PATH = resolved_path
    _set_runtime_mode("poll")
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


def _process_entry(entry: Path, *, require_stable_seen: bool = True) -> bool:
    with _STATE_LOCK:
        state = _load_state()

    if not _watchable_file(entry):
        return False
    try:
        stats = entry.stat()
    except FileNotFoundError:
        return False

    signature = f"{stats.st_mtime_ns}:{stats.st_size}"
    path_key = str(entry.resolve())
    seen = dict(state.get("seen") or {})
    processed = dict(state.get("processed") or {})

    if seen.get(path_key) != signature:
        seen[path_key] = signature
        with _STATE_LOCK:
            state = _load_state()
            state["seen"] = seen
            state["last_scan_at"] = _utc_now()
            _save_state(state)
        if require_stable_seen:
            return False
    if processed.get(path_key) == signature or _PROCESSOR is None:
        return False

    try:
        with _STATE_LOCK:
            state = _load_state()
            state["current_file"] = entry.name
            state["current_started_at"] = _utc_now()
            state["last_error"] = None
            _save_state(state)

        result = _PROCESSOR(entry) or {}
        processed[path_key] = signature
        with _STATE_LOCK:
            state = _load_state()
            state["processed"] = processed
            state["seen"] = seen
            state["last_processed_at"] = _utc_now()
            state["last_scan_at"] = _utc_now()
            state["last_file"] = entry.name
            state["last_document_id"] = result.get("document_id")
            state["last_error"] = None
            state["current_file"] = None
            state["current_started_at"] = None
            _save_state(state)
        return True
    except Exception as exc:
        with _STATE_LOCK:
            state = _load_state()
            state["current_file"] = None
            state["current_started_at"] = None
            _save_state(state)
        _set_last_error(str(exc))
        return False


def _run_scan_pass(require_stable_seen: bool = True) -> bool:
    with _STATE_LOCK:
        state = _load_state()
    if not state.get("enabled"):
        return False

    folder_text = str(state.get("path") or "").strip()
    if not folder_text:
        _set_last_error("Watch folder path is empty.")
        return False

    folder = Path(folder_text)
    if not folder.exists() or not folder.is_dir():
        _set_last_error("Watch folder is unavailable.")
        return False

    changed = False
    for entry in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        changed = _process_entry(entry, require_stable_seen=require_stable_seen) or changed
    with _STATE_LOCK:
        state = _load_state()
        state["last_scan_at"] = _utc_now()
        _save_state(state)
    return changed


def _run_loop() -> None:
    while not _STOP_EVENT.is_set():
        _run_scan_pass()
        time.sleep(POLL_SECONDS)


class _WatchdogHandler(FileSystemEventHandler):  # type: ignore[misc]
    def on_created(self, event):  # pragma: no cover - exercised via runtime only
        if getattr(event, "is_directory", False):
            return
        time.sleep(0.2)
        _process_entry(Path(str(event.src_path)), require_stable_seen=False)

    def on_modified(self, event):  # pragma: no cover - exercised via runtime only
        if getattr(event, "is_directory", False):
            return
        time.sleep(0.2)
        _process_entry(Path(str(event.src_path)), require_stable_seen=False)

