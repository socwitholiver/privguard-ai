import time

import automation.folder_watch as folder_watch


def test_force_restart_reprocesses_existing_files(tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    target = incoming / "payroll.txt"
    target.write_text("salary data", encoding="utf-8")

    monkeypatch.setattr(folder_watch, "STATE_PATH", tmp_path / "instance" / "watch_folder_state.json")
    folder_watch.stop_watch_folder_runner()

    processed = []

    def processor(path):
        processed.append(path.name)
        return {"document_id": "PG-2026-00077"}

    try:
        folder_watch.configure_watch_folder(str(incoming), "tester", reset_progress=True)
        folder_watch.ensure_watch_folder_running(processor)

        deadline = time.time() + 1.5
        while time.time() < deadline and processed != ["payroll.txt"]:
            time.sleep(0.05)

        assert processed == ["payroll.txt"]

        processed.clear()
        folder_watch.configure_watch_folder(str(incoming), "tester", reset_progress=True)
        folder_watch.ensure_watch_folder_running(processor, force_restart=True)

        deadline = time.time() + 1.5
        while time.time() < deadline and processed != ["payroll.txt"]:
            time.sleep(0.05)

        assert processed == ["payroll.txt"]
    finally:
        folder_watch.disable_watch_folder("tester")
        folder_watch.stop_watch_folder_runner()


def test_force_restart_switches_to_new_folder(tmp_path, monkeypatch):
    first = tmp_path / "incoming-a"
    second = tmp_path / "incoming-b"
    first.mkdir()
    second.mkdir()
    (second / "contract.md").write_text("contract", encoding="utf-8")

    monkeypatch.setattr(folder_watch, "STATE_PATH", tmp_path / "instance" / "watch_folder_state.json")
    folder_watch.stop_watch_folder_runner()

    processed = []

    def processor(path):
        processed.append(path.parent.name + "/" + path.name)
        return {"document_id": "PG-2026-00078"}

    try:
        folder_watch.configure_watch_folder(str(first), "tester")
        folder_watch.ensure_watch_folder_running(processor)

        folder_watch.configure_watch_folder(str(second), "tester", reset_progress=True)
        folder_watch.ensure_watch_folder_running(processor, force_restart=True)

        deadline = time.time() + 1.5
        while time.time() < deadline and "incoming-b/contract.md" not in processed:
            time.sleep(0.05)

        assert processed[-1] == "incoming-b/contract.md"
        state = folder_watch.get_watch_folder_state()
        assert state["path"] == str(second.resolve())
        assert state["last_file"] == "contract.md"
    finally:
        folder_watch.disable_watch_folder("tester")
        folder_watch.stop_watch_folder_runner()
