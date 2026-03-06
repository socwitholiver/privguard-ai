import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from automation.folder_watch import (
    configure_watch_folder,
    disable_watch_folder,
    ensure_watch_folder_running,
    get_watch_folder_state,
    stop_watch_folder_runner,
)
from classification import build_risk_summary
from detection import count_sensitive_items, detect_sensitive_data
from extraction import read_document_text
from protection import (
    decrypt_text,
    encrypt_text,
    generate_encryption_key,
    redact_text,
    verify_redaction_quality,
)
from security.auth import authenticate_user, current_user, require_login, require_vault_unlock
from security.vault import (
    ensure_vault_layout,
    lock_vault,
    unlock_vault,
    unwrap_document_key,
    vault_is_configured,
    vault_is_unlocked,
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
    generate_document_id,
    get_document,
    get_latest_artifact,
    list_documents,
    record_artifact,
    update_document_status,
)

app = Flask(__name__)
app.secret_key = os.environ.get("PRIVGUARD_SECRET_KEY", "privguard-dev-secret-change-me")
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


def _save_uploaded_original(file_obj) -> tuple[str, str, Path]:
    if not file_obj or not file_obj.filename:
        raise ValueError("A valid file is required.")
    filename = secure_filename(file_obj.filename)
    if not filename:
        raise ValueError("Empty filename")
    document_id = generate_document_id(datetime.now(timezone.utc).strftime("%Y"))
    original_path = ensure_vault_layout()["originals"] / f"{document_id}__{filename}"
    file_obj.save(str(original_path))
    return document_id, filename, original_path


def _register_document_record(
    *,
    document_id: str,
    original_filename: str,
    original_path: Path,
    actor: str,
    source: str,
) -> tuple[dict, Path, str, dict, dict]:
    extracted_text = read_document_text(original_path)
    findings = detect_sensitive_data(extracted_text)
    risk = build_risk_summary(findings)
    total_items = count_sensitive_items(findings)
    document = create_document_record(
        document_id=document_id,
        original_filename=original_filename,
        original_path=str(original_path),
        findings=findings,
        risk=risk,
        total_sensitive_items=total_items,
        actor=actor,
        status="SCANNED",
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


def _register_uploaded_document(file_obj, actor: str | None = None, source: str = "web") -> tuple[dict, Path, str, dict, dict]:
    actor_name = actor or _actor_name()
    document_id, original_filename, original_path = _save_uploaded_original(file_obj)
    return _register_document_record(
        document_id=document_id,
        original_filename=original_filename,
        original_path=original_path,
        actor=actor_name,
        source=source,
    )


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
    extracted_text = read_document_text(original_path)
    findings = document.get("findings") or detect_sensitive_data(extracted_text)
    risk = build_risk_summary(findings)
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
        risk_after = build_risk_summary(detect_sensitive_data(final_text))

    payload = {
        "document_id": document["document_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": document.get("original_filename"),
        "workflow_status": workflow_status,
        "policy": risk.get("policy", {}),
        "sensitive_items_detected": count_sensitive_items(findings),
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
    artifacts = document.get("artifacts") or {}
    status_label = _result_label(document)
    download_artifact = artifacts.get("redacted") or artifacts.get("original")
    report_artifact = artifacts.get("report")
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
            if download_artifact else None
        ),
        "report_url": (
            f"/api/documents/{document['document_id']}/artifacts/report/download"
            if report_artifact else None
        ),
        "open_url": (
            f"/api/documents/{document['document_id']}/open"
            if artifacts.get("encrypted") else None
        ),
        "artifacts": {key: True for key in artifacts.keys()},
    }


def _workspace_payload() -> dict:
    documents = [_document_payload(document) for document in list_documents(limit=20)]
    return {
        "summary": summarize_scan_events(limit=50),
        "recent_files": documents,
        "activity": list_recent_audit_events(limit=12),
        "watch_folder": get_watch_folder_state(),
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
        "Sensitive data detected" if count_sensitive_items(findings) else "No sensitive data detected",
    ]
    response_download_url = f"/api/documents/{document['document_id']}/artifacts/original/download"
    response_download_label = document.get("original_filename", "original")
    preview_text = source_text[:700]
    redaction_quality = None
    workflow_status = "ALLOWED"
    encryption_status = "not_required"
    final_text = source_text

    if policy_mode in {"redact", "redact_encrypt"}:
        redacted_text = redact_text(source_text, findings)
        redacted_name = _artifact_filename(document, "redacted", "txt")
        redacted_path = ensure_vault_layout()["redacted"] / redacted_name
        redacted_path.write_text(redacted_text, encoding="utf-8")
        redaction_quality = verify_redaction_quality(findings, redacted_text)
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
        key = generate_encryption_key()
        key_path = wrap_document_key(document["document_id"], key)
        record_artifact(
            document["document_id"],
            "key",
            str(key_path),
            key_path.name,
            {"wrapped_by": "vault", "algorithm": "Fernet"},
        )
        encrypted_text = encrypt_text(source_text, key)
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


def _ensure_watch_service() -> None:
    if vault_is_unlocked() and get_watch_folder_state().get("enabled"):
        ensure_watch_folder_running(_process_watch_file)


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
@require_vault_unlock
def home():
    return render_template("dashboard.html", user=current_user())


@app.route("/dashboard")
@require_login
@require_vault_unlock
def dashboard():
    return render_template("dashboard.html", user=current_user())


@app.route("/launch")
@require_login
@require_vault_unlock
def launch():
    return render_template("launch.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", vault_configured=vault_is_configured())

    payload = request.get_json(silent=True) or request.form
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    supplied_master_password = str(payload.get("master_password", "")).strip()
    master_password = supplied_master_password or password
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    try:
        unlock_vault(master_password, user["username"])
    except ValueError:
        return jsonify({
            "error": "Unlock failed. If your master password differs from your sign-in password, use the separate master password option.",
        }), 401

    _apply_profile_session(user["username"], role=user["role"])
    session["vault_unlocked"] = True
    _ensure_watch_service()
    return jsonify({"message": "Login successful"})


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    session.clear()
    stop_watch_folder_runner()
    lock_vault()
    return jsonify({"message": "Logged out"})


@app.route("/api/workspace")
@require_login
@require_vault_unlock
def workspace_api():
    _ensure_watch_service()
    return jsonify(_workspace_payload())
@app.route("/api/profile", methods=["GET"])
@require_login
@require_vault_unlock
def profile_api():
    username = str(session.get("username", "")).strip()
    if not username:
        return jsonify({"error": "Authentication required"}), 401
    _apply_profile_session(username)
    return jsonify(current_user())


@app.route("/api/profile", methods=["POST"])
@require_login
@require_vault_unlock
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
@require_vault_unlock
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


@app.route("/api/watch-folder", methods=["GET"])
@require_login
@require_vault_unlock
def watch_folder_status_api():
    _ensure_watch_service()
    return jsonify(get_watch_folder_state())


@app.route("/api/watch-folder", methods=["POST"])
@require_login
@require_vault_unlock
def watch_folder_enable_api():
    payload = request.get_json(silent=True) or request.form
    resolved = _validate_watch_folder(str(payload.get("path", "")).strip())
    state = configure_watch_folder(str(resolved), _actor_name())
    ensure_watch_folder_running(_process_watch_file)
    log_audit_event(
        event_type="watch_folder_enabled",
        actor=_actor_name(),
        source="web",
        details={"path": state.get("path")},
    )
    return jsonify(state)


@app.route("/api/watch-folder", methods=["DELETE"])
@require_login
@require_vault_unlock
def watch_folder_disable_api():
    state = disable_watch_folder(_actor_name())
    log_audit_event(
        event_type="watch_folder_disabled",
        actor=_actor_name(),
        source="web",
        details={"path": state.get("path")},
    )
    return jsonify(state)


@app.route("/automate", methods=["POST"])
@require_login
@require_vault_unlock
def automate():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        document, _path, source_text, findings, risk = _register_uploaded_document(file)
        payload = _run_policy_pipeline(document, source_text, findings, risk)
        payload["workspace"] = _workspace_payload()
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


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
            plain_text = decrypt_text(token, unwrap_document_key(document_id))
            opened_as = "Encrypted"
        elif artifacts.get("redacted"):
            redacted_path = Path(str(artifacts["redacted"]["file_path"]))
            plain_text = redacted_path.read_text(encoding="utf-8")
            opened_as = "Redacted"
        else:
            plain_text = read_document_text(original_path)
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


if __name__ == "__main__":
    app.run(
        host=os.environ.get("PRIVGUARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("PRIVGUARD_DEBUG", "0") == "1",
    )




