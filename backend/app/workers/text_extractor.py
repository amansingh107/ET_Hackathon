"""
Downloads and extracts text from NSE filing attachments (PDF/HTML).
Populates content_text on corporate_filings rows so the keyword scorer works.
"""
import io
import time
import random

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.celery_app import celery_app
from app.database import db_session
from app.models.filing import CorporateFiling

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/",
}

MAX_TEXT_LEN = 50_000  # characters — enough for keyword matching


def _extract_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            parts = []
            for page in pdf.pages[:10]:  # first 10 pages is enough
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n".join(parts)[:MAX_TEXT_LEN]
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")
        return ""


def _extract_html_text(content: bytes) -> str:
    try:
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:MAX_TEXT_LEN]
    except Exception as e:
        logger.warning(f"HTML extraction failed: {e}")
        return ""


def _download_and_extract(url: str) -> str:
    """Download a filing URL and return extracted text."""
    try:
        session = requests.Session()
        session.headers.update(NSE_HEADERS)
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return _extract_pdf_text(resp.content)
        else:
            # Treat as HTML / XML
            return _extract_html_text(resp.content)
    except Exception as e:
        logger.warning(f"Download failed for {url}: {e}")
        return ""


@celery_app.task(name="app.workers.text_extractor.extract_filing_texts")
def extract_filing_texts(batch_size: int = 20):
    """Process unextracted filings in batches."""
    with db_session() as session:
        filings = (
            session.query(CorporateFiling)
            .filter(
                CorporateFiling.content_url.isnot(None),
                CorporateFiling.content_text.is_(None),
                CorporateFiling.is_processed == False,
            )
            .order_by(CorporateFiling.filing_date.desc())
            .limit(batch_size)
            .all()
        )

    if not filings:
        logger.info("No unextracted filings found")
        return "No filings to process"

    processed = 0
    for filing in filings:
        text = _download_and_extract(filing.content_url)
        with db_session() as session:
            obj = session.query(CorporateFiling).get(filing.id)
            if obj:
                obj.content_text = text or ""
                obj.is_processed = True
        processed += 1
        time.sleep(random.uniform(0.5, 1.5))  # polite crawl rate

    logger.info(f"Text extractor: processed {processed} filings")
    return f"Processed {processed} filings"
