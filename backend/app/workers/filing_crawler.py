"""
Crawls NSE for corporate announcements every 15 minutes.
Stores raw filings in corporate_filings table.
"""
import asyncio
import random
from datetime import datetime, timezone

import httpx
from loguru import logger

from app.celery_app import celery_app
from app.database import db_session
from app.models.filing import CorporateFiling

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    # Do NOT set Accept-Encoding — let httpx handle decompression automatically
    "Referer": "https://www.nseindia.com/",
}

NSE_ANNOUNCEMENTS_URL = (
    "https://www.nseindia.com/api/corporate-announcements?index=equities"
)


async def _fetch_nse_announcements() -> list:
    """Hit NSE homepage first to warm cookies, then fetch announcements."""
    async with httpx.AsyncClient(headers=NSE_HEADERS, timeout=30, follow_redirects=True) as client:
        try:
            await client.get("https://www.nseindia.com")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            resp = await client.get(NSE_ANNOUNCEMENTS_URL)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"NSE announcements fetch failed: {e}")
            return []


def _parse_filing_date(raw: str) -> datetime:
    """Parse NSE date strings like '26-Mar-2026 10:30:00' into UTC datetime."""
    formats = ["%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S"]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
    return datetime.now(timezone.utc)


@celery_app.task(name="app.workers.filing_crawler.crawl_nse_filings")
def crawl_nse_filings():
    """Fetch and store new NSE corporate announcements."""
    data = asyncio.run(_fetch_nse_announcements())
    if not data:
        return "No data received from NSE"

    new_count = 0
    with db_session() as session:
        for item in data:
            content_url = item.get("attchmntFile") or item.get("filingUrl")

            # Deduplicate by (source, symbol, subject, filing_date)
            symbol = item.get("symbol", "")
            subject = item.get("subject") or item.get("desc") or ""
            raw_date = item.get("an_dt") or item.get("exchdisstime") or ""
            filing_date = _parse_filing_date(raw_date) if raw_date else datetime.now(timezone.utc)

            exists = session.query(CorporateFiling).filter(
                CorporateFiling.source == "NSE",
                CorporateFiling.symbol == symbol,
                CorporateFiling.subject == subject,
            ).first()

            if exists:
                continue

            filing = CorporateFiling(
                source="NSE",
                symbol=symbol,
                filing_type=item.get("desc") or item.get("filingType") or "General",
                filing_date=filing_date,
                subject=subject,
                content_url=content_url,
                raw_json=item,
                is_processed=False,
            )
            session.add(filing)
            new_count += 1

    logger.info(f"NSE crawler: stored {new_count} new filings")
    return f"Stored {new_count} new NSE filings"
