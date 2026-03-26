"""
Fetches daily OHLCV data for all active stocks via NSE historical API.
Stores into ohlcv_daily table (TimescaleDB hypertable).
"""
import time
from datetime import date, timedelta
from typing import List

import httpx
import pandas as pd
from loguru import logger
from sqlalchemy import text

from app.celery_app import celery_app
from app.database import db_session
from app.models.stock import Stock
from app.models.ohlcv import OHLCVDaily

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/",
}


def _get_active_symbols() -> List[str]:
    with db_session() as session:
        rows = session.query(Stock.symbol).filter(Stock.is_active == True).all()
        return [r.symbol for r in rows]


def _fetch_nse_ohlcv(symbol: str, days: int = 5) -> list:
    to_date = date.today().strftime("%d-%m-%Y")
    from_date = (date.today() - timedelta(days=days)).strftime("%d-%m-%Y")
    url = (
        f"https://www.nseindia.com/api/historical/cm/equity"
        f'?symbol={symbol}&series=["EQ"]&from={from_date}&to={to_date}&csv=false'
    )
    with httpx.Client(headers=NSE_HEADERS, timeout=30, follow_redirects=True) as client:
        client.get("https://www.nseindia.com")
        time.sleep(1.5)
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json().get("data", [])


@celery_app.task(name="app.workers.ohlcv_fetcher.fetch_stock_ohlcv")
def fetch_stock_ohlcv(symbol: str, days: int = 5):
    try:
        rows = _fetch_nse_ohlcv(symbol, days=days)
        if not rows:
            logger.warning(f"No OHLCV data for {symbol}")
            return

        with db_session() as session:
            for row in rows:
                dt = pd.to_datetime(row["CH_TIMESTAMP"], utc=True)
                session.execute(
                    text("DELETE FROM ohlcv_daily WHERE time = :t AND symbol = :s"),
                    {"t": dt, "s": symbol},
                )
                session.add(OHLCVDaily(
                    time=dt,
                    symbol=symbol,
                    open=float(row.get("CH_OPENING_PRICE") or 0) or None,
                    high=float(row.get("CH_TRADE_HIGH_PRICE") or 0) or None,
                    low=float(row.get("CH_TRADE_LOW_PRICE") or 0) or None,
                    close=float(row.get("CH_CLOSING_PRICE") or 0) or None,
                    volume=int(row.get("CH_TOT_TRADED_QTY") or 0) or None,
                    turnover_cr=round(float(row.get("CH_TOT_TRADED_VAL") or 0) / 1e7, 2) or None,
                ))
        logger.info(f"OHLCV updated for {symbol}: {len(rows)} rows")
    except Exception as e:
        logger.error(f"OHLCV fetch failed for {symbol}: {e}")
        raise


@celery_app.task(name="app.workers.ohlcv_fetcher.fetch_all_daily_ohlcv")
def fetch_all_daily_ohlcv():
    symbols = _get_active_symbols()
    logger.info(f"Dispatching OHLCV fetch for {len(symbols)} stocks")
    for symbol in symbols:
        fetch_stock_ohlcv.apply_async(args=[symbol, 3], queue="default")
    return f"Dispatched {len(symbols)} OHLCV tasks"
