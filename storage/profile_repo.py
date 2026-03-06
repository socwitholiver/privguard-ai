"""Local profile preferences for PrivGuard users."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


PROFILES_PATH = Path("instance/user_profiles.json")
_ALLOWED_THEMES = {"dark", "light"}


def _load_profiles() -> Dict[str, dict]:
    if not PROFILES_PATH.exists():
        return {}
    try:
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_profiles(profiles: Dict[str, dict]) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


def _default_profile(username: str) -> dict:
    return {
        "username": username,
        "display_name": username,
        "avatar_url": "",
        "theme": "dark",
    }


def get_profile(username: str) -> dict:
    profiles = _load_profiles()
    profile = profiles.get(username)
    if profile:
        merged = _default_profile(username)
        merged.update(profile)
        return merged
    profile = _default_profile(username)
    profiles[username] = profile
    _save_profiles(profiles)
    return profile


def update_profile(username: str, **updates) -> dict:
    profiles = _load_profiles()
    profile = _default_profile(username)
    profile.update(profiles.get(username, {}))

    display_name = str(updates.get("display_name", profile["display_name"]) or "").strip()
    if display_name:
        profile["display_name"] = display_name[:80]

    avatar_url = updates.get("avatar_url")
    if avatar_url is not None:
        profile["avatar_url"] = str(avatar_url)

    theme = str(updates.get("theme", profile["theme"]) or profile["theme"]).strip().lower()
    if theme in _ALLOWED_THEMES:
        profile["theme"] = theme

    profiles[username] = profile
    _save_profiles(profiles)
    return profile
