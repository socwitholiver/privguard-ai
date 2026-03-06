from pathlib import Path

from storage import profile_repo


def test_profile_repo_creates_default_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_repo, "PROFILES_PATH", tmp_path / "user_profiles.json")

    profile = profile_repo.get_profile("admin")

    assert profile["username"] == "admin"
    assert profile["display_name"] == "admin"
    assert profile["avatar_url"] == ""
    assert profile["theme"] == "dark"
    assert profile_repo.PROFILES_PATH.exists()


def test_profile_repo_updates_display_name_avatar_and_theme(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_repo, "PROFILES_PATH", tmp_path / "user_profiles.json")
    profile_repo.get_profile("operator")

    updated = profile_repo.update_profile(
        "operator",
        display_name="Grace Wanjiku",
        avatar_url="/static/uploads/avatars/grace.png",
        theme="light",
    )

    assert updated["display_name"] == "Grace Wanjiku"
    assert updated["avatar_url"] == "/static/uploads/avatars/grace.png"
    assert updated["theme"] == "light"

    stored = profile_repo.get_profile("operator")
    assert stored == updated
