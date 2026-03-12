import time
from pathlib import Path

import automation.folder_watch as folder_watch


def test_watch_folder_processes_new_files(tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()

    monkeypatch.setattr(folder_watch, "STATE_PATH", tmp_path / "instance" / "watch_folder_state.json")
    monkeypatch.setattr(folder_watch, "POLL_SECONDS", 0.05)
    folder_watch.stop_watch_folder_runner()

    processed = []

    def processor(path: Path):
        processed.append(path.name)
        return {"document_id": "PG-2026-00001"}

    try:
        state = folder_watch.configure_watch_folder(str(incoming), "tester")
        assert state["enabled"] is True

        folder_watch.ensure_watch_folder_running(processor)
        (incoming / "payroll.txt").write_text("salary data", encoding="utf-8")

        deadline = time.time() + 1.5
        while time.time() < deadline and not processed:
            time.sleep(0.05)

        assert processed == ["payroll.txt"]
        current_state = folder_watch.get_watch_folder_state()
        assert current_state["enabled"] is True
        assert current_state["last_file"] == "payroll.txt"
        assert current_state["last_document_id"] == "PG-2026-00001"
        assert current_state["supported_total"] == 1
        assert current_state["processed_count"] == 1
        assert current_state["pending_count"] == 0
    finally:
        folder_watch.disable_watch_folder("tester")
        folder_watch.stop_watch_folder_runner()


def test_event_mode_initial_scan_runs_in_background(tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    for index in range(5):
        (incoming / f"payroll_{index}.txt").write_text("salary data", encoding="utf-8")

    monkeypatch.setattr(folder_watch, "STATE_PATH", tmp_path / "instance" / "watch_folder_state.json")
    monkeypatch.setattr(folder_watch, "POLL_SECONDS", 0.05)
    folder_watch.stop_watch_folder_runner()

    processed = []

    def processor(path: Path):
        time.sleep(0.05)
        processed.append(path.name)
        return {"document_id": f"PG-2026-{len(processed):05d}"}

    try:
        folder_watch.configure_watch_folder(str(incoming), "tester", reset_progress=True)
        started_at = time.time()
        state = folder_watch.ensure_watch_folder_running(processor, force_restart=True)
        elapsed = time.time() - started_at

        assert state["enabled"] is True
        assert elapsed < 0.2

        deadline = time.time() + 2.0
        while time.time() < deadline and len(processed) < 5:
            time.sleep(0.05)

        assert len(processed) == 5
    finally:
        folder_watch.disable_watch_folder("tester")
        folder_watch.stop_watch_folder_runner()
