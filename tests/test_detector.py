import sys
import os

# Add project root to Python path so 'backend' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.detector import SensitiveDataDetector

detector = SensitiveDataDetector()

def test_detection():
    sample = """
    Email: test@example.com
    Phone: 0712345678
    ID: 12345678
    Card: 1234567890123456
    """

    results = detector.detect(sample)

    assert len(results["email"]) > 0
    assert len(results["phone"]) > 0
    assert len(results["id_number"]) > 0
    assert len(results["financial"]) > 0
