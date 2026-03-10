"""Configuration loading utilities for PRIVGUARD AI."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SYSTEM_CONFIG_PATH = CONFIG_DIR / "system_config.yaml"
LOCAL_SYSTEM_CONFIG_PATH = BASE_DIR / "instance" / "local_system_config.yaml"
LOCAL_ONLY_CONFIG_KEYS = {
    ("vault", "default_master_key"),
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _strip_local_only_values(config: Dict[str, Any], base: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = deepcopy(config)
    for path in LOCAL_ONLY_CONFIG_KEYS:
        source_cursor: Dict[str, Any] | None = base
        target_cursor: Dict[str, Any] | None = sanitized
        for key in path[:-1]:
            if not isinstance(source_cursor, dict) or not isinstance(target_cursor, dict):
                source_cursor = None
                target_cursor = None
                break
            source_cursor = source_cursor.get(key)
            target_cursor = target_cursor.get(key)
        final_key = path[-1]
        if isinstance(target_cursor, dict):
            if isinstance(source_cursor, dict) and final_key in source_cursor:
                target_cursor[final_key] = source_cursor[final_key]
            else:
                target_cursor.pop(final_key, None)
    return sanitized


@lru_cache(maxsize=1)
def load_detection_config() -> Dict[str, Any]:
    with (CONFIG_DIR / "detection_rules.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def load_risk_policy() -> Dict[str, Any]:
    with (CONFIG_DIR / "risk_policy.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def load_system_config() -> Dict[str, Any]:
    config = _load_yaml(SYSTEM_CONFIG_PATH)

    if LOCAL_SYSTEM_CONFIG_PATH.exists():
        local_config = _load_yaml(LOCAL_SYSTEM_CONFIG_PATH)
        config = _deep_merge(config, local_config)

    return config


def save_system_config(config: Dict[str, Any]) -> None:
    base_config = _load_yaml(SYSTEM_CONFIG_PATH)
    sanitized = _strip_local_only_values(config, base_config)
    SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SYSTEM_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(sanitized, handle, sort_keys=False)
    load_system_config.cache_clear()


def save_local_system_config(config: Dict[str, Any]) -> None:
    LOCAL_SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_SYSTEM_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    load_system_config.cache_clear()
