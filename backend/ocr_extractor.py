from pathlib import Path

from backend.file_loader import FileLoader
from backend.logger import get_logger

logger = get_logger()


class OCRExtractor:
    """
    Backward-compatible OCR/text extraction facade.

    Older pipeline code expects `OCRExtractor.extract_text(filepath)`.
    This shim keeps that contract while delegating plain document loading
    to `FileLoader` and using optional image OCR only when available.
    """

    def __init__(self):
        self.loader = FileLoader()

    def extract_text(self, filepath):
        ext = Path(filepath).suffix.lower()
        if ext in {".png", ".jpg", ".jpeg"}:
            return self._extract_image_text(filepath)
        return self.loader.load_file(filepath)

    def _extract_image_text(self, filepath):
        try:
            from backend.ocr_engine import extract_text_from_image
        except Exception as exc:
            logger.warning(f"OCR engine unavailable for image extraction: {exc}")
            return ""
        return extract_text_from_image(filepath)
