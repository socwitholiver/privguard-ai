"""Offline OCR diagnostics for environment readiness checks."""

from __future__ import annotations

from typing import Dict

import pytesseract


def run_ocr_diagnostics() -> Dict[str, object]:
    try:
        version = str(pytesseract.get_tesseract_version())
        return {
            "status": "ready",
            "tesseract_available": True,
            "tesseract_version": version,
            "message": "OCR engine is available for offline image extraction.",
        }
    except Exception as exc:
        return {
            "status": "not_ready",
            "tesseract_available": False,
            "message": "Tesseract OCR is not installed or not in PATH.",
            "error": str(exc),
        }
