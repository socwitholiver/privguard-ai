from backend.ocr_extractor import OCRExtractor
from backend.detector import IntelligentDataDetector

class PrivGuardPipeline:
    """
    End-to-end document processing pipeline.
    """

    def __init__(self):
        self.ocr = OCRExtractor()
        self.detector = IntelligentDataDetector()

    def run(self, filepath):
        """
        Full processing pipeline for a document/image.
        """
        # Step 1: OCR
        text = self.ocr.extract_text(filepath)

        # Step 2: Detect fields
        findings, doc_type = self.detector.detect_fields(text)

        # Step 3: Classify & generate recommendations
        result = self.detector.classify_document(findings, doc_type)
        result["file"] = filepath
        return result

# CLI support
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m backend.pipeline <file_path>")
        sys.exit(1)

    filepath = sys.argv[1]
    pipeline = PrivGuardPipeline()
    result = pipeline.run(filepath)
    print(json.dumps(result, indent=4))