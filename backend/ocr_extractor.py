"""
OCR Extractor for PrivGuard AI
Safely extracts text from images using Tesseract OCR.

Security considerations:
- Only processes local files
- No external network calls
- Handles errors gracefully
"""

import os
import pytesseract
from PIL import Image, ImageOps, ImageFilter

# Updated Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRExtractor:
    """
    Secure OCR extractor with preprocessing.
    Improves accuracy and prevents decoding errors.
    """

    def preprocess(self, image):
        """
        Convert to grayscale and sharpen for better OCR.
        """
        image = ImageOps.grayscale(image)
        image = image.filter(ImageFilter.SHARPEN)
        return image

    def extract_text(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            image = Image.open(filepath)

            # Preprocess image
            image = self.preprocess(image)

            text = pytesseract.image_to_string(image)

            return text

        except Exception as e:
            raise RuntimeError(f"OCR extraction failed: {str(e)}")