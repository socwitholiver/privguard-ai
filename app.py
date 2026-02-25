"""
PrivGuard AI — Flask Application

Handles:
- UI rendering
- Secure file uploads
- Running analysis pipeline
- Returning results

Security considerations:
- Validates uploaded file
- Uses safe upload directory
- Prevents empty uploads
"""

import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from backend.pipeline import PrivGuardPipeline

app = Flask(__name__)

# Initialize pipeline
pipeline = PrivGuardPipeline()

# Upload configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    """
    Check file extension for security.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    """
    Render main UI.
    """
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    """
    Handle file upload and analysis.
    """

    # Ensure file exists
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    # Validate filename
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Validate extension
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    # Secure filename
    filename = secure_filename(file.filename)

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        result = pipeline.run(filepath)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)