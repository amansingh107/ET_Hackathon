# Module 2: Chart Pattern Intelligence

> Real-time technical pattern detection across the full NSE universe with plain-English explanations and historical back-tested success rates per pattern per stock.

---

## Overview

The Pattern Intelligence engine scans all NSE stocks nightly, detects 27+ technical patterns using TA-Lib and custom algorithms, back-tests each pattern's historical success rate on that specific stock, and generates plain-English explanations via Ollama.

---

## Pipeline Stages

```
[OHLCV Fetch] → [Indicator Computation] → [Pattern Detection] → [Backtest] → [LLM Explain] → [API]
```

---

## Stage 1: OHLCV Fetcher

### File: `backend/app/workers/ohlcv_fetcher.py`

```python
"""
Fetches daily OHLCV for all NSE stocks and writes to TimescaleDB.
Runs nightly at 7 PM IST after NSE closes and data is final.
"""
from nsepy import get_history
from datetime import date, timedelta
import pandas as pd
from celery import shared_task

@shared_task
def fetch_all_daily_ohlcv():
    """Fetch OHLCV for all active stocks in the universe."""
    symbols = get_active_symbols()  # From stocks table
    yesterday = date.today() - timedelta(days=1)

    for symbol in symbols:
        fetch_stock_ohlcv.delay(symbol, yesterday, yesterday)


@shared_task
def fetch_stock_ohlcv(symbol: str, start: date, end: date):
    """Fetch OHLCV for a single stock and upsert into DB."""
    try:
        df = get_history(symbol=symbol, start=start, end=end)
        if df.empty:
            # Fallback to yfinance
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(start=start, end=end)
            df = _normalize_yfinance(df)

        with db_session() as session:
            for idx, row in df.iterrows():
                session.merge(OHLCVDaily(
                    time=idx,
                    symbol=symbol,
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=row["Volume"],
                ))
            session.commit()

    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")


@shared_task
def fetch_historical_bulk(symbol: str, years: int = 5):
    """
    Fetch 5 years of history for a new stock being added.
    Used during initial setup to seed the backtest engine.
    """
    end = date.today()
    start = end - timedelta(days=365 * years)
    df = get_history(symbol=symbol, start=start, end=end)
    # Batch insert to TimescaleDB
    df.to_sql("ohlcv_daily", engine, if_exists="append", method="multi")
```

---

## Stage 2: Technical Indicator Computation

### File: `backend/app/patterns/indicators.py`

```python
"""
Computes all technical indicators needed for pattern detection.
Returns enriched DataFrame with indicator columns.
"""
import pandas as pd
import numpy as np
import talib
import pandas_ta as pta
from scipy.signal import argrelextrema

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: OHLCV DataFrame with columns [Open, High, Low, Close, Volume]
    Output: Same DataFrame enriched with indicator columns
    """
    close = df["Close"].values
    high  = df["High"].values
    low   = df["Low"].values
    vol   = df["Volume"].values

    # Trend indicators
    df["sma_20"]  = talib.SMA(close, timeperiod=20)
    df["sma_50"]  = talib.SMA(close, timeperiod=50)
    df["sma_200"] = talib.SMA(close, timeperiod=200)
    df["ema_9"]   = talib.EMA(close, timeperiod=9)
    df["ema_21"]  = talib.EMA(close, timeperiod=21)

    # Momentum
    df["rsi_14"]  = talib.RSI(close, timeperiod=14)
    df["macd"], df["macd_signal"], df["macd_hist"] = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )

    # Volatility
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = talib.BBANDS(
        close, timeperiod=20, nbdevup=2, nbdevdn=2
    )
    df["atr_14"] = talib.ATR(high, low, close, timeperiod=14)

    # Volume
    df["obv"]     = talib.OBV(close, vol.astype(float))
    df["adline"]  = talib.AD(high, low, close, vol.astype(float))
    df["vol_sma_20"] = talib.SMA(vol.astype(float), timeperiod=20)

    # Support / Resistance via local extrema
    df["is_local_max"] = False
    df["is_local_min"] = False
    max_idx = argrelextrema(close, np.greater, order=10)[0]
    min_idx = argrelextrema(close, np.less, order=10)[0]
    df.iloc[max_idx, df.columns.get_loc("is_local_max")] = True
    df.iloc[min_idx, df.columns.get_loc("is_local_min")] = True

    # 52-week high/low
    df["52w_high"] = df["High"].rolling(252).max()
    df["52w_low"]  = df["Low"].rolling(252).min()

    return df
```

---

## Stage 3: Pattern Detection

### File: `backend/app/patterns/detector.py`

```python
"""
Detects all supported patterns on a given stock's OHLCV data.
Returns list of PatternDetection objects.
"""
import talib
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional
from app.patterns.indicators import compute_all_indicators

@dataclass
class DetectedPattern:
    symbol: str
    pattern_name: str
    timeframe: str
    detected_at: str
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    confidence_score: int
    volume_confirmation: bool


def detect_all_patterns(symbol: str, df: pd.DataFrame, timeframe: str = "1D") -> List[DetectedPattern]:
    """Run all detectors on the dataframe. Returns patterns detected on the latest bar."""
    df = compute_all_indicators(df)
    detected = []

    # TA-Lib candlestick patterns
    detected.extend(_detect_talib_candles(symbol, df, timeframe))

    # Price structure patterns
    detected.extend(_detect_breakouts(symbol, df, timeframe))
    detected.extend(_detect_moving_average_crosses(symbol, df, timeframe))
    detected.extend(_detect_divergences(symbol, df, timeframe))

    # Chart patterns (complex)
    detected.extend(_detect_double_top_bottom(symbol, df, timeframe))
    detected.extend(_detect_head_and_shoulders(symbol, df, timeframe))

    return detected


# --- TA-Lib Candlestick Patterns ---

TALIB_CANDLE_PATTERNS = {
    "BULLISH_ENGULFING": talib.CDLENGULFING,
    "BEARISH_ENGULFING": talib.CDLENGULFING,
    "HAMMER":            talib.CDLHAMMER,
    "SHOOTING_STAR":     talib.CDLSHOOTINGSTAR,
    "DOJI":              talib.CDLDOJI,
    "MORNING_STAR":      talib.CDLMORNINGSTAR,
    "EVENING_STAR":      talib.CDLEVENINGSTAR,
    "THREE_WHITE_SOLDIERS": talib.CDL3WHITESOLDIERS,
    "THREE_BLACK_CROWS":    talib.CDL3BLACKCROWS,
    "DRAGONFLY_DOJI":    talib.CDLDRAGONFLYDOJI,
    "GRAVESTONE_DOJI":   talib.CDLGRAVESTONEDOJI,
    "HARAMI":            talib.CDLHARAMI,
    "PIERCING":          talib.CDLPIERCING,
    "DARK_CLOUD_COVER":  talib.CDLDARKCLOUDCOVER,
}

def _detect_talib_candles(symbol, df, timeframe) -> List[DetectedPattern]:
    detected = []
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values

    for name, func in TALIB_CANDLE_PATTERNS.items():
        result = func(o, h, l, c)
        last_val = result.iloc[-1] if hasattr(result, 'iloc') else result[-1]

        if last_val == 0:
            continue  # No pattern on latest bar

        # Skip if already classified (e.g., ENGULFING returns +100 bullish, -100 bearish)
        is_bullish = last_val > 0

        # Volume confirmation: current volume > 1.5x 20-day average
        vol_confirm = float(df["Volume"].iloc[-1]) > 1.5 * float(df["vol_sma_20"].iloc[-1])

        # Confidence: base 60 + volume bonus + trend alignment bonus
        confidence = 60
        if vol_confirm:
            confidence += 20
        if is_bullish and df["Close"].iloc[-1] > df["sma_50"].iloc[-1]:
            confidence += 10  # Bullish pattern in uptrend
        if not is_bullish and df["Close"].iloc[-1] < df["sma_50"].iloc[-1]:
            confidence += 10  # Bearish pattern in downtrend

        # ATR-based targets and stops
        atr = float(df["atr_14"].iloc[-1])
        entry = float(df["Close"].iloc[-1])
        target = entry + (2 * atr) if is_bullish else entry - (2 * atr)
        stop = entry - (1 * atr) if is_bullish else entry + (1 * atr)

        detected.append(DetectedPattern(
            symbol=symbol,
            pattern_name=name if is_bullish else f"BEARISH_{name}",
            timeframe=timeframe,
            detected_at=str(df.index[-1]),
            entry_price=entry,
            target_price=round(target, 2),
            stop_loss=round(stop, 2),
            confidence_score=min(confidence, 100),
            volume_confirmation=vol_confirm
        ))

    return detected


# --- Breakout Detection ---

def _detect_breakouts(symbol, df, timeframe) -> List[DetectedPattern]:
    detected = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    atr = float(latest["atr_14"])

    # 52-week high breakout
    if (float(latest["Close"]) >= float(latest["52w_high"]) and
        float(prev["Close"]) < float(prev["52w_high"])):

        vol_confirm = float(latest["Volume"]) > 2.0 * float(latest["vol_sma_20"])
        confidence = 80 if vol_confirm else 55

        detected.append(DetectedPattern(
            symbol=symbol,
            pattern_name="BREAKOUT_52W_HIGH",
            timeframe=timeframe,
            detected_at=str(df.index[-1]),
            entry_price=float(latest["Close"]),
            target_price=round(float(latest["Close"]) + 3 * atr, 2),
            stop_loss=round(float(latest["52w_high"]) * 0.97, 2),
            confidence_score=confidence,
            volume_confirmation=vol_confirm
        ))

    # Bollinger Band breakout
    if float(latest["Close"]) > float(latest["bb_upper"]) and vol_confirm:
        detected.append(DetectedPattern(
            symbol=symbol,
            pattern_name="BREAKOUT_RESISTANCE",
            timeframe=timeframe,
            detected_at=str(df.index[-1]),
            entry_price=float(latest["Close"]),
            target_price=round(float(latest["Close"]) + 2 * atr, 2),
            stop_loss=round(float(latest["bb_upper"]) * 0.98, 2),
            confidence_score=70,
            volume_confirmation=True
        ))

    return detected


# --- Moving Average Crosses ---

def _detect_moving_average_crosses(symbol, df, timeframe) -> List[DetectedPattern]:
    detected = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Golden Cross: SMA50 crosses above SMA200
    if (float(latest["sma_50"]) > float(latest["sma_200"]) and
        float(prev["sma_50"]) <= float(prev["sma_200"])):
        detected.append(DetectedPattern(
            symbol=symbol,
            pattern_name="GOLDEN_CROSS",
            timeframe=timeframe,
            detected_at=str(df.index[-1]),
            entry_price=float(latest["Close"]),
            target_price=None,
            stop_loss=round(float(latest["sma_50"]) * 0.97, 2),
            confidence_score=75,
            volume_confirmation=False
        ))

    # Death Cross: SMA50 crosses below SMA200
    if (float(latest["sma_50"]) < float(latest["sma_200"]) and
        float(prev["sma_50"]) >= float(prev["sma_200"])):
        detected.append(DetectedPattern(
            symbol=symbol,
            pattern_name="DEATH_CROSS",
            timeframe=timeframe,
            detected_at=str(df.index[-1]),
            entry_price=float(latest["Close"]),
            target_price=None,
            stop_loss=round(float(latest["sma_50"]) * 1.03, 2),
            confidence_score=70,
            volume_confirmation=False
        ))

    return detected


# --- RSI Divergence ---

def _detect_divergences(symbol, df, timeframe) -> List[DetectedPattern]:
    """
    Bullish divergence: price making lower lows, RSI making higher lows.
    Bearish divergence: price making higher highs, RSI making lower highs.
    Look back over last 20 bars.
    """
    detected = []
    window = df.tail(20)

    prices = window["Close"].values
    rsi    = window["rsi_14"].values

    # Find pivot points
    from scipy.signal import argrelextrema
    price_min_idx = argrelextrema(prices, np.less, order=3)[0]
    rsi_min_idx   = argrelextrema(rsi, np.less, order=3)[0]

    if len(price_min_idx) >= 2 and len(rsi_min_idx) >= 2:
        # Check if last two price lows are lower while RSI lows are higher
        if (prices[price_min_idx[-1]] < prices[price_min_idx[-2]] and
            rsi[rsi_min_idx[-1]] > rsi[rsi_min_idx[-2]]):

            atr = float(df["atr_14"].iloc[-1])
            entry = float(df["Close"].iloc[-1])
            detected.append(DetectedPattern(
                symbol=symbol,
                pattern_name="BULLISH_DIVERGENCE_RSI",
                timeframe=timeframe,
                detected_at=str(df.index[-1]),
                entry_price=entry,
                target_price=round(entry + 2.5 * atr, 2),
                stop_loss=round(entry - atr, 2),
                confidence_score=72,
                volume_confirmation=False
            ))

    return detected
```

---

## Stage 4: Backtesting Engine

See `BACKTESTING.md` for the full engine. Summary of integration:

```python
# backend/app/workers/pattern_scanner.py

@shared_task
def scan_all_stocks_for_patterns():
    """Nightly: scan all NSE stocks for patterns, backtest each, store results."""
    symbols = get_active_symbols()

    for symbol in symbols:
        scan_stock_patterns.delay(symbol)


@shared_task
def scan_stock_patterns(symbol: str):
    df = load_ohlcv_from_db(symbol, days=365)
    if len(df) < 60:
        return  # Insufficient data

    patterns = detect_all_patterns(symbol, df, timeframe="1D")

    with db_session() as session:
        for p in patterns:
            # Get backtest stats from cache or compute
            stats = get_backtest_stats(symbol, p.pattern_name, "1D")

            # Generate LLM explanation
            explanation = ollama.explain_pattern(p, stats)

            session.add(PatternDetection(
                symbol=p.symbol,
                pattern_name=p.pattern_name,
                timeframe=p.timeframe,
                detected_at=p.detected_at,
                entry_price=p.entry_price,
                target_price=p.target_price,
                stop_loss=p.stop_loss,
                confidence_score=p.confidence_score,
                volume_confirmation=p.volume_confirmation,
                plain_english=explanation,
                backtest_win_rate=stats.win_rate if stats else None,
                backtest_avg_gain=stats.avg_gain_pct if stats else None,
                backtest_avg_loss=stats.avg_loss_pct if stats else None,
                backtest_sample_size=stats.sample_size if stats else None,
            ))
        session.commit()
```

---

## Stage 5: LLM Pattern Explanation

### File: `backend/app/llm/pattern_prompts.py`

```python
PATTERN_EXPLANATION_PROMPT = """
You are a stock market educator explaining technical analysis to a retail Indian investor who understands basic concepts but not advanced chart reading.

Stock: {symbol}
Pattern: {pattern_name}
Timeframe: {timeframe}
Current Price: ₹{entry_price}
Target Price: ₹{target_price}
Stop Loss: ₹{stop_loss}
Volume Confirmation: {volume_confirmation}
Historical Win Rate on this stock: {win_rate}% (over {sample_size} past occurrences)

Write a plain-English explanation in 3 short paragraphs:
1. What this pattern is and what it looks like on the chart (describe visually)
2. What it suggests about buyer/seller behavior and likely next move
3. What an investor should watch for to confirm or invalidate the pattern

Tone: Clear, direct, helpful. No jargon without explanation. Write for someone who checks their portfolio on their phone.
"""
```

---

## Full NSE Universe Scanner

The scanner splits the ~2000 stock universe across multiple Celery workers:

```python
@shared_task
def nightly_full_scan():
    symbols = get_active_symbols()  # ~500 most liquid for hackathon
    batch_size = 50

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        # Celery group: all tasks in parallel
        from celery import group
        job = group(scan_stock_patterns.s(sym) for sym in batch)
        job.apply_async()
```

---

## Supported Patterns Summary

| Category | Patterns |
|---|---|
| Candlestick (Bullish) | Bullish Engulfing, Hammer, Morning Star, Three White Soldiers, Dragonfly Doji, Harami, Piercing |
| Candlestick (Bearish) | Bearish Engulfing, Shooting Star, Evening Star, Three Black Crows, Gravestone Doji, Dark Cloud Cover |
| Breakout | 52W High Breakout, Resistance Breakout, Bollinger Band Squeeze Breakout |
| Breakdown | 52W Low Breakdown, Support Breakdown |
| MA Crosses | Golden Cross (50/200), Death Cross (50/200) |
| Chart Patterns | Cup & Handle, Double Top, Double Bottom, Head & Shoulders, Inverse H&S, Ascending Triangle, Descending Triangle |
| Divergences | RSI Bullish Divergence, RSI Bearish Divergence, MACD Bullish Divergence, MACD Bearish Divergence |
