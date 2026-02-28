"""Signing key management for audit exports."""

from __future__ import annotations

import secrets
from pathlib import Path

from config_loader import load_system_config


SYSTEM_CONFIG = load_system_config()
SIGNING_KEY_PATH = Path(SYSTEM_CONFIG["export"]["signing_key_path"])


def get_or_create_signing_key() -> bytes:
    SIGNING_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SIGNING_KEY_PATH.exists():
        return SIGNING_KEY_PATH.read_bytes()
    key = secrets.token_bytes(32)
    SIGNING_KEY_PATH.write_bytes(key)
    return key
