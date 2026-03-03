"""Offline text extraction utilities for PRIVGUARD AI.

Supports plain text-like files and image OCR using local Tesseract.
Sharp preprocessing pipeline for unclear/blurry photos: upscale, denoise,
sharpen, and binarize to maximize sensitive-data detection.
Configurable via config/system_config.yaml under the `ocr` key.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageOps, ImageFilter
import pytesseract
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency import path
    PdfReader = None
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency import path
    fitz = None

# Optional: OpenCV for sharp preprocessing (denoise, sharpen, adaptive threshold)
try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    from config_loader import load_system_config
except ImportError:
    load_system_config = None


TEXT_SUFFIXES = {".txt", ".md", ".csv", ".log"}
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}

# Defaults when no config is present
_DEFAULT_OCR_CONFIG: Dict[str, Any] = {
    "sharp_preprocessing": True,
    "min_text_height_px": 1200,
    "max_dimension_px": 4000,
    "pdf_scale": 3,
}

# Runtime override from dashboard (instance/ocr_override.json) overrides YAML
_OCR_OVERRIDE_PATH = Path("instance/ocr_override.json")


def _get_ocr_config() -> Dict[str, Any]:
    """Return OCR settings from system config + optional dashboard override, with defaults."""
    out = dict(_DEFAULT_OCR_CONFIG)
    if load_system_config:
        try:
            cfg = load_system_config().get("ocr") or {}
            for k in out:
                if k in cfg and cfg[k] is not None:
                    out[k] = cfg[k]
        except Exception:
            pass
    # Dashboard override (toggle) takes precedence
    if _OCR_OVERRIDE_PATH.exists():
        try:
            raw = _OCR_OVERRIDE_PATH.read_text(encoding="utf-8")
            override = json.loads(raw)
            if "sharp_preprocessing" in override:
                out["sharp_preprocessing"] = bool(override["sharp_preprocessing"])
        except Exception:
            pass
    return out


def get_ocr_config() -> Dict[str, Any]:
    """Public API for current OCR settings (used by dashboard and API)."""
    return _get_ocr_config()


def set_ocr_override(sharp_preprocessing: bool) -> None:
    """Persist Sharp OCR toggle from dashboard; creates instance/ and file if needed."""
    _OCR_OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OCR_OVERRIDE_PATH.write_text(
        json.dumps({"sharp_preprocessing": sharp_preprocessing}, indent=2),
        encoding="utf-8",
    )


def _configure_tesseract_cmd() -> None:
    """Configure Tesseract path for Windows-friendly local setups.

    Priority:
    1) `TESSERACT_CMD` environment variable
    2) executable discoverable on PATH
    3) common Windows install locations under Program Files
    """
    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if env_cmd and Path(env_cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        return

    on_path = shutil.which("tesseract")
    if on_path:
        pytesseract.pytesseract.tesseract_cmd = on_path
        return

    common_windows_paths = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in common_windows_paths:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return


def _preprocess_image_sharp_pil(
    image: Image.Image,
    min_text_height_px: int,
    max_dimension_px: int,
) -> Image.Image:
    """PIL-only preprocessing: upscale, sharpen, contrast. Used when OpenCV is not available."""
    w, h = image.size
    min_dim = min(w, h)
    if min_dim < min_text_height_px:
        scale = min_text_height_px / min_dim
        new_w = min(int(round(w * scale)), max_dimension_px)
        new_h = min(int(round(h * scale)), max_dimension_px)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    sharp = gray.filter(ImageFilter.SHARPEN)
    return sharp


def _preprocess_image_sharp_cv2(
    image: Image.Image,
    min_text_height_px: int,
    max_dimension_px: int,
) -> Image.Image:
    """OpenCV sharp pipeline: upscale, denoise, sharpen, adaptive binarization for unclear photos."""
    if not _CV2_AVAILABLE:
        return _preprocess_image_sharp_pil(image, min_text_height_px, max_dimension_px)
    arr = np.array(image)
    if arr.ndim == 2:
        gray = arr
    else:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    min_dim = min(w, h)
    if min_dim < min_text_height_px:
        scale = min_text_height_px / min_dim
        new_w = min(int(round(w * scale)), max_dimension_px)
        new_h = min(int(round(h * scale)), max_dimension_px)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    # Denoise while preserving edges (helps blurry/noisy photos)
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    # Unsharp mask: enhance edges so text is crisper
    gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.0)
    sharp = cv2.addWeighted(denoised, 1.5, gaussian, -0.5, 0)
    # Binarize: adaptive threshold handles uneven lighting and blur better than global Otsu
    thresh_adaptive = cv2.adaptiveThreshold(
        sharp, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 2
    )
    return Image.fromarray(thresh_adaptive)


def _preprocess_image_simple(image: Image.Image) -> Image.Image:
    """Minimal preprocessing: grayscale + autocontrast only (faster, less accurate on blur)."""
    return ImageOps.autocontrast(ImageOps.grayscale(image))


def _preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Apply preprocessing from config: sharp pipeline (with min/max px) or simple."""
    cfg = _get_ocr_config()
    if not cfg.get("sharp_preprocessing", True):
        return _preprocess_image_simple(image)
    min_px = int(cfg.get("min_text_height_px", _DEFAULT_OCR_CONFIG["min_text_height_px"]))
    max_px = int(cfg.get("max_dimension_px", _DEFAULT_OCR_CONFIG["max_dimension_px"]))
    if _CV2_AVAILABLE:
        return _preprocess_image_sharp_cv2(image, min_px, max_px)
    return _preprocess_image_sharp_pil(image, min_px, max_px)


def _run_ocr_robust(processed: Image.Image, use_multi_psm: bool = True) -> str:
    """Run Tesseract; when use_multi_psm, merge results from PSM 6 and 3 for difficult images."""
    config_base = "--oem 3"  # LSTM engine
    if use_multi_psm:
        texts = []
        for psm in (6, 3):
            try:
                t = pytesseract.image_to_string(
                    processed, config=f"{config_base} --psm {psm}"
                ).strip()
                if t:
                    texts.append(t)
            except Exception:
                continue
        if not texts:
            return ""
        return max(texts, key=len)
    return pytesseract.image_to_string(processed, config=f"{config_base} --psm 6").strip()


def _extract_text_from_image(path: Path) -> str:
    """Run preprocessing + OCR on an image file (sharp pipeline when enabled in config)."""
    _configure_tesseract_cmd()
    image = Image.open(path).convert("RGB")
    processed = _preprocess_image_for_ocr(image)
    cfg = _get_ocr_config()
    use_multi_psm = cfg.get("sharp_preprocessing", True)
    return _run_ocr_robust(processed, use_multi_psm=use_multi_psm)


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
        _configure_tesseract_cmd()
        cfg = _get_ocr_config()
        scale = int(cfg.get("pdf_scale", _DEFAULT_OCR_CONFIG["pdf_scale"]))
        scale = max(2, min(scale, 5))  # clamp 2–5
        with fitz.open(str(path)) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                processed = _preprocess_image_for_ocr(image)
                use_multi_psm = cfg.get("sharp_preprocessing", True)
                ocr_chunks.append(_run_ocr_robust(processed, use_multi_psm=use_multi_psm))
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
