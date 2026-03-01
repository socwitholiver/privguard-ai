import os
try:
    import PyPDF2
except Exception:  # pragma: no cover - optional dependency path
    PyPDF2 = None

try:
    import docx
except Exception:  # pragma: no cover - optional dependency path
    docx = None
from backend.logger import get_logger

logger = get_logger()


class FileLoader:
    def __init__(self):
        logger.info("FileLoader initialized.")

    def load_file(self, filepath):
        """
        Detect file type and extract text.
        Supports PDF, DOCX, and TXT.
        """

        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")

        if os.path.getsize(filepath) == 0:
            logger.warning(f"Empty file detected: {filepath}")
            raise ValueError("File is empty.")

        extension = filepath.lower().split(".")[-1]

        try:
            if extension == "pdf":
                logger.info(f"Extracting PDF: {filepath}")
                text = self._extract_from_pdf(filepath)

            elif extension == "docx":
                logger.info(f"Extracting DOCX: {filepath}")
                text = self._extract_from_docx(filepath)

            elif extension == "txt":
                logger.info(f"Extracting TXT: {filepath}")
                text = self._extract_from_txt(filepath)

            else:
                logger.warning(f"Unsupported file type: {extension}")
                raise ValueError("Unsupported file type. Only PDF, DOCX, and TXT allowed.")

            if not text:
                logger.warning(f"No readable text extracted from: {filepath}")
                raise ValueError("No readable text found in file.")

            return text

        except Exception as e:
            logger.error(f"Extraction failed for {filepath}: {str(e)}")
            raise

    def _extract_from_pdf(self, filepath):
        if PyPDF2 is None:
            raise ModuleNotFoundError("PyPDF2 is required for PDF extraction.")
        text = ""
        try:
            with open(filepath, "rb") as file:
                pdf = PyPDF2.PdfReader(file)
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            raise Exception(f"PDF extraction error: {str(e)}")

        return text.strip()

    def _extract_from_docx(self, filepath):
        if docx is None:
            raise ModuleNotFoundError("python-docx is required for DOCX extraction.")
        try:
            doc = docx.Document(filepath)
            text = "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raise Exception(f"DOCX extraction error: {str(e)}")

        return text.strip()

    def _extract_from_txt(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        except Exception as e:
            raise Exception(f"TXT extraction error: {str(e)}")

        return text.strip()
