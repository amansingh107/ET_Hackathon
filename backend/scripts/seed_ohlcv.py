"""
Seeds historical OHLCV data using NSE Bhavcopy (daily CSV with all stocks).
One request per trading day → gets all 2000+ stocks at once.

Run: python3 scripts/seed_ohlcv.py [--days 30] [--symbol RELIANCE]
"""
import sys
import os
import argparse
import time
import io
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pandas as pd
from loguru import logger
from sqlalchemy import text

from app.database import db_session
from app.models.ohlcv import OHLCVDaily

# NSE Bhavcopy full data — one CSV per trading day, all stocks
# Format: sec_bhavdata_full_DDMMYYYY.csv
BHAVCOPY_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.nseindia.com/",
}


def trading_days(days: int) -> list[date]:
    """Return last N calendar days that are Mon-Fri (approximate trading days)."""
    result = []
    d = date.today() - timedelta(days=1)  # yesterday (today's bhavcopy not out yet)
    while len(result) < days:
        if d.weekday() < 5:  # Mon=0 … Fri=4
            result.append(d)
        d -= timedelta(days=1)
    return result


def fetch_bhavcopy(client: httpx.Client, day: date) -> pd.DataFrame | None:
    date_str = day.strftime("%d%m%Y")
    url = BHAVCOPY_URL.format(date=date_str)
    try:
        resp = client.get(url, timeout=30)
        if resp.status_code == 404:
            logger.debug(f"No bhavcopy for {day} (holiday/weekend)")
            return None
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logger.error(f"Bhavcopy fetch failed for {day}: {e}")
        return None


def store_bhavcopy(df: pd.DataFrame, day: date, filter_symbol: str = None) -> int:
    # Keep only EQ series
    df = df[df["SERIES"].str.strip() == "EQ"].copy()
    if filter_symbol:
        df = df[df["SYMBOL"].str.strip() == filter_symbol]
    if df.empty:
        return 0

    ts = pd.Timestamp(day, tz="UTC")
    count = 0
    with db_session() as session:
        for _, row in df.iterrows():
            symbol = str(row["SYMBOL"]).strip()
            try:
                session.execute(
                    text("DELETE FROM ohlcv_daily WHERE time = :t AND symbol = :s"),
                    {"t": ts, "s": symbol},
                )
                session.add(OHLCVDaily(
                    time=ts,
                    symbol=symbol,
                    open=float(row["OPEN_PRICE"]) if pd.notna(row["OPEN_PRICE"]) else None,
                    high=float(row["HIGH_PRICE"]) if pd.notna(row["HIGH_PRICE"]) else None,
                    low=float(row["LOW_PRICE"]) if pd.notna(row["LOW_PRICE"]) else None,
                    close=float(row["CLOSE_PRICE"]) if pd.notna(row["CLOSE_PRICE"]) else None,
                    volume=int(row["TTL_TRD_QNTY"]) if pd.notna(row["TTL_TRD_QNTY"]) else None,
                    turnover_cr=round(float(row["TURNOVER_LACS"]) / 100, 2) if pd.notna(row.get("TURNOVER_LACS", None)) else None,
                ))
                count += 1
            except Exception as e:
                logger.debug(f"Skip {symbol} on {day}: {e}")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=10, help="Number of trading days")
    parser.add_argument("--symbol", type=str, default=None, help="Filter to one symbol")
    args = parser.parse_args()

    days = trading_days(args.days)
    logger.info(f"Fetching bhavcopy for {len(days)} trading days: {days[-1]} → {days[0]}")

    client = httpx.Client(headers=HEADERS, follow_redirects=True)
    total = 0

    for i, day in enumerate(days, 1):
        df = fetch_bhavcopy(client, day)
        if df is not None:
            n = store_bhavcopy(df, day, filter_symbol=args.symbol)
            total += n
            logger.info(f"[{i}/{len(days)}] {day}: {n} rows stored")
        else:
            logger.info(f"[{i}/{len(days)}] {day}: skipped")
        time.sleep(0.5)

    client.close()
    logger.info(f"Done. Total rows: {total}")


if __name__ == "__main__":
    main()
