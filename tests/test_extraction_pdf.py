from pathlib import Path

from extraction import read_document_text


def test_read_document_text_handles_malformed_pdf_with_fallbacks():
    text = read_document_text(Path("demo_docs/sensitive_demo.pdf"))

    assert "Employee Personal & Tax Summary" in text
    assert "National ID Number: 27894561" in text
    assert "KRA PIN: P123456789A" in text
