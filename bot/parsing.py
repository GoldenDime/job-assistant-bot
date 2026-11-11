import io

from docx import Document
from pypdf import PdfReader

MAX_CHARS = 20_000


class ParseError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Возвращает (текст, формат)."""
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(data))
            text, fmt = "\n".join(p.extract_text() or "" for p in reader.pages), "pdf"
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(data))
            text, fmt = "\n".join(p.text for p in doc.paragraphs), "docx"
        elif name.endswith(".txt"):
            text, fmt = data.decode("utf-8", errors="replace"), "txt"
        else:
            raise ParseError("unsupported_format")
    except ParseError:
        raise
    except Exception as exc:  # битый файл
        raise ParseError("corrupted_file") from exc
    text = text.strip()
    if len(text) < 200:
        raise ParseError("too_short")  # скан или пустой файл
    return text[:MAX_CHARS], fmt
