import pytesseract
from PIL import Image
import os

class OCRExtractor:
    """
    Handles OCR extraction from images.
    """

    def __init__(self):
        # Set Tesseract executable path
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    def extract_text(self, filepath):
        """
        Extract text from an image file.
        Raises RuntimeError on failure.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        try:
            image = Image.open(filepath)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            raise RuntimeError(f"OCR extraction failed: {str(e)}")