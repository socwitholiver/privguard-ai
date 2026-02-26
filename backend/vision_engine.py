"""
Vision Intelligence Engine

Provides lightweight document understanding:
- Detect document type
- Improve OCR reasoning
- Assist risk decisions

Offline friendly — no cloud required.
"""

import cv2
import numpy as np


class VisionEngine:
    """
    Simple computer vision heuristics for document classification.
    """

    def classify_document(self, image_path):
        """
        Determine document type using visual heuristics.
        """

        try:
            image = cv2.imread(image_path)

            if image is None:
                return "Unknown"

            height, width, _ = image.shape
            aspect_ratio = width / height

            # ATM cards usually have ~1.58 ratio
            if 1.5 < aspect_ratio < 1.7:
                return "Card (ATM/ID)"

            # Tall images — likely documents
            if height > width:
                return "Document"

            return "Generic Image"

        except Exception:
            return "Unknown"