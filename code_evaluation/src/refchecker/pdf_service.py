"""PDF text extraction service."""

from __future__ import annotations
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text(source: io.BytesIO | bytes) -> Optional[str]:
    """Extract text from PDF bytes. Tries pypdf, falls back to pdfplumber."""
    if isinstance(source, bytes):
        source = io.BytesIO(source)

    text = _try_pypdf(source)
    if text:
        return text
    return _try_pdfplumber(source)


def _try_pypdf(buf: io.BytesIO) -> Optional[str]:
    try:
        import pypdf
        buf.seek(0)
        reader = pypdf.PdfReader(buf)
        pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
        return "\n".join(pages) if pages else None
    except Exception as e:
        logger.debug("pypdf extraction failed: %s", e)
        return None


def _try_pdfplumber(buf: io.BytesIO) -> Optional[str]:
    try:
        import pdfplumber
        buf.seek(0)
        with pdfplumber.open(buf) as pdf:
            pages = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
            return "\n".join(pages) if pages else None
    except Exception as e:
        logger.debug("pdfplumber extraction failed: %s", e)
        return None


def download_pdf(url: str, timeout: int = 30) -> Optional[io.BytesIO]:
    """Download a PDF from URL and return as BytesIO."""
    try:
        import requests
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return io.BytesIO(r.content)
    except Exception as e:
        logger.error("PDF download failed for %s: %s", url, e)
        return None
