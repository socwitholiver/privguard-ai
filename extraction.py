"""Offline text extraction utilities for PRIVGUARD AI.

Supports plain text-like files and image OCR using local Tesseract.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
import pytesseract


TEXT_SUFFIXES = {".txt", ".md", ".csv", ".log"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _extract_text_from_image(path: Path) -> str:
    """Run lightweight preprocessing + OCR on an image file."""
    image = Image.open(path)
    # Improve OCR quality with grayscale and auto contrast.
    processed = ImageOps.autocontrast(ImageOps.grayscale(image))
    # psm 6 assumes a block of text, suitable for forms/documents.
    return pytesseract.image_to_string(processed, config="--oem 3 --psm 6")


def read_document_text(path: Path) -> str:
    """Read a supported document path and return extracted text.

    Raises:
        FileNotFoundError: If input path does not exist.
        ValueError: If path is not file or unsupported type.
        RuntimeError: If OCR is unavailable for image extraction.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix in IMAGE_SUFFIXES:
        try:
            return _extract_text_from_image(path)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR is not installed or not in PATH. "
                "Install Tesseract locally for offline image text extraction."
            ) from exc

    raise ValueError(
        "Unsupported file type. Use text files "
        "(.txt, .md, .csv, .log) or images (.png, .jpg, .jpeg, .bmp, .tiff, .webp)."
    )
