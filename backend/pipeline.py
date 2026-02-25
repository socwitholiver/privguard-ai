import os
import mimetypes

from backend.file_loader import FileLoader
from backend.detector import SensitiveDataDetector
from backend.risk_scoring import RiskScorer
from backend.ai_classifier import AIClassifier
from backend.logger import get_logger
from backend.ocr_extractor import OCRExtractor

logger = get_logger()


class PrivGuardPipeline:
    """
    End-to-end processing pipeline supporting:
    - Text files
    - Documents
    - Images (OCR)
    """

    def __init__(self):
        self.loader = FileLoader()
        self.detector = SensitiveDataDetector()
        self.scorer = RiskScorer()
        self.classifier = AIClassifier()
        self.ocr = OCRExtractor()

        logger.info("PrivGuard Pipeline initialized.")

    def _is_image(self, filepath):
        mime, _ = mimetypes.guess_type(filepath)
        return mime and mime.startswith("image")

    def run(self, filepath):
        logger.info(f"Starting pipeline for {filepath}")

        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        # Decide processing path
        if self._is_image(filepath):
            logger.info("Image detected → running OCR")
            text = self.ocr.extract_text(filepath)
        else:
            logger.info("Document detected → loading file")
            text = self.loader.load_file(filepath)

        findings = self.detector.detect(text)
        risk = self.scorer.score(findings)
        classification = self.classifier.classify(findings)

        result = {
            "file": os.path.abspath(filepath),
            "findings": findings,
            "risk": risk,
            "classification": classification
        }

        logger.info("Pipeline completed successfully.")
        return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m backend.pipeline <file>")
        sys.exit(1)

    pipeline = PrivGuardPipeline()
    result = pipeline.run(sys.argv[1])

    import json
    print(json.dumps(result, indent=4))