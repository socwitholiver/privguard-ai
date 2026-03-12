from pathlib import Path

import fitz

from extraction import read_document_text


def test_read_document_text_handles_malformed_pdf_with_fallbacks(tmp_path):
    pdf_path = tmp_path / "sensitive_demo.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "Employee Personal & Tax Summary",
                "National ID Number: 27894561",
                "KRA PIN: P123456789A",
            ]
        ),
    )
    doc.save(pdf_path)
    doc.close()

    text = read_document_text(pdf_path)

    assert "Employee Personal & Tax Summary" in text
    assert "National ID Number: 27894561" in text
    assert "KRA PIN: P123456789A" in text
