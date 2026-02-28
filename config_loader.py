"""Configuration loading utilities for PRIVGUARD AI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"


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
    with (CONFIG_DIR / "system_config.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
