import os
import pandas as pd
import pdfplumber
import fitz  # PyMuPDF
import docx
from ocr_engine import extract_text_from_image

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_pdf(file_path)
    elif ext == ".docx":
        return extract_docx(file_path)
    elif ext in [".xlsx", ".csv"]:
        return extract_spreadsheet(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_text_from_image(file_path)
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        return ""

def extract_pdf(file_path):
    text = ""

    # First try text layer
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"

    # If empty → fallback to OCR
    if not text.strip():
        doc = fitz.open(file_path)
        for page in doc:
            pix = page.get_pixmap()
            img_path = "temp_page.png"
            pix.save(img_path)
            text += extract_text_from_image(img_path)

    return text

def extract_docx(file_path):
    document = docx.Document(file_path)
    return "\n".join([para.text for para in document.paragraphs])

def extract_spreadsheet(file_path):
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    return df.to_string()