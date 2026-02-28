import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from classification import build_risk_summary
from detection import count_sensitive_items, detect_sensitive_data
from extraction import read_document_text
from ops.audit_export import export_signed_audit
from ops.ocr_diagnostics import run_ocr_diagnostics
from ops.retention import run_retention_cleanup
from protection import encrypt_text, generate_encryption_key, redact_text, verify_redaction_quality
from security.auth import (
    authenticate_user,
    current_user,
    require_login,
    require_permission,
)
from storage.audit_repo import log_audit_event, log_scan_event
from storage.db import init_db

app = Flask(__name__)
app.secret_key = os.environ.get("PRIVGUARD_SECRET_KEY", "privguard-dev-secret-change-me")

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
KEY_FOLDER = "keys"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(KEY_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
init_db()

# In-memory scan history (last 10 only)
scan_history = []


def _save_upload(file_obj, destination_dir: str) -> Path:
    filename = secure_filename(file_obj.filename)
    filepath = Path(destination_dir) / filename
    file_obj.save(str(filepath))
    return filepath


def _build_dashboard_summary() -> dict:
    total_scans = len(scan_history)
    risk_distribution = {"High": 0, "Medium": 0, "Low": 0}
    avg_risk_score = 0.0
    entity_totals = {
        "national_ids": 0,
        "phone_numbers": 0,
        "emails": 0,
        "kra_pins": 0,
    }

    for entry in scan_history:
        level = str(entry.get("risk_level", "Low"))
        if level in risk_distribution:
            risk_distribution[level] += 1
        avg_risk_score += float(entry.get("risk_score", 0))
        for key in entity_totals:
            entity_totals[key] += int(entry.get("counts", {}).get(key, 0))

    avg_risk_score = round(avg_risk_score / total_scans, 2) if total_scans else 0.0
    high_ratio = round((risk_distribution["High"] / total_scans) * 100, 2) if total_scans else 0.0
    trend_scores = [int(entry.get("risk_score", 0)) for entry in reversed(scan_history)]
    return {
        "documents_scanned": total_scans,
        "average_risk_score": avg_risk_score,
        "high_risk_ratio": high_ratio,
        "risk_distribution": risk_distribution,
        "entity_totals": entity_totals,
        "trend_scores": trend_scores,
    }


@app.route("/")
@require_login
def home():
    return render_template("dashboard.html", user=current_user())


@app.route("/dashboard")
@require_login
def dashboard():
    return render_template("dashboard.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    payload = request.get_json(silent=True) or request.form
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    from flask import session

    session["username"] = user["username"]
    session["role"] = user["role"]
    return jsonify({"message": "Login successful", "role": user["role"]})


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    from flask import session

    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/dashboard-data")
@require_permission("view_dashboard")
def dashboard_data():
    return jsonify({"recent_scans": scan_history, "summary": _build_dashboard_summary()})


@app.route("/scan", methods=["POST"])
@require_permission("scan")
def scan():
    global scan_history
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        path = _save_upload(file, app.config["UPLOAD_FOLDER"])
        extracted_text = read_document_text(path)
        findings = detect_sensitive_data(extracted_text)
        risk = build_risk_summary(findings)

        scan_entry = {
            "filename": path.name,
            "risk_level": risk["level"],
            "risk_score": risk["score"],
            "counts": risk["counts"],
        }
        scan_history.insert(0, scan_entry)
        scan_history = scan_history[:10]
        total_items = count_sensitive_items(findings)
        log_scan_event(path.name, risk["level"], risk["score"], total_items, source="web")
        log_audit_event(
            event_type="scan",
            actor="web-user",
            source="web",
            details={
                "filename": path.name,
                "risk_level": risk["level"],
                "risk_score": risk["score"],
                "total_sensitive_items": total_items,
            },
        )

        return jsonify(
            {
                "filename": path.name,
                "findings": findings,
                "risk_score": risk["score"],
                "risk_level": risk["level"],
                "counts": risk["counts"],
                "insights": risk["insights"],
                "extracted_preview": extracted_text[:700],
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/protect", methods=["POST"])
@require_permission("protect")
def protect():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    action = request.form.get("action", "").strip().lower()
    if action not in {"redact", "encrypt"}:
        return jsonify({"error": "Action must be redact or encrypt"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        path = _save_upload(file, app.config["UPLOAD_FOLDER"])
        source_text = read_document_text(path)
        findings = detect_sensitive_data(source_text)

        if action == "redact":
            protected = redact_text(source_text, findings)
            out_path = Path(OUTPUT_FOLDER) / f"{path.stem}.redacted.txt"
            out_path.write_text(protected, encoding="utf-8")
            quality = verify_redaction_quality(findings, protected)
            log_audit_event(
                event_type="protect_redact",
                actor="web-user",
                source="web",
                details={
                    "filename": path.name,
                    "output_file": str(out_path),
                    "quality_status": quality["quality_status"],
                    "leak_count": quality["leak_count"],
                },
            )
            return jsonify(
                {
                    "action": "redact",
                    "output_file": str(out_path),
                    "quality": quality,
                    "preview": protected[:700],
                }
            )

        key = generate_encryption_key()
        key_path = Path(KEY_FOLDER) / f"{path.stem}.key"
        key_path.write_bytes(key)
        encrypted = encrypt_text(source_text, key)
        out_path = Path(OUTPUT_FOLDER) / f"{path.stem}.encrypted.txt"
        out_path.write_text(encrypted, encoding="utf-8")
        log_audit_event(
            event_type="protect_encrypt",
            actor="web-user",
            source="web",
            details={
                "filename": path.name,
                "output_file": str(out_path),
                "key_file": str(key_path),
            },
        )
        return jsonify(
            {
                "action": "encrypt",
                "output_file": str(out_path),
                "key_file": str(key_path),
                "preview": encrypted[:220],
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/verify-redaction", methods=["POST"])
@require_permission("verify")
def verify_redaction():
    if "original" not in request.files or "protected" not in request.files:
        return jsonify({"error": "Upload both original and protected files"}), 400

    original = request.files["original"]
    protected = request.files["protected"]
    if original.filename == "" or protected.filename == "":
        return jsonify({"error": "Both files must have valid names"}), 400

    try:
        original_path = _save_upload(original, app.config["UPLOAD_FOLDER"])
        protected_path = _save_upload(protected, app.config["UPLOAD_FOLDER"])

        original_text = read_document_text(original_path)
        protected_text = read_document_text(protected_path)
        original_findings = detect_sensitive_data(original_text)
        quality = verify_redaction_quality(original_findings, protected_text)
        log_audit_event(
            event_type="verify_redaction",
            actor="web-user",
            source="web",
            details={
                "original_file": original_path.name,
                "protected_file": protected_path.name,
                "quality_status": quality["quality_status"],
                "leak_count": quality["leak_count"],
            },
        )
        return jsonify(quality)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/export-audit", methods=["POST"])
@require_permission("admin_export")
def admin_export_audit():
    try:
        result = export_signed_audit(limit=5000)
        user = current_user() or {"username": "unknown"}
        log_audit_event(
            event_type="export_audit",
            actor=user["username"],
            source="web",
            details=result,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/retention-cleanup", methods=["POST"])
@require_permission("admin_cleanup")
def admin_retention_cleanup():
    try:
        result = run_retention_cleanup()
        user = current_user() or {"username": "unknown"}
        log_audit_event(
            event_type="retention_cleanup",
            actor=user["username"],
            source="web",
            details=result,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/ocr-diagnostics", methods=["POST"])
@require_permission("admin_cleanup")
def admin_ocr_diagnostics():
    try:
        result = run_ocr_diagnostics()
        user = current_user() or {"username": "unknown"}
        log_audit_event(
            event_type="ocr_diagnostics",
            actor=user["username"],
            source="web",
            details=result,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True)