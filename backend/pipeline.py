from backend.file_loader import FileLoader
from backend.detector import SensitiveDataDetector
from backend.risk_scoring import RiskScorer
from backend.logger import get_logger

logger = get_logger()


class PrivGuardPipeline:
    """
    End-to-end document processing pipeline.
    """

    def __init__(self):
        self.loader = FileLoader()
        self.detector = SensitiveDataDetector()
        self.scorer = RiskScorer()

        logger.info("PrivGuard Pipeline initialized.")

    def run(self, filepath):
        """
        Process document fully.
        """

        logger.info(f"Starting pipeline for {filepath}")

        # Step 1 — Extract text
        text = self.loader.load_file(filepath)

        # Step 2 — Detect sensitive data
        findings = self.detector.detect(text)

        # Step 3 — Score risk
        risk = self.scorer.score(findings)

        result = {
            "file": filepath,
            "findings": findings,
            "risk": risk
        }

        logger.info("Pipeline completed successfully.")

        return result
