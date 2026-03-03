"""Generate demo_docs assets: PDF with sensitive info, Kenyan ID and driving license mock JPGs.

Run from project root: python demo_docs/generate_demo_assets.py

All data is synthetic. Use only for testing PRIVGUARD AI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = Path(__file__).resolve().parent


def _pdf_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\))")

def make_pdf():
    """Create a PDF with synthetic sensitive content for scan demo."""
    text_plain = """
CONFIDENTIAL – SAMPLE DOCUMENT (Synthetic data only)

Employee Personal & Tax Summary
---------------------------------
Full Name: James Otieno Okello
National ID Number: 27894561
KRA PIN: P123456789A
Date of Birth: 15-03-1985

Contact Details:
Mobile: +254722334455
Alternative: 0733112233
Email: j.okello@example.co.ke

Next of Kin: Mary Wanjiku Okello
Kin Phone: 0712987654
Kin Email: m.wanjiku@example.org
Kin ID: 31234567

Bank Details (for payroll):
Account Name: James O Okello
KRA PIN (confirm): P123456789A

This is synthetic demo data for PRIVGUARD AI testing only.
""".strip()

    try:
        import fitz
        out = DEMO_DIR / "sensitive_demo.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, text_plain, fontsize=11, fontname="Helvetica", align=0)
        doc.save(str(out))
        doc.close()
        print(f"Created {out}")
        return True
    except ImportError:
        pass

    # Fallback: write minimal PDF with standard library (no PyMuPDF)
    out = DEMO_DIR / "sensitive_demo.pdf"
    lines = text_plain.split("\n")
    stream_parts = ["BT\n/F1 11 Tf\n50 792 Td\n"]
    for i, line in enumerate(lines):
        if i:
            stream_parts.append("0 -14 Td\n")
        stream_parts.append(f"({_pdf_escape(line)}) Tj\n")
    stream_parts.append("ET")
    content = "".join(stream_parts).encode("latin-1", errors="replace")
    obj1 = "<< /Type /Catalog /Pages 2 0 R >>\n"
    obj2 = "<< /Type /Pages /Kids [3 0 R] /Count 1 /MediaBox [0 0 595 842] >>\n"
    obj3 = "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>\n"
    obj4_stream = content.decode("latin-1")
    obj4 = f"<< /Length {len(content)} >>\nstream\n{obj4_stream}\nendstream\n"
    body_str = (
        "%PDF-1.4\n"
        "1 0 obj\n" + obj1 + "endobj\n"
        "2 0 obj\n" + obj2 + "endobj\n"
        "3 0 obj\n" + obj3 + "endobj\n"
        "4 0 obj\n" + obj4 + "endobj\n"
    )
    body = body_str.encode("latin-1", errors="replace")
    import re
    obj_starts = [(int(m.group(1)), m.start()) for m in re.finditer(rb"(\d+) 0 obj", body)]
    obj_offset = {num: pos for num, pos in obj_starts if 1 <= num <= 4}
    xref_body = "xref\n0 5\n0000000000 65535 f \n"
    for k in (1, 2, 3, 4):
        xref_body += f"{str(obj_offset.get(k, 0)).zfill(10)} 00000 n \n"
    xref_section = xref_body.encode("latin-1")
    startxref = len(body) + len(xref_section)
    trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n"
    out.write_bytes(body + xref_section + trailer.encode("latin-1"))
    print(f"Created {out} (minimal PDF fallback)")
    return True


def make_id_card_jpg():
    """Create a mock Kenyan national ID card image (synthetic, clearly labelled SAMPLE)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow required. pip install pillow")
        return False

    w, h = 600, 380
    img = Image.new("RGB", (w, h), color=(240, 238, 225))
    draw = ImageDraw.Draw(img)
    def _font(size: int):
        for path in ("arial.ttf", "Arial.ttf", "C:/Windows/Fonts/arial.ttf"):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, TypeError):
                continue
        return ImageFont.load_default()

    font_l, font_m = _font(18), _font(14)
    font_s = _font(12)

    # Border
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(80, 80, 80), width=2)
    # Header
    draw.text((w // 2, 28), "REPUBLIC OF KENYA", fill=(0, 0, 0), anchor="mm", font=font_l)
    draw.text((w // 2, 52), "NATIONAL IDENTITY CARD  (SAMPLE – NOT OFFICIAL)", fill=(120, 0, 0), anchor="mm", font=font_s)
    # Photo placeholder
    draw.rectangle([(40, 85), (160, 220)], outline=(100, 100, 100), fill=(220, 218, 210))
    draw.text((100, 152), "PHOTO", fill=(150, 150, 150), anchor="mm", font=font_s)
    # Fields
    y = 90
    for label, value in [
        ("Name:", "Jane Wambui Demo"),
        ("ID No:", "27894561"),
        ("Date of Birth:", "01-06-1992"),
        ("Gender:", "F"),
        ("Phone:", "+254712345678"),
    ]:
        draw.text((180, y), f"{label}  {value}", fill=(0, 0, 0), font=font_m)
        y += 26
    draw.text((w // 2, h - 24), "DEMO DOCUMENT – SYNTHETIC DATA ONLY", fill=(120, 0, 0), anchor="mm", font=font_s)

    out = DEMO_DIR / "kenyan_id_sample.jpg"
    img.save(str(out), "JPEG", quality=92)
    print(f"Created {out}")
    return True


def make_license_jpg():
    """Create a mock Kenyan driving license image (synthetic, clearly labelled SAMPLE)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    def _font(size: int):
        for path in ("arial.ttf", "Arial.ttf", "C:/Windows/Fonts/arial.ttf"):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, TypeError):
                continue
        return ImageFont.load_default()

    w, h = 600, 380
    img = Image.new("RGB", (w, h), color=(245, 242, 230))
    draw = ImageDraw.Draw(img)
    font_l, font_m = _font(18), _font(14)
    font_s = _font(12)

    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(60, 80, 60), width=2)
    draw.text((w // 2, 28), "REPUBLIC OF KENYA", fill=(0, 0, 0), anchor="mm", font=font_l)
    draw.text((w // 2, 52), "DRIVING LICENSE  (SAMPLE – NOT OFFICIAL)", fill=(0, 80, 40), anchor="mm", font=font_s)
    draw.rectangle([(40, 85), (160, 220)], outline=(80, 100, 80), fill=(230, 235, 225))
    draw.text((100, 152), "PHOTO", fill=(120, 140, 120), anchor="mm", font=font_s)
    y = 90
    for label, value in [
        ("Holder:", "John Kamau Demo"),
        ("License No:", "DL 12345678"),
        ("ID No:", "31234567"),
        ("Class:", "B, B1"),
        ("Valid:", "01-01-2024 to 31-12-2029"),
        ("Mobile:", "0733112233"),
    ]:
        draw.text((180, y), f"{label}  {value}", fill=(0, 0, 0), font=font_m)
        y += 24
    draw.text((w // 2, h - 24), "DEMO DOCUMENT – SYNTHETIC DATA ONLY", fill=(0, 80, 40), anchor="mm", font=font_s)

    out = DEMO_DIR / "kenyan_driving_license_sample.jpg"
    img.save(str(out), "JPEG", quality=92)
    print(f"Created {out}")
    return True


def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    ok &= make_pdf()
    ok &= make_id_card_jpg()
    ok &= make_license_jpg()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
