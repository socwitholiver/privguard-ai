import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tkinter import Tk, filedialog

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from automation.demo_workflow import (
    ensure_demo_watch_folder,
    get_demo_target_count,
    get_demo_watch_folder_path,
    rebuild_demo_workspace,
    clear_demo_workspace,
)
from automation.folder_watch import (
    configure_watch_folder,
    disable_watch_folder,
    ensure_watch_folder_running,
    get_watch_folder_state,
    stop_watch_folder_runner,
)
from automation.lifecycle_worker import ensure_lifecycle_runner, lifecycle_state, stop_lifecycle_runner
from config_loader import load_system_config, save_local_system_config, save_system_config
from lifecycle_manager import archive_root, build_lifecycle_policy, evaluate_lifecycle
from security.auth import authenticate_user, current_user, require_login, require_vault_unlock
from security.vault import (
    change_master_password,
    ensure_vault_layout,
    get_default_master_key,
    lock_vault,
    unlock_vault,
    unwrap_document_key,
    vault_is_configured,
    vault_is_unlocked,
    vault_uses_system_master_key,
    wrap_document_key,
)
from storage.audit_repo import (
    list_recent_audit_events,
    log_audit_event,
    log_scan_event,
    summarize_scan_events,
)
from storage.db import init_db
from storage.profile_repo import get_profile, update_profile
from storage.document_repo import (
    create_document_record,
    delete_artifacts_for_document,
    generate_document_id,
    get_document,
    get_latest_artifact,
    list_documents,
    record_artifact,
    update_artifact_location,
    update_document_fields,
    update_document_status,
    vault_summary,
)

app = Flask(__name__)
app.secret_key = os.environ.get("PRIVGUARD_SECRET_KEY", "privguard-dev-secret-change-me")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
ensure_vault_layout()
init_db()

ENTITY_TOTAL_KEYS = (
    "national_ids",
    "phone_numbers",
    "emails",
    "kra_pins",
    "passwords",
    "financial_info",
    "personal_names",
)
AVATAR_DIR = Path("static/uploads/avatars")
ALLOWED_AVATAR_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def _dashboard_asset_version() -> int:
    asset_paths = (
        Path("static/css/privguard-cyber-ui.css"),
        Path("static/js/privguard-workspace.js"),
    )
    existing = [int(path.stat().st_mtime) for path in asset_paths if path.exists()]
    return max(existing) if existing else 0


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".webp",
}


def _read_document_text(path: Path) -> str:
    from extraction import read_document_text

    return read_document_text(path)


def _detect_sensitive_data(text: str) -> dict:
    from detection import detect_sensitive_data

    return detect_sensitive_data(text)


def _count_sensitive_items(findings: dict) -> int:
    from detection import count_sensitive_items

    return count_sensitive_items(findings)


def _build_risk_summary(findings: dict) -> dict:
    from classification import build_risk_summary

    return build_risk_summary(findings)


def _decrypt_text(token: str, key: bytes) -> str:
    from protection import decrypt_text

    return decrypt_text(token, key)


def _encrypt_text(text: str, key: bytes) -> str:
    from protection import encrypt_text

    return encrypt_text(text, key)


def _generate_encryption_key() -> bytes:
    from protection import generate_encryption_key

    return generate_encryption_key()


def _redact_text(text: str, findings: dict) -> str:
    from protection import redact_text

    return redact_text(text, findings)


def _verify_redaction_quality(findings: dict, protected_text: str) -> dict:
    from protection import verify_redaction_quality

    return verify_redaction_quality(findings, protected_text)


def _profile_payload(username: str) -> dict:
    profile = get_profile(username)
    return {
        "username": username,
        "display_name": str(profile.get("display_name") or username),
        "avatar_url": str(profile.get("avatar_url") or ""),
        "theme": "light" if str(profile.get("theme") or "dark").lower() == "light" else "dark",
    }


def _apply_profile_session(username: str, *, role: str | None = None) -> dict:
    profile = _profile_payload(username)
    session["username"] = username
    if role is not None:
        session["role"] = role
    session["display_name"] = profile["display_name"]
    session["avatar_url"] = profile["avatar_url"]
    session["theme"] = profile["theme"]
    return profile


def _remove_prior_avatar(avatar_url: str) -> None:
    prefix = "/static/uploads/avatars/"
    if not avatar_url or not str(avatar_url).startswith(prefix):
        return
    avatar_name = str(avatar_url).replace(prefix, "", 1)
    avatar_path = AVATAR_DIR / avatar_name
    if avatar_path.exists() and avatar_path.is_file():
        avatar_path.unlink()


def _save_avatar(file_obj, username: str, existing_avatar_url: str = "") -> str:
    if not file_obj or not file_obj.filename:
        raise ValueError("An avatar file is required.")

    suffix = Path(file_obj.filename).suffix.lower()
    if suffix not in ALLOWED_AVATAR_SUFFIXES:
        raise ValueError("Avatar must be a PNG, JPG, JPEG, WEBP, or GIF image.")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    safe_user = secure_filename(username) or "user"
    avatar_name = f"{safe_user}__avatar__{_timestamp_suffix()}{suffix}"
    avatar_path = AVATAR_DIR / avatar_name
    file_obj.save(str(avatar_path))
    _remove_prior_avatar(existing_avatar_url)
    return url_for("static", filename=f"uploads/avatars/{avatar_name}")

def _actor_name(default: str = "web-user") -> str:
    user = current_user() or {}
    return str(user.get("username") or default)


def _timestamp_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _artifact_filename(document: dict, suffix: str, extension: str) -> str:
    original_stem = Path(str(document.get("original_filename", "document"))).stem
    safe_stem = secure_filename(original_stem) or "document"
    return f"{document['document_id']}__{safe_stem}.{_timestamp_suffix()}.{suffix}.{extension}"


def _system_settings_payload() -> dict:
    config = load_system_config()
    lifecycle = config.get("lifecycle", {})
    return {
        "retention_defaults": {
            "high": int(lifecycle.get("retention_defaults", {}).get("high", 90)),
            "medium": int(lifecycle.get("retention_defaults", {}).get("medium", 180)),
            "low": int(lifecycle.get("retention_defaults", {}).get("low", 365)),
        },
        "expiring_soon_days": int(lifecycle.get("expiring_soon_days", 10)),
        "auto_archive_expired": bool(lifecycle.get("auto_archive_expired", True)),
        "auto_delete_archived": bool(lifecycle.get("auto_delete_archived", False)),
        "scan_seconds": int(lifecycle.get("scan_seconds", 60)),
        "vault_mode": "system" if vault_uses_system_master_key() else "user",
    }


def _save_lifecycle_settings(payload: dict) -> dict:
    config = load_system_config()
    lifecycle = config.setdefault("lifecycle", {})
    lifecycle["retention_defaults"] = {
        "high": max(1, int(payload.get("high_retention_days", payload.get("high", 90)))),
        "medium": max(1, int(payload.get("medium_retention_days", payload.get("medium", 180)))),
        "low": max(1, int(payload.get("low_retention_days", payload.get("low", 365)))),
    }
    lifecycle["expiring_soon_days"] = max(1, int(payload.get("expiring_soon_days", lifecycle.get("expiring_soon_days", 10))))
    lifecycle["auto_archive_expired"] = bool(payload.get("auto_archive_expired", lifecycle.get("auto_archive_expired", True)))
    lifecycle["auto_delete_archived"] = bool(payload.get("auto_delete_archived", lifecycle.get("auto_delete_archived", False)))
    lifecycle["scan_seconds"] = max(10, int(payload.get("scan_seconds", lifecycle.get("scan_seconds", 60))))
    save_system_config(config)
    return _system_settings_payload()


def _archive_document_by_id(document_id: str, *, actor: str, source: str) -> dict:
    document = get_document(document_id)
    if not document:
        raise FileNotFoundError(f"Document {document_id} not found")
    updated = _archive_document_bundle(document)
    log_audit_event(
        event_type="lifecycle_archive",
        actor=actor,
        source=source,
        details={
            "document_id": document_id,
            "filename": updated.get("original_filename"),
            "archive_path": updated.get("archive_path"),
        },
    )
    return updated


def _secure_delete_document_by_id(document_id: str, *, actor: str, source: str) -> dict:
    document = get_document(document_id)
    if not document:
        raise FileNotFoundError(f"Document {document_id} not found")
    updated = _secure_delete_document_bundle(document)
    log_audit_event(
        event_type="lifecycle_secure_delete",
        actor=actor,
        source=source,
        details={
            "document_id": document_id,
            "filename": updated.get("original_filename"),
        },
    )
    return updated


def _ensure_lifecycle_service() -> None:
    ensure_lifecycle_runner(
        lambda document_id: _archive_document_by_id(document_id, actor="lifecycle-engine", source="scheduler"),
        lambda document_id: _secure_delete_document_by_id(document_id, actor="lifecycle-engine", source="scheduler"),
    )


def _ensure_document_lifecycle(document: dict) -> dict:
    if document.get("retention_until") and document.get("owner") and document.get("department"):
        return document
    lifecycle = build_lifecycle_policy(
        str(document.get("original_filename") or "document"),
        {"level": document.get("risk_level", "Low")},
        created_at=document.get("created_at"),
    )
    update_document_fields(
        document["document_id"],
        owner=lifecycle["owner"],
        department=lifecycle["department"],
        retention_days=lifecycle["retention_days"],
        retention_until=lifecycle["retention_until"],
        expiry_action=lifecycle["expiry_action"],
        policy_name=lifecycle["policy_name"],
        lifecycle_status=lifecycle["lifecycle_status"],
        lifecycle_next_action=lifecycle["next_action"],
    )
    document.update(lifecycle)
    return document


def _archive_document_bundle(document: dict) -> dict:
    document = _ensure_document_lifecycle(document)
    archive_dir = archive_root() / datetime.now(timezone.utc).strftime("%Y") / document["document_id"]
    archive_dir.mkdir(parents=True, exist_ok=True)

    original_path_value = str(document.get("original_path") or "").strip()
    if original_path_value:
        original_path = Path(original_path_value)
        if original_path.exists() and original_path.is_file():
            archived_original = archive_dir / original_path.name
            if original_path.resolve() != archived_original.resolve():
                archived_original.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(original_path), archived_original)
                update_document_fields(document["document_id"], original_path=str(archived_original))

    for artifact in document.get("artifact_history", []):
        artifact_path = Path(str(artifact.get("file_path") or ""))
        if artifact_path.exists() and artifact_path.is_file():
            archived_path = archive_dir / artifact_path.name
            if artifact_path.resolve() != archived_path.resolve():
                archived_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(artifact_path), archived_path)
            metadata = dict(artifact.get("metadata") or {})
            metadata["archived"] = True
            metadata["archive_path"] = str(archived_path)
            update_artifact_location(artifact["id"], str(archived_path), archived_path.name, metadata)

    archived_at = datetime.now(timezone.utc).isoformat()
    update_document_fields(
        document["document_id"],
        lifecycle_status="archived",
        lifecycle_next_action="Stored in archive",
        archive_path=str(archive_dir),
        archived_at=archived_at,
    )
    refreshed = get_document(document["document_id"]) or document
    refreshed = _ensure_document_lifecycle(refreshed)
    return refreshed


def _secure_delete_document_bundle(document: dict) -> dict:
    document = _ensure_document_lifecycle(document)
    original_path_value = str(document.get("original_path") or "").strip()
    if original_path_value:
        original_path = Path(original_path_value)
        if original_path.exists() and original_path.is_file():
            original_path.unlink()

    for artifact in document.get("artifact_history", []):
        artifact_path = Path(str(artifact.get("file_path") or ""))
        if artifact_path.exists() and artifact_path.is_file():
            artifact_path.unlink()

    delete_artifacts_for_document(document["document_id"])
    deleted_at = datetime.now(timezone.utc).isoformat()
    update_document_fields(
        document["document_id"],
        original_path="",
        lifecycle_status="deleted",
        lifecycle_next_action="Deleted from vault",
        archive_path="",
        deleted_at=deleted_at,
    )
    refreshed = get_document(document["document_id"]) or document
    refreshed = _ensure_document_lifecycle(refreshed)
    return refreshed


def _protected_placeholder_summary() -> dict:
    return {
        "score": 0,
        "level": "Protected",
        "counts": {key: 0 for key in ENTITY_TOTAL_KEYS},
        "insights": [
            "Protected output is encrypted; use the policy outcome recorded at scan time for the original exposure.",
        ],
        "recommendations": [
            "Keep encrypted artifacts and the local vault available only to authorized users.",
        ],
        "primary_action": "allow",
        "policy": {
            "mode": "allow",
            "label": "Protected",
            "redact": False,
            "encrypt": False,
            "reason": "Protected artifact placeholder.",
        },
    }


def _copy_original_to_vault(source_path: Path, document_id: str) -> tuple[str, Path]:
    filename = secure_filename(source_path.name)
    if not filename:
        raise ValueError("Empty filename")
    original_path = ensure_vault_layout()["originals"] / f"{document_id}__{filename}"
    shutil.copy2(source_path, original_path)
    return filename, original_path



def _register_document_record(
    *,
    document_id: str,
    original_filename: str,
    original_path: Path,
    actor: str,
    source: str,
) -> tuple[dict, Path, str, dict, dict]:
    extracted_text = _read_document_text(original_path)
    findings = _detect_sensitive_data(extracted_text)
    risk = _build_risk_summary(findings)
    total_items = _count_sensitive_items(findings)
    lifecycle = build_lifecycle_policy(original_filename, risk)
    document = create_document_record(
        document_id=document_id,
        original_filename=original_filename,
        original_path=str(original_path),
        findings=findings,
        risk=risk,
        total_sensitive_items=total_items,
        actor=actor,
        status="SCANNED",
        lifecycle=lifecycle,
    )
    record_artifact(
        document_id,
        "original",
        str(original_path),
        original_path.name,
        {"stored_in": "vault", "kind": "original"},
    )
    log_scan_event(
        filename=original_filename,
        risk_level=str(risk.get("level", "Low")),
        risk_score=int(risk.get("score", 0)),
        total_sensitive_items=total_items,
        source=source,
        counts=risk.get("counts", {}),
        document_id=document_id,
    )
    log_audit_event(
        event_type="scan",
        actor=actor,
        source=source,
        details={
            "document_id": document_id,
            "filename": original_filename,
            "risk_level": risk.get("level", "Low"),
            "risk_score": risk.get("score", 0),
            "total_sensitive_items": total_items,
        },
    )
    return document, original_path, extracted_text, findings, risk



def _register_path_document(source_path: Path, actor: str, source: str = "watch_folder") -> tuple[dict, Path, str, dict, dict]:
    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {source_path.suffix}")
    document_id = generate_document_id(datetime.now(timezone.utc).strftime("%Y"))
    original_filename, original_path = _copy_original_to_vault(source_path, document_id)
    return _register_document_record(
        document_id=document_id,
        original_filename=original_filename,
        original_path=original_path,
        actor=actor,
        source=source,
    )


def _load_document_context(document_id: str) -> tuple[dict, Path, str, dict, dict]:
    document = get_document(document_id)
    if not document:
        raise FileNotFoundError(f"Document {document_id} was not found.")
    original_path = Path(str(document["original_path"]))
    if not original_path.exists():
        raise FileNotFoundError(f"Original file for {document_id} is missing from the vault.")
    extracted_text = _read_document_text(original_path)
    findings = document.get("findings") or _detect_sensitive_data(extracted_text)
    risk = _build_risk_summary(findings)
    return document, original_path, extracted_text, findings, risk


def _write_compliance_report(
    document: dict,
    findings: dict,
    risk: dict,
    outputs: dict,
    *,
    actions_applied: list[str],
    final_text: str | None = None,
    redaction_quality: dict | None = None,
    encryption_status: str = "not_required",
    workflow_status: str = "ALLOWED",
) -> tuple[Path, dict]:
    report_name = _artifact_filename(document, "report", "json")
    report_path = ensure_vault_layout()["reports"] / report_name
    if final_text is None and encryption_status == "encrypted":
        risk_after = _protected_placeholder_summary()
    elif final_text is None:
        risk_after = risk
    else:
        risk_after = _build_risk_summary(_detect_sensitive_data(final_text))

    payload = {
        "document_id": document["document_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": document.get("original_filename"),
        "workflow_status": workflow_status,
        "policy": risk.get("policy", {}),
        "sensitive_items_detected": _count_sensitive_items(findings),
        "findings": findings,
        "risk_before_protection": risk,
        "risk_after_protection": risk_after,
        "actions_applied": actions_applied,
        "redaction_quality": redaction_quality,
        "encryption_status": encryption_status,
        "outputs": outputs,
        "compliance_basis": "Kenya Data Protection Act (2019)",
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    record_artifact(
        document["document_id"],
        "report",
        str(report_path),
        report_path.name,
        {"status": workflow_status, "encryption_status": encryption_status},
    )
    return report_path, payload


def _result_label(document: dict) -> str:
    artifacts = document.get("artifacts") or {}
    if artifacts.get("encrypted"):
        return "Encrypted"
    if artifacts.get("redacted"):
        return "Redacted"
    return "Allowed"


def _document_payload(document: dict) -> dict:
    document = _ensure_document_lifecycle(document)
    artifacts = document.get("artifacts") or {}
    lifecycle = evaluate_lifecycle(document)
    update_document_fields(
        document["document_id"],
        lifecycle_status=str(lifecycle.get("lifecycle_status", "Active")).lower().replace(" ", "_"),
        lifecycle_next_action=lifecycle.get("next_action", "Monitor lifecycle"),
    )
    status_label = _result_label(document)
    download_artifact = artifacts.get("redacted") or artifacts.get("original")
    report_artifact = artifacts.get("report")
    deleted = bool(document.get("deleted_at"))
    archived = bool(document.get("archived_at"))
    lifecycle_actions = []
    if not deleted and not archived and lifecycle.get("lifecycle_status") in {"Expired", "Expiring Soon"}:
        lifecycle_actions.append("archive")
    if not deleted and lifecycle.get("lifecycle_status") in {"Expired", "Archived"}:
        lifecycle_actions.append("secure_delete")
    return {
        "document_id": document["document_id"],
        "filename": document.get("original_filename"),
        "risk_level": document.get("risk_level"),
        "risk_score": document.get("risk_score"),
        "status": document.get("status"),
        "status_label": status_label,
        "created_at": document.get("created_at"),
        "download_url": (
            f"/api/documents/{document['document_id']}/artifacts/{download_artifact['artifact_type']}/download"
            if download_artifact and not deleted else None
        ),
        "report_url": (
            f"/api/documents/{document['document_id']}/artifacts/report/download"
            if report_artifact and not deleted else None
        ),
        "open_url": (
            f"/api/documents/{document['document_id']}/open"
            if artifacts.get("encrypted") and not deleted else None
        ),
        "artifacts": {key: True for key in artifacts.keys()},
        "owner": lifecycle.get("owner"),
        "department": lifecycle.get("department"),
        "retention_days": lifecycle.get("retention_days"),
        "retention_until": lifecycle.get("retention_until"),
        "retention_label": lifecycle.get("retention_label"),
        "days_remaining": lifecycle.get("days_remaining"),
        "lifecycle_status": lifecycle.get("lifecycle_status"),
        "next_action": lifecycle.get("next_action"),
        "policy_name": lifecycle.get("policy_name"),
        "archive_path": lifecycle.get("archive_path"),
        "lifecycle_actions": lifecycle_actions,
    }


def _workspace_payload() -> dict:
    documents = [_document_payload(document) for document in list_documents(limit=20)]
    vault_metrics = vault_summary()
    summary = summarize_scan_events(limit=50)
    summary["documents_scanned"] = int(vault_metrics.get("documents_total", 0))
    summary["protected_outputs"] = int(vault_metrics.get("protected_documents", 0))
    summary["high_risk_alerts"] = int(vault_metrics.get("high_risk_documents", 0))
    lifecycle_summary = {
        "active": int(vault_metrics.get("active_documents", 0)),
        "expiring": int(vault_metrics.get("expiring_documents", 0)),
        "expired": int(vault_metrics.get("expired_documents", 0)),
        "archived": int(vault_metrics.get("archived_documents", 0)),
        "deleted": int(vault_metrics.get("deleted_documents", 0)),
    }
    return {
        "summary": summary,
        "recent_files": documents,
        "activity": list_recent_audit_events(limit=12),
        "watch_folder": _watch_folder_payload(),
        "vault_summary": vault_metrics,
        "lifecycle_summary": lifecycle_summary,
        "lifecycle_engine": lifecycle_state(),
        "settings": _system_settings_payload(),
        "demo": {
            "watch_folder": _demo_watch_folder_path(),
            "target_count": _demo_target_count(),
        },
        "user": current_user(),
    }


def _run_policy_pipeline(
    document: dict,
    source_text: str,
    findings: dict,
    risk: dict,
    *,
    actor: str | None = None,
    source: str = "web",
) -> dict:
    actor_name = actor or _actor_name()
    policy = risk.get("policy", {})
    policy_mode = str(policy.get("mode", "allow"))
    outputs: dict[str, str] = {}
    actions_applied: list[str] = []
    completed_steps = [
        "Sensitive data detected" if _count_sensitive_items(findings) else "No sensitive data detected",
    ]
    response_download_url = f"/api/documents/{document['document_id']}/artifacts/original/download"
    response_download_label = document.get("original_filename", "original")
    preview_text = source_text[:700]
    redaction_quality = None
    workflow_status = "ALLOWED"
    encryption_status = "not_required"
    final_text = source_text

    if policy_mode in {"redact", "redact_encrypt"}:
        redacted_text = _redact_text(source_text, findings)
        redacted_name = _artifact_filename(document, "redacted", "txt")
        redacted_path = ensure_vault_layout()["redacted"] / redacted_name
        redacted_path.write_text(redacted_text, encoding="utf-8")
        redaction_quality = _verify_redaction_quality(findings, redacted_text)
        record_artifact(
            document["document_id"],
            "redacted",
            str(redacted_path),
            redacted_path.name,
            {
                "quality_status": redaction_quality["quality_status"],
                "coverage_percent": redaction_quality["coverage_percent"],
            },
        )
        outputs["redacted_file"] = str(redacted_path)
        actions_applied.append("redact")
        completed_steps.append("Document redacted")
        preview_text = redacted_text[:700]
        response_download_url = f"/api/documents/{document['document_id']}/artifacts/redacted/download"
        response_download_label = redacted_path.name
        workflow_status = "PROTECTED"
        final_text = redacted_text
    else:
        completed_steps.append("Document allowed")

    if policy_mode == "redact_encrypt":
        key = _generate_encryption_key()
        key_path = wrap_document_key(document["document_id"], key)
        record_artifact(
            document["document_id"],
            "key",
            str(key_path),
            key_path.name,
            {"wrapped_by": "vault", "algorithm": "Fernet"},
        )
        encrypted_text = _encrypt_text(source_text, key)
        encrypted_name = _artifact_filename(document, "encrypted", "txt")
        encrypted_path = ensure_vault_layout()["encrypted"] / encrypted_name
        encrypted_path.write_text(encrypted_text, encoding="utf-8")
        record_artifact(
            document["document_id"],
            "encrypted",
            str(encrypted_path),
            encrypted_path.name,
            {"content_scope": "original_document", "algorithm": "Fernet"},
        )
        outputs["encrypted_file"] = str(encrypted_path)
        actions_applied.append("encrypt")
        completed_steps.append("Original encrypted")
        encryption_status = "encrypted"
        workflow_status = "SECURED"

    report_path, _report_payload = _write_compliance_report(
        document,
        findings,
        risk,
        outputs,
        actions_applied=actions_applied,
        final_text=final_text,
        redaction_quality=redaction_quality,
        encryption_status=encryption_status,
        workflow_status=workflow_status,
    )
    outputs["report_file"] = str(report_path)
    completed_steps.append("Vault updated")
    update_document_status(document["document_id"], workflow_status)
    log_audit_event(
        event_type="policy_auto_protect",
        actor=actor_name,
        source=source,
        details={
            "document_id": document["document_id"],
            "filename": document.get("original_filename"),
            "policy_mode": policy_mode,
            "workflow_status": workflow_status,
            "actions_applied": actions_applied,
            "report_file": str(report_path),
        },
    )

    status_label = "Encrypted" if policy_mode == "redact_encrypt" else "Redacted" if policy_mode == "redact" else "Allowed"
    return {
        "document_id": document["document_id"],
        "filename": document.get("original_filename"),
        "risk_level": risk.get("level"),
        "risk_score": risk.get("score"),
        "counts": risk.get("counts", {}),
        "policy": policy,
        "recommendations": risk.get("recommendations", []),
        "insights": risk.get("insights", []),
        "status": workflow_status,
        "status_label": status_label,
        "completed_steps": completed_steps,
        "download": {
            "label": response_download_label,
            "url": response_download_url,
        },
        "report": {
            "label": report_path.name,
            "url": f"/api/documents/{document['document_id']}/artifacts/report/download",
        },
        "open_url": f"/api/documents/{document['document_id']}/open" if policy_mode == "redact_encrypt" else None,
        "preview": preview_text,
        "findings": findings,
    }


def _process_watch_file(file_path: Path) -> dict | None:
    actor = "folder-monitor"
    document, _original_path, source_text, findings, risk = _register_path_document(file_path, actor=actor, source="watch_folder")
    payload = _run_policy_pipeline(document, source_text, findings, risk, actor=actor, source="watch_folder")
    log_audit_event(
        event_type="watch_folder_processed",
        actor=actor,
        source="watch_folder",
        details={
            "document_id": payload["document_id"],
            "filename": payload["filename"],
            "watch_path": str(file_path),
            "status": payload["status"],
        },
    )
    return payload


def _ensure_background_vault_access() -> bool:
    if vault_is_unlocked():
        return True
    if not vault_is_configured() or vault_uses_system_master_key():
        try:
            unlock_vault(get_default_master_key(), "automation-engine", key_mode="system")
            return True
        except ValueError:
            return False
    return False


def _ensure_watch_service() -> None:
    if get_watch_folder_state().get("enabled") and _ensure_background_vault_access():
        ensure_watch_folder_running(_process_watch_file)

def _lock_vault_session() -> None:
    session["vault_unlocked"] = False


def _select_folder_dialog() -> str:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="Select Watch Folder")
    finally:
        root.destroy()
    return str(selected or "").strip()



def _demo_target_count() -> int:
    return int(get_demo_target_count())


def _demo_watch_folder_path() -> str:
    return str(get_demo_watch_folder_path())



def _watch_folder_payload() -> dict:
    state = get_watch_folder_state()
    if not state.get("path"):
        state["path"] = _demo_watch_folder_path()
    return state


def _validate_watch_folder(folder_path: str) -> Path:
    if not folder_path:
        raise ValueError("Watch folder path is required.")
    resolved = Path(folder_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError("Watch folder must be an existing directory.")

    vault_root = ensure_vault_layout()["root"].resolve()
    if resolved == vault_root or resolved.is_relative_to(vault_root) or vault_root.is_relative_to(resolved):
        raise ValueError("Watch folder cannot be the vault or contain the vault.")
    return resolved


@app.route("/")
@require_login
def home():
    return dashboard()


@app.route("/dashboard")
@require_login
def dashboard():
    demo_watch_folder = _demo_watch_folder_path()
    demo_file_count = _demo_target_count()
    if session.pop("allow_dashboard_once", False):
        return render_template(
            "dashboard.html",
            user=current_user(),
            demo_watch_folder=demo_watch_folder,
            demo_file_count=demo_file_count,
            asset_version=_dashboard_asset_version(),
        )
    _lock_vault_session()
    return render_template(
        "dashboard.html",
        user=current_user(),
        demo_watch_folder=demo_watch_folder,
        demo_file_count=demo_file_count,
            asset_version=_dashboard_asset_version(),
    )


@app.route("/launch")
@require_login
def launch():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", vault_configured=vault_is_configured())

    payload = request.get_json(silent=True) or request.form
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    _apply_profile_session(user["username"], role=user["role"])
    session["vault_unlocked"] = False
    session["allow_dashboard_once"] = True
    _ensure_lifecycle_service()
    return jsonify({"message": "Login successful"})


@app.route("/api/vault/unlock", methods=["POST"])
@require_login
def vault_unlock_api():
    payload = request.get_json(silent=True) or request.form
    pin = str(payload.get("pin", "")).strip()
    user = current_user() or {}
    username = str(user.get("username") or session.get("username") or "local-user")

    vault_password = pin
    vault_key_mode = "system" if (not vault_is_configured() or vault_uses_system_master_key()) else "user"

    try:
        unlock_vault(vault_password, username, key_mode=vault_key_mode)
    except ValueError:
        session["vault_unlocked"] = False
        return jsonify({"error": "Invalid master PIN"}), 401

    session["vault_unlocked"] = True
    _ensure_watch_service()
    _ensure_lifecycle_service()
    return jsonify({"message": "Vault unlocked", "user": current_user()})


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    session.clear()
    stop_watch_folder_runner()
    stop_lifecycle_runner()
    lock_vault()
    return jsonify({"message": "Logged out"})


@app.route("/api/workspace")
@require_login
def workspace_api():
    _ensure_watch_service()
    _ensure_lifecycle_service()
    return jsonify(_workspace_payload())

@app.route("/api/profile", methods=["GET"])
@require_login
def profile_api():
    username = str(session.get("username", "")).strip()
    if not username:
        return jsonify({"error": "Authentication required"}), 401
    _apply_profile_session(username)
    return jsonify(current_user())


@app.route("/api/profile", methods=["POST"])
@require_login
def update_profile_api():
    username = str(session.get("username", "")).strip()
    if not username:
        return jsonify({"error": "Authentication required"}), 401

    payload = request.get_json(silent=True) or request.form
    profile = update_profile(
        username,
        display_name=payload.get("display_name"),
        theme=payload.get("theme"),
    )
    _apply_profile_session(username)
    log_audit_event(
        event_type="profile_updated",
        actor=_actor_name(),
        source="web",
        details={
            "display_name": profile.get("display_name"),
            "theme": profile.get("theme"),
        },
    )
    return jsonify(current_user())


@app.route("/api/profile/avatar", methods=["POST"])
@require_login
def upload_profile_avatar_api():
    username = str(session.get("username", "")).strip()
    if not username:
        return jsonify({"error": "Authentication required"}), 401
    if "avatar" not in request.files:
        return jsonify({"error": "No avatar uploaded"}), 400

    file_obj = request.files["avatar"]
    if not file_obj.filename:
        return jsonify({"error": "No avatar uploaded"}), 400

    try:
        current_profile = _profile_payload(username)
        avatar_url = _save_avatar(file_obj, username, current_profile.get("avatar_url", ""))
        update_profile(username, avatar_url=avatar_url)
        _apply_profile_session(username)
        log_audit_event(
            event_type="profile_avatar_updated",
            actor=_actor_name(),
            source="web",
            details={"avatar_url": avatar_url},
        )
        return jsonify(current_user())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/system-settings", methods=["GET"])
@require_login
def system_settings_api():
    return jsonify(_system_settings_payload())


@app.route("/api/system-settings", methods=["POST"])
@require_login
def update_system_settings_api():
    payload = request.get_json(silent=True) or request.form
    settings = _save_lifecycle_settings(payload)
    log_audit_event(
        event_type="lifecycle_settings_updated",
        actor=_actor_name(),
        source="web",
        details=settings,
    )
    return jsonify(settings)


@app.route("/api/vault/pin", methods=["POST"])
@require_login
@require_vault_unlock
def change_vault_pin_api():
    payload = request.get_json(silent=True) or request.form
    current_pin = str(payload.get("current_pin", "")).strip()
    new_pin = str(payload.get("new_pin", "")).strip()
    if len(new_pin) < 4:
        return jsonify({"error": "New vault PIN must be at least 4 characters."}), 400
    try:
        status = change_master_password(current_pin, new_pin)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if vault_uses_system_master_key():
        save_local_system_config({"vault": {"default_master_key": new_pin}})
    log_audit_event(
        event_type="vault_pin_changed",
        actor=_actor_name(),
        source="web",
        details={"key_mode": status.get("key_mode")},
    )
    return jsonify({"message": "Vault PIN updated successfully.", "vault": status})


@app.route("/api/watch-folder/pick", methods=["POST"])
@require_login
def watch_folder_picker_api():
    selected = _select_folder_dialog()
    if not selected:
        return jsonify({"error": "No folder selected"}), 400
    resolved = _validate_watch_folder(selected)
    return jsonify({"path": str(resolved)})


@app.route("/api/watch-folder", methods=["GET"])
@require_login
def watch_folder_status_api():
    return jsonify(_watch_folder_payload())


@app.route("/api/watch-folder", methods=["POST"])
@require_login
def watch_folder_enable_api():
    payload = request.get_json(silent=True) or request.form
    requested_path = str(payload.get("path", "")).strip()
    if requested_path and Path(requested_path).expanduser().resolve() == get_demo_watch_folder_path().resolve():
        ensure_demo_watch_folder(target_count=_demo_target_count())
    resolved = _validate_watch_folder(requested_path)
    previous_path = str(get_watch_folder_state().get("path") or "")
    force_rescan = bool(payload.get("force_rescan", False))
    if not _ensure_background_vault_access():
        return jsonify({"error": "Unlock the vault once with the system master PIN to enable automatic folder protection."}), 423
    state = configure_watch_folder(str(resolved), _actor_name(), reset_progress=force_rescan)
    ensure_watch_folder_running(
        _process_watch_file,
        force_restart=force_rescan or previous_path != str(resolved),
    )
    log_audit_event(
        event_type="watch_folder_enabled",
        actor=_actor_name(),
        source="web",
        details={"path": state.get("path"), "force_rescan": force_rescan},
    )
    return jsonify(state)



@app.route("/api/watch-folder", methods=["DELETE"])
@require_login
def watch_folder_disable_api():
    state = disable_watch_folder(_actor_name())
    log_audit_event(
        event_type="watch_folder_disabled",
        actor=_actor_name(),
        source="web",
        details={"path": state.get("path")},
    )
    return jsonify(state)


@app.route("/api/demo/rebuild", methods=["POST"])
@require_login
def demo_rebuild_api():
    if not _ensure_background_vault_access():
        return jsonify({"error": "Unlock the vault once with the system master PIN to rebuild the demo workflow."}), 423

    stop_watch_folder_runner()
    summary = rebuild_demo_workspace(target_count=_demo_target_count())
    state = configure_watch_folder(summary["watch_folder"], _actor_name(), reset_progress=True)
    ensure_watch_folder_running(_process_watch_file, force_restart=True)
    log_audit_event(
        event_type="demo_workflow_rebuilt",
        actor=_actor_name(),
        source="web",
        details={
            "watch_folder": summary["watch_folder"],
            "target_count": summary["target_count"],
            "seeded_file_count": summary["seeded_file_count"],
            "removed_watch_files": summary["removed_watch_files"],
            "reset_database_rows": summary["reset_database_rows"],
            "removed_vault_files": summary["removed_vault_files"],
        },
    )
    return jsonify(
        {
            "message": f"Rebuilt {summary['seeded_file_count']} synthetic demo files and restarted WATCH FOLDER.",
            "demo": summary,
            "watch_folder": state,
        }
    )



@app.route("/api/demo/reset", methods=["POST"])
@require_login
def demo_reset_api():
    stop_watch_folder_runner()
    stop_lifecycle_runner()
    summary = clear_demo_workspace()
    state = disable_watch_folder(_actor_name())
    log_audit_event(
        event_type="demo_workflow_reset",
        actor=_actor_name(),
        source="web",
        details={
            "watch_folder": summary["watch_folder"],
            "removed_watch_files": summary["removed_watch_files"],
            "reset_database_rows": summary["reset_database_rows"],
            "removed_vault_files": summary["removed_vault_files"],
        },
    )
    return jsonify(
        {
            "message": "Terminated the demo pipeline and cleared all dashboard, watch-folder, and vault activity.",
            "demo": summary,
            "watch_folder": state,
            "workspace": _workspace_payload(),
        }
    )
@app.route("/api/documents/<document_id>/lifecycle/archive", methods=["POST"])
@require_login
@require_vault_unlock
def archive_document_lifecycle(document_id: str):
    document = get_document(document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    updated = _archive_document_by_id(document_id, actor=_actor_name(), source="web")
    return jsonify({"message": "Document archived", "document": _document_payload(updated)})


@app.route("/api/documents/<document_id>/lifecycle/delete", methods=["POST"])
@require_login
@require_vault_unlock
def secure_delete_document_lifecycle(document_id: str):
    document = get_document(document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    updated = _secure_delete_document_by_id(document_id, actor=_actor_name(), source="web")
    return jsonify({"message": "Document securely deleted", "document": _document_payload(updated)})


@app.route("/api/documents/<document_id>/artifacts/<artifact_type>/download")
@require_login
@require_vault_unlock
def download_document_artifact(document_id: str, artifact_type: str):
    artifact = get_latest_artifact(document_id, artifact_type)
    if not artifact:
        return jsonify({"error": "Artifact not found"}), 404
    artifact_path = Path(str(artifact["file_path"]))
    vault_root = ensure_vault_layout()["root"].resolve()
    if not artifact_path.is_file() or not artifact_path.resolve().is_relative_to(vault_root):
        return jsonify({"error": "Artifact file not found"}), 404
    return send_file(artifact_path, as_attachment=True, download_name=artifact["filename"])


@app.route("/api/documents/<document_id>/open", methods=["POST"])
@require_login
@require_vault_unlock
def open_document(document_id: str):
    document, original_path, _source_text, _findings, _risk = _load_document_context(document_id)
    artifacts = document.get("artifacts") or {}

    try:
        if artifacts.get("encrypted"):
            encrypted_path = Path(str(artifacts["encrypted"]["file_path"]))
            token = encrypted_path.read_text(encoding="utf-8").strip()
            plain_text = _decrypt_text(token, unwrap_document_key(document_id))
            opened_as = "Encrypted"
        elif artifacts.get("redacted"):
            redacted_path = Path(str(artifacts["redacted"]["file_path"]))
            plain_text = redacted_path.read_text(encoding="utf-8")
            opened_as = "Redacted"
        else:
            plain_text = _read_document_text(original_path)
            opened_as = "Allowed"

        log_audit_event(
            event_type="open_document",
            actor=_actor_name(),
            source="web",
            details={
                "document_id": document_id,
                "opened_as": opened_as,
            },
        )
        return jsonify(
            {
                "document_id": document_id,
                "filename": document.get("original_filename"),
                "opened_as": opened_as,
                "content": plain_text,
            }
        )
    except Exception:
        return jsonify({"error": "Unable to open this document right now."}), 400



@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
if __name__ == "__main__":
    _ensure_lifecycle_service()
    app.run(
        host=os.environ.get("PRIVGUARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("PRIVGUARD_DEBUG", "0") == "1",
    )






































