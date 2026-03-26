"""
Computes all technical indicators needed for pattern detection.
Uses pure pandas/numpy — no TA-Lib dependency.
"""
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: DataFrame with columns [Open, High, Low, Close, Volume]
    Output: Same DataFrame enriched with indicator columns.
    Requires at least 60 rows for meaningful results.
    """
    c = df["Close"]
    h = df["High"]
    lo = df["Low"]
    v = df["Volume"].astype(float)

    # --- Moving Averages ---
    df["sma_20"]  = c.rolling(20).mean()
    df["sma_50"]  = c.rolling(50).mean()
    df["sma_200"] = c.rolling(200).mean()
    df["ema_9"]   = c.ewm(span=9, adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21, adjust=False).mean()

    # --- RSI ---
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # --- MACD ---
    ema_12 = c.ewm(span=12, adjust=False).mean()
    ema_26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # --- Bollinger Bands ---
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_mid"]   = sma20
    df["bb_lower"] = sma20 - 2 * std20

    # --- ATR ---
    tr = pd.concat([
        h - lo,
        (h - c.shift()).abs(),
        (lo - c.shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    # --- Volume SMA ---
    df["vol_sma_20"] = v.rolling(20).mean()

    # --- OBV ---
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    df["obv"] = obv

    # --- 52-week high / low ---
    df["52w_high"] = h.rolling(252, min_periods=50).max()
    df["52w_low"]  = lo.rolling(252, min_periods=50).min()

    # --- Candle body / wick sizes (used by candlestick detectors) ---
    df["body"]      = (c - df["Open"]).abs()
    df["body_dir"]  = np.sign(c - df["Open"])   # +1 bull, -1 bear
    df["upper_wick"] = h - pd.concat([c, df["Open"]], axis=1).max(axis=1)
    df["lower_wick"] = pd.concat([c, df["Open"]], axis=1).min(axis=1) - lo
    df["candle_range"] = h - lo

    return df
