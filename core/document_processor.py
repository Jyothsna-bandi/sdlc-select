"""Text extraction for supported requirement document formats."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile
from typing import BinaryIO


@dataclass(frozen=True)
class DocumentContent:
    filename: str
    file_type: str
    text: str
    pages: tuple[str, ...]


class DocumentExtractionError(ValueError):
    """Raised when a supported file cannot provide usable text."""


def extract_document(source: bytes | BinaryIO, filename: str) -> DocumentContent:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise DocumentExtractionError("Unsupported document format. Upload a PDF, DOCX, or TXT file.")
    raw = source if isinstance(source, bytes) else source.read()
    if not raw:
        raise DocumentExtractionError("The uploaded document is empty.")

    if suffix == ".txt":
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentExtractionError(f"Could not decode {filename} as UTF-8 text.") from error
        pages = tuple(part.strip() for part in text.split("\f") if part.strip())
        if not pages and text.strip():
            pages = (text.strip(),)
    elif suffix == ".pdf":
        import pymupdf

        try:
            with pymupdf.open(stream=raw, filetype="pdf") as document:
                pages = tuple(page.get_text("text").strip() for page in document)
            text = "\n\n".join(f"[Page {number}]\n{page}" for number, page in enumerate(pages, 1) if page)
        except (pymupdf.FileDataError, OSError, ValueError) as error:
            raise DocumentExtractionError(f"Could not parse {filename}: {error}") from error
    else:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError

        try:
            document = Document(BytesIO(raw))
            paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
            table_rows = [
                " | ".join(cell.text.strip() for cell in row.cells)
                for table in document.tables
                for row in table.rows
                if any(cell.text.strip() for cell in row.cells)
            ]
            text = "\n".join(paragraphs + table_rows)
            pages = (text,) if text.strip() else ()
        except (PackageNotFoundError, BadZipFile, OSError, ValueError, KeyError) as error:
            raise DocumentExtractionError(f"Could not parse {filename}: {error}") from error

    if not text.strip():
        raise DocumentExtractionError("No readable text was found in the document.")
    return DocumentContent(filename, suffix[1:], text.strip(), pages or (text.strip(),))
