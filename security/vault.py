"""Master-password protected vault helpers for PRIVGUARD AI."""

from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from werkzeug.security import check_password_hash, generate_password_hash

from config_loader import load_system_config


SYSTEM_CONFIG = load_system_config()
VAULT_CONFIG = SYSTEM_CONFIG.get("vault", {})
VAULT_ROOT = Path(VAULT_CONFIG.get("root_dir", "vault"))
VAULT_STATE_PATH = Path(VAULT_CONFIG.get("state_path", "instance/vault_state.json"))
VAULT_DIR_NAMES = {
    "originals": VAULT_CONFIG.get("directories", {}).get("originals", "Originals"),
    "redacted": VAULT_CONFIG.get("directories", {}).get("redacted", "Redacted"),
    "encrypted": VAULT_CONFIG.get("directories", {}).get("encrypted", "Encrypted"),
    "reports": VAULT_CONFIG.get("directories", {}).get("reports", "Reports"),
    "keys": VAULT_CONFIG.get("directories", {}).get("keys", "Keys"),
    "logs": VAULT_CONFIG.get("directories", {}).get("logs", "Logs"),
}

_RUNTIME: Dict[str, object] = {
    "master_key": None,
    "unlocked": False,
    "unlocked_by": None,
    "unlocked_at": None,
}
DEFAULT_MASTER_KEY_PLACEHOLDER = "SET_IN_INSTANCE_LOCAL_CONFIG"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_default_master_key() -> str:
    value = str(load_system_config().get("vault", {}).get("default_master_key", "")).strip()
    if not value or value == DEFAULT_MASTER_KEY_PLACEHOLDER:
        raise ValueError("System master PIN is not configured. Set it in instance/local_system_config.yaml.")
    return value


def get_vault_paths() -> Dict[str, Path]:
    paths = {name: VAULT_ROOT / folder_name for name, folder_name in VAULT_DIR_NAMES.items()}
    paths["root"] = VAULT_ROOT
    return paths


def ensure_vault_layout() -> Dict[str, Path]:
    paths = get_vault_paths()
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    VAULT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return paths


def _load_state() -> dict:
    if not VAULT_STATE_PATH.exists():
        return {}
    try:
        return json.loads(VAULT_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(payload: dict) -> None:
    VAULT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    VAULT_STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _derive_master_key(password: str, salt_b64: str) -> bytes:
    salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def vault_is_configured() -> bool:
    state = _load_state()
    return bool(state.get("password_hash") and state.get("salt"))


def vault_uses_system_master_key() -> bool:
    state = _load_state()
    return bool(state.get("password_hash") and state.get("salt") and state.get("key_mode") == "system")


def vault_is_unlocked() -> bool:
    return bool(_RUNTIME.get("unlocked") and _RUNTIME.get("master_key"))


def unlock_vault(master_password: str, username: str | None = None, *, key_mode: str = "user") -> dict:
    if not master_password:
        raise ValueError("Master password is required.")

    ensure_vault_layout()
    state = _load_state()
    created = False

    if not state:
        salt_b64 = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode("utf-8")
        state = {
            "version": 1,
            "created_at": _utc_now(),
            "password_hash": generate_password_hash(master_password),
            "salt": salt_b64,
            "key_mode": key_mode,
        }
        _save_state(state)
        created = True
    elif not check_password_hash(state.get("password_hash", ""), master_password):
        raise ValueError("Invalid master password.")

    master_key = _derive_master_key(master_password, state["salt"])
    _RUNTIME["master_key"] = master_key
    _RUNTIME["unlocked"] = True
    _RUNTIME["unlocked_by"] = username or "local-user"
    _RUNTIME["unlocked_at"] = _utc_now()
    return {
        "created": created,
        "configured": True,
        "unlocked": True,
        "unlocked_by": _RUNTIME["unlocked_by"],
        "unlocked_at": _RUNTIME["unlocked_at"],
        "key_mode": state.get("key_mode", key_mode),
        "paths": {name: str(path) for name, path in get_vault_paths().items()},
    }


def change_master_password(current_password: str, new_password: str) -> dict:
    if not new_password:
        raise ValueError("A new master password is required.")
    ensure_vault_layout()
    state = _load_state()
    if not state:
        raise ValueError("Vault is not configured.")
    if not check_password_hash(state.get("password_hash", ""), current_password):
        raise ValueError("Current master password is invalid.")

    old_master_key = _derive_master_key(current_password, state["salt"])
    key_dir = get_vault_paths()["keys"]
    decrypted_keys: dict[Path, bytes] = {}
    for key_path in key_dir.glob("*.key.json"):
        payload = json.loads(key_path.read_text(encoding="utf-8"))
        token = str(payload.get("encrypted_key", ""))
        if not token:
            continue
        decrypted_keys[key_path] = Fernet(old_master_key).decrypt(token.encode("utf-8"))

    salt_b64 = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode("utf-8")
    new_master_key = _derive_master_key(new_password, salt_b64)
    for key_path, plain_key in decrypted_keys.items():
        payload = json.loads(key_path.read_text(encoding="utf-8"))
        payload["encrypted_key"] = Fernet(new_master_key).encrypt(plain_key).decode("utf-8")
        key_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    key_mode = state.get("key_mode", "user")
    state["password_hash"] = generate_password_hash(new_password)
    state["salt"] = salt_b64
    state["key_mode"] = key_mode
    _save_state(state)

    _RUNTIME["master_key"] = new_master_key
    _RUNTIME["unlocked"] = True
    _RUNTIME["unlocked_at"] = _utc_now()
    return vault_status()


def lock_vault() -> None:
    _RUNTIME["master_key"] = None
    _RUNTIME["unlocked"] = False
    _RUNTIME["unlocked_by"] = None
    _RUNTIME["unlocked_at"] = None


def require_master_key() -> bytes:
    master_key = _RUNTIME.get("master_key")
    if not master_key:
        raise ValueError("Vault is locked.")
    return master_key  # type: ignore[return-value]


def wrap_document_key(document_id: str, document_key: bytes) -> Path:
    paths = ensure_vault_layout()
    master_key = require_master_key()
    token = Fernet(master_key).encrypt(document_key).decode("utf-8")
    payload = {
        "document_id": document_id,
        "created_at": _utc_now(),
        "algorithm": "Fernet",
        "encrypted_key": token,
    }
    key_path = paths["keys"] / f"{document_id}.key.json"
    key_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return key_path


def unwrap_document_key(document_id: str) -> bytes:
    key_path = get_vault_paths()["keys"] / f"{document_id}.key.json"
    if not key_path.exists():
        raise FileNotFoundError(f"No key entry found for {document_id}.")
    payload = json.loads(key_path.read_text(encoding="utf-8"))
    master_key = require_master_key()
    token = str(payload.get("encrypted_key", ""))
    if not token:
        raise ValueError(f"Key entry for {document_id} is invalid.")
    return Fernet(master_key).decrypt(token.encode("utf-8"))


def vault_status() -> dict:
    paths = ensure_vault_layout()
    state = _load_state()
    file_counts = {}
    for name, path in paths.items():
        if name == "root":
            continue
        file_counts[name] = len([entry for entry in path.iterdir() if entry.is_file()])
    return {
        "configured": vault_is_configured(),
        "unlocked": vault_is_unlocked(),
        "unlocked_by": _RUNTIME.get("unlocked_by"),
        "unlocked_at": _RUNTIME.get("unlocked_at"),
        "created_at": state.get("created_at"),
        "key_mode": state.get("key_mode", "user"),
        "paths": {name: str(path) for name, path in paths.items()},
        "file_counts": file_counts,
    }

