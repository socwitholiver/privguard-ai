"""Configuration loading utilities for PRIVGUARD AI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
SYSTEM_CONFIG_PATH = CONFIG_DIR / "system_config.yaml"


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
    with SYSTEM_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def save_system_config(config: Dict[str, Any]) -> None:
    SYSTEM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SYSTEM_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    load_system_config.cache_clear()
