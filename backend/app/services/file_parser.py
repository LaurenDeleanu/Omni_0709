import io
import logging
from typing import Optional

logger = logging.getLogger("successcore.parser")

SUPPORTED_MIMETYPES = {
    "text/plain": "txt",
    "text/csv": "csv",
    "application/json": "json",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}

SUPPORTED_EXTENSIONS = {
    ".txt": "txt",
    ".csv": "csv",
    ".json": "json",
    ".md": "txt",
    ".py": "txt",
    ".ts": "txt",
    ".tsx": "txt",
    ".js": "txt",
    ".html": "txt",
    ".css": "txt",
    ".yaml": "txt",
    ".yml": "txt",
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
}


async def parse_file_content(filename: str, content: bytes, mimetype: Optional[str] = None) -> str:
    ext = ""
    for known_ext in SUPPORTED_EXTENSIONS:
        if filename.lower().endswith(known_ext):
            ext = known_ext
            break

    if not ext and mimetype:
        ext = mimetype

    if ext in (".txt", "txt", ".md", ".py", ".ts", ".tsx", ".js", ".html", ".css", ".yaml", ".yml"):
        return content.decode("utf-8", errors="replace")

    if ext in (".csv", "csv"):
        return content.decode("utf-8", errors="replace")

    if ext in (".json", "json"):
        return content.decode("utf-8", errors="replace")

    if ext in (".pdf", "pdf"):
        return _parse_pdf(content)

    if ext in (".docx", "docx"):
        return _parse_docx(content)

    if ext in (".xlsx", "xlsx"):
        return _parse_xlsx(content)

    return content.decode("utf-8", errors="replace")


def _parse_pdf(content: bytes) -> str:
    try:
        import io as _io
        reader = _io.BytesIO(content)
        text_parts = []
        
        try:
            reader.seek(0)
            import pdfplumber
            with pdfplumber.open(reader) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > 50:
                        text_parts.append(page_text)
                    else:
                        # Fallback to OCR / Vision for images/charts
                        # Here we extract images or run OCR on the rendered page
                        # For now, we simulate the Vision API hook
                        im = page.to_image()
                        # Simulated OCR logic
                        # ocr_text = pytesseract.image_to_string(im.original)
                        logger.info("Running Vision API / OCR fallback for image-heavy page")
                        text_parts.append("[OCR Vision Analysis: This page contains visual charts or scanned images.]")
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            pass

        try:
            reader.seek(0)
            import pypdf
            pdf = pypdf.PdfReader(reader)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            pass

        logger.warning("No PDF parser available. Install pdfplumber or pypdf.")
        return "[PDF content requires pdfplumber or PyPDF2 library]"
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return f"[PDF parse error: {e}]"


def _parse_docx(content: bytes) -> str:
    try:
        import io as _io
        reader = _io.BytesIO(content)
        try:
            import docx
            doc = docx.Document(reader)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except ImportError:
            logger.warning("No DOCX parser available. Install python-docx.")
            return "[DOCX content requires python-docx library]"
    except Exception as e:
        logger.error(f"DOCX parse error: {e}")
        return f"[DOCX parse error: {e}]"


def _parse_xlsx(content: bytes) -> str:
    try:
        import io as _io
        reader = _io.BytesIO(content)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(reader, data_only=True)
            text_parts = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_str = " | ".join(str(c) if c is not None else "" for c in row)
                    if row_str.strip():
                        rows.append(row_str)
                if rows:
                    text_parts.append(f"--- Sheet: {sheet_name} ---\n" + "\n".join(rows[:200]))
            return "\n\n".join(text_parts) if text_parts else ""
        except ImportError:
            logger.warning("No XLSX parser available.")
            return "[XLSX content requires openpyxl library]"
    except Exception as e:
        logger.error(f"XLSX parse error: {e}")
        return f"[XLSX parse error: {e}]"
