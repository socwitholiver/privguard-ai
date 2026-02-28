import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from classification import build_risk_summary
from detection import detect_sensitive_data
from extraction import read_document_text
from protection import encrypt_text, generate_encryption_key, redact_text, verify_redaction_quality

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
KEY_FOLDER = "keys"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(KEY_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# In-memory scan history (last 10 only)
scan_history = []


def _save_upload(file_obj, destination_dir: str) -> Path:
    filename = secure_filename(file_obj.filename)
    filepath = Path(destination_dir) / filename
    file_obj.save(str(filepath))
    return filepath


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard-data")
def dashboard_data():
    return jsonify({"recent_scans": scan_history})


@app.route("/scan", methods=["POST"])
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
        }
        scan_history.insert(0, scan_entry)
        scan_history = scan_history[:10]

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
        return jsonify(quality)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True)