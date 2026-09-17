from io import BytesIO

from pypdf import PdfReader


MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 30


class PdfExtractionError(ValueError):
    pass


def extract_pdf_text(content: bytes) -> str:
    if not content:
        raise PdfExtractionError("The uploaded PDF is empty.")
    if len(content) > MAX_PDF_BYTES:
        raise PdfExtractionError("PDF uploads are limited to 8 MB.")
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as error:
        raise PdfExtractionError("The uploaded file is not a readable PDF.") from error
    if len(reader.pages) > MAX_PDF_PAGES:
        raise PdfExtractionError("PDF uploads are limited to 30 pages.")
    try:
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as error:
        raise PdfExtractionError("Text could not be extracted from this PDF.") from error
    if not text:
        raise PdfExtractionError("This PDF has no extractable text; scanned-PDF OCR is not available yet.")
    return text
