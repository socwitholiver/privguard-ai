"""Retention and lifecycle policy helpers for PrivGuard vault records."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from config_loader import load_system_config
from security.vault import ensure_vault_layout



def _lifecycle_config() -> dict:
    return load_system_config().get("lifecycle", {})


def _expiring_soon_days() -> int:
    return int(_lifecycle_config().get("expiring_soon_days", 10))


def _default_retention() -> dict:
    config = _lifecycle_config().get("retention_defaults", {})
    return {
        "High": int(config.get("high", 90)),
        "Medium": int(config.get("medium", 180)),
        "Low": int(config.get("low", 365)),
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | None, fallback: datetime | None = None) -> datetime:
    if not value:
        return fallback or _utc_now()
    normalized = str(value)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _keyword_policy(filename: str) -> dict:
    name = filename.lower()
    if any(token in name for token in ("payroll", "salary", "hr", "payslip")):
        return {
            "owner": "HR",
            "department": "Human Resources",
            "retention_days": 90,
            "expiry_action": "archive_or_delete",
            "policy_name": "Payroll retention policy",
        }
    if any(token in name for token in ("admission", "student", "enrol", "enroll", "school")):
        return {
            "owner": "Admissions",
            "department": "Student Records",
            "retention_days": 365,
            "expiry_action": "archive",
            "policy_name": "Admissions retention policy",
        }
    if any(token in name for token in ("contract", "agreement", "legal", "tender")):
        return {
            "owner": "Legal",
            "department": "Legal Affairs",
            "retention_days": 365,
            "expiry_action": "manual_review",
            "policy_name": "Contract review policy",
        }
    return {}


def build_lifecycle_policy(filename: str, risk: Dict[str, Any], created_at: str | None = None) -> dict:
    created_dt = _parse_timestamp(created_at)
    risk_level = str(risk.get("level", "Low"))
    policy = _keyword_policy(filename)
    retention_days = int(policy.get("retention_days", _default_retention().get(risk_level, 180)))
    expiry_action = str(
        policy.get(
            "expiry_action",
            "archive_or_delete" if risk_level == "High" else "archive" if risk_level == "Medium" else "review",
        )
    )
    owner = str(policy.get("owner", "Records" if risk_level == "High" else "Operations"))
    department = str(policy.get("department", "Protected Records" if risk_level == "High" else "Operations"))
    retention_until = created_dt + timedelta(days=retention_days)
    return {
        "owner": owner,
        "department": department,
        "retention_days": retention_days,
        "retention_until": retention_until.isoformat(),
        "expiry_action": expiry_action,
        "policy_name": str(policy.get("policy_name", f"{risk_level} risk retention policy")),
        "lifecycle_status": "active",
        "next_action": _next_action(expiry_action, days_remaining=retention_days),
    }


def _next_action(expiry_action: str, *, days_remaining: int | None = None, archived: bool = False, deleted: bool = False) -> str:
    if deleted:
        return "Deleted from vault"
    if archived:
        return "Stored in archive"
    if days_remaining is not None and days_remaining <= 0:
        if expiry_action == "manual_review":
            return "Review for archive decision"
        if expiry_action == "archive":
            return "Archive now"
        if expiry_action == "archive_or_delete":
            return "Archive or secure delete"
        return "Review retention"
    if expiry_action == "manual_review":
        return "Manual review before expiry"
    if days_remaining is not None and days_remaining <= _expiring_soon_days():
        return f"{days_remaining} days until expiry"
    if expiry_action == "archive_or_delete":
        return "Monitor until archive window"
    if expiry_action == "archive":
        return "Monitor until archive"
    return "Monitor lifecycle"


def evaluate_lifecycle(document: Dict[str, Any], now: datetime | None = None) -> dict:
    current_time = now or _utc_now()
    archived = bool(document.get("archived_at"))
    deleted = bool(document.get("deleted_at"))
    retention_until = _parse_timestamp(document.get("retention_until"), current_time)
    days_remaining = math.ceil((retention_until - current_time).total_seconds() / 86400)
    expiry_action = str(document.get("expiry_action") or "review")

    if deleted:
        lifecycle_state = "Deleted"
        retention_label = "Deleted"
    elif archived:
        lifecycle_state = "Archived"
        retention_label = "Archived"
    elif days_remaining <= 0:
        lifecycle_state = "Expired"
        retention_label = "Expired"
    elif days_remaining <= _expiring_soon_days():
        lifecycle_state = "Expiring Soon"
        retention_label = f"{days_remaining} days left"
    else:
        lifecycle_state = "Active"
        retention_label = f"{days_remaining} days left"

    return {
        "owner": document.get("owner") or "Operations",
        "department": document.get("department") or "Operations",
        "retention_days": int(document.get("retention_days") or _default_retention().get(str(document.get("risk_level") or "Low"), 180)),
        "retention_until": retention_until.isoformat(),
        "days_remaining": max(days_remaining, 0),
        "retention_label": retention_label,
        "lifecycle_status": lifecycle_state,
        "expiry_action": expiry_action,
        "policy_name": document.get("policy_name") or f"{document.get('risk_level', 'Low')} risk retention policy",
        "next_action": _next_action(expiry_action, days_remaining=days_remaining, archived=archived, deleted=deleted),
        "archive_path": document.get("archive_path") or "",
        "archived_at": document.get("archived_at"),
        "deleted_at": document.get("deleted_at"),
    }


def archive_root() -> Path:
    return ensure_vault_layout()["root"] / str(_lifecycle_config().get("archive_dir", "Archive"))
