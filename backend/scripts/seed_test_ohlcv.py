"""
Seeds synthetic OHLCV data for testing the pattern engine.
Creates a realistic trending + reversal price series for RELIANCE and INFY.
Run: python3 scripts/seed_test_ohlcv.py
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import db_session
from app.models.ohlcv import OHLCVDaily
from loguru import logger

random.seed(42)
np.random.seed(42)


def gen_ohlcv(start_price: float, days: int = 400, trend: float = 0.0003) -> pd.DataFrame:
    """Generate synthetic OHLCV with realistic noise and trend."""
    dates = []
    d = datetime.now(timezone.utc) - timedelta(days=days)
    while len(dates) < days:
        if d.weekday() < 5:  # Mon-Fri
            dates.append(d)
        d += timedelta(days=1)

    closes = [start_price]
    for _ in range(len(dates) - 1):
        change = closes[-1] * (trend + np.random.normal(0, 0.015))
        closes.append(max(closes[-1] + change, 10))

    rows = []
    for i, dt in enumerate(dates):
        c = closes[i]
        o = c * (1 + np.random.uniform(-0.01, 0.01))
        h = max(o, c) * (1 + abs(np.random.normal(0, 0.008)))
        lo = min(o, c) * (1 - abs(np.random.normal(0, 0.008)))
        vol = int(np.random.lognormal(15, 0.5))
        rows.append({"time": dt, "open": round(o,2), "high": round(h,2),
                     "low": round(lo,2), "close": round(c,2), "volume": vol})
    return pd.DataFrame(rows)


def store(symbol: str, df: pd.DataFrame):
    with db_session() as session:
        session.execute(text("DELETE FROM ohlcv_daily WHERE symbol = :s"), {"s": symbol})
        for _, row in df.iterrows():
            session.add(OHLCVDaily(
                time=row["time"], symbol=symbol,
                open=row["open"], high=row["high"],
                low=row["low"], close=row["close"], volume=row["volume"],
            ))
    logger.info(f"Stored {len(df)} rows for {symbol}")


if __name__ == "__main__":
    store("RELIANCE", gen_ohlcv(2400, days=400, trend=0.0004))
    store("INFY",     gen_ohlcv(1500, days=400, trend=0.0002))
    store("HDFCBANK", gen_ohlcv(1700, days=400, trend=0.0001))
    store("TCS",      gen_ohlcv(3800, days=400, trend=0.0003))
    store("WIPRO",    gen_ohlcv(480,  days=400, trend=-0.0001))
    logger.info("Done. Now run: curl -X POST http://localhost:8000/api/v1/ingest/patterns/scan/RELIANCE")
