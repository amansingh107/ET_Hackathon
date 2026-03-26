"""
Seeds the stocks table with the Nifty 500 universe from NSE.
Run: python scripts/seed_universe.py
"""
import sys
import os
import io
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from loguru import logger
from app.database import db_session
from app.models.stock import Stock

NSE_NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Sector mapping from NSE industry labels → cleaner names
SECTOR_MAP = {
    "Financial Services": "Financials",
    "Information Technology": "IT",
    "Consumer Goods": "FMCG",
    "Automobile": "Auto",
    "Pharmaceuticals": "Pharma",
    "Oil & Gas": "Energy",
    "Metals": "Metals",
    "Construction": "Infra",
    "Cement & Cement Products": "Cement",
    "Telecom": "Telecom",
    "Media & Entertainment": "Media",
    "Textiles": "Textiles",
    "Power": "Power",
    "Services": "Services",
    "Chemicals": "Chemicals",
    "Consumer Services": "Consumer Services",
    "Capital Goods": "Capital Goods",
    "Healthcare": "Pharma",
    "Realty": "Real Estate",
    "FMCG": "FMCG",
    "Diversified": "Diversified",
}


def fetch_nifty500_csv() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.nseindia.com/",
    }
    resp = httpx.get(NSE_NIFTY500_URL, headers=headers, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def seed(rows: list[dict]) -> int:
    seeded = 0
    with db_session() as session:
        for row in rows:
            symbol = row.get("Symbol", "").strip()
            if not symbol:
                continue

            exists = session.query(Stock).filter_by(symbol=symbol).first()
            if exists:
                continue

            industry_raw = row.get("Industry", "").strip()
            sector = SECTOR_MAP.get(industry_raw, industry_raw or "Other")

            session.add(Stock(
                symbol=symbol,
                company_name=row.get("Company Name", "").strip(),
                isin=row.get("ISIN Code", "").strip() or None,
                series=row.get("Series", "EQ").strip(),
                sector=sector,
                industry=industry_raw or None,
                is_active=True,
            ))
            seeded += 1
    return seeded


if __name__ == "__main__":
    logger.info("Fetching Nifty 500 list from NSE...")
    try:
        rows = fetch_nifty500_csv()
        logger.info(f"Downloaded {len(rows)} rows")
        n = seed(rows)
        logger.info(f"Seeded {n} new stocks into the stocks table")
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        sys.exit(1)
