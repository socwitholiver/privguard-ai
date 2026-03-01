"""Offline text extraction utilities for PRIVGUARD AI.

Supports plain text-like files and image OCR using local Tesseract.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
import pytesseract
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency import path
    PdfReader = None
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency import path
    fitz = None


TEXT_SUFFIXES = {".txt", ".md", ".csv", ".log"}
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _extract_text_from_image(path: Path) -> str:
    """Run lightweight preprocessing + OCR on an image file."""
    image = Image.open(path)
    # Improve OCR quality with grayscale and auto contrast.
    processed = ImageOps.autocontrast(ImageOps.grayscale(image))
    # psm 6 assumes a block of text, suitable for forms/documents.
    return pytesseract.image_to_string(processed, config="--oem 3 --psm 6")


def _extract_text_from_pdf(path: Path) -> str:
    """Extract text from PDF pages using local parser (no cloud).

    Strategy:
    1) Try native text extraction via pypdf.
    2) If empty, fallback to OCR by rasterizing pages with PyMuPDF.
    """
    if PdfReader is None:
        raise RuntimeError(
            "PDF support requires 'pypdf'. Install dependencies from requirements.txt."
        )
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    text = "\n".join(chunks).strip()
    if text:
        return text

    if fitz is None:
        raise RuntimeError(
            "This PDF appears image-based. Install 'pymupdf' for scanned PDF OCR fallback."
        )

    try:
        ocr_chunks = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                processed = ImageOps.autocontrast(ImageOps.grayscale(image))
                ocr_chunks.append(
                    pytesseract.image_to_string(processed, config="--oem 3 --psm 6")
                )
        return "\n".join(ocr_chunks).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or not in PATH. "
            "Install Tesseract locally for offline PDF OCR fallback."
        ) from exc


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

    if suffix in PDF_SUFFIXES:
        try:
            return _extract_text_from_pdf(path)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Failed to extract text from PDF: {exc}") from exc

    if suffix in IMAGE_SUFFIXES:
        try:
            return _extract_text_from_image(path)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR is not installed or not in PATH. "
                "Install Tesseract locally for offline image text extraction."
            ) from exc

    raise ValueError(
        "Unsupported file type. Use text/PDF files "
        "(.txt, .md, .csv, .log, .pdf) or images (.png, .jpg, .jpeg, .bmp, .tiff, .webp)."
    )
