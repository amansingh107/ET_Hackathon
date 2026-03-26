"""
Pattern detection engine — no TA-Lib required.
All patterns use pure pandas/numpy/scipy.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from app.patterns.indicators import compute_indicators


@dataclass
class DetectedPattern:
    symbol: str
    pattern_name: str
    timeframe: str
    detected_at: object          # timestamp
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    confidence_score: int        # 0-100
    volume_confirmation: bool


def detect_all_patterns(symbol: str, df: pd.DataFrame, timeframe: str = "1D") -> list[DetectedPattern]:
    if len(df) < 60:
        return []

    df = compute_indicators(df.copy())
    detected: list[DetectedPattern] = []

    detected.extend(_breakouts(symbol, df, timeframe))
    detected.extend(_ma_crosses(symbol, df, timeframe))
    detected.extend(_candlesticks(symbol, df, timeframe))
    detected.extend(_rsi_divergence(symbol, df, timeframe))
    detected.extend(_macd_divergence(symbol, df, timeframe))
    detected.extend(_double_top_bottom(symbol, df, timeframe))

    return detected


# ─── helpers ────────────────────────────────────────────────────────────────

def _vol_ok(row: pd.Series, multiplier: float = 1.5) -> bool:
    return (
        pd.notna(row["vol_sma_20"])
        and float(row["vol_sma_20"]) > 0
        and float(row["Volume"]) > multiplier * float(row["vol_sma_20"])
    )


def _atr_targets(row: pd.Series, bullish: bool, atr_mult_target: float = 2.0, atr_mult_stop: float = 1.0):
    atr   = float(row["atr_14"])
    entry = float(row["Close"])
    if bullish:
        return round(entry + atr_mult_target * atr, 2), round(entry - atr_mult_stop * atr, 2)
    return round(entry - atr_mult_target * atr, 2), round(entry + atr_mult_stop * atr, 2)


# ─── Breakouts ───────────────────────────────────────────────────────────────

def _breakouts(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    r   = df.iloc[-1]
    p   = df.iloc[-2]
    atr = float(r["atr_14"]) if pd.notna(r["atr_14"]) else 0

    # 52-week high breakout
    if (pd.notna(r["52w_high"]) and pd.notna(p["52w_high"])
            and float(r["Close"]) >= float(r["52w_high"])
            and float(p["Close"]) < float(p["52w_high"])):
        vc = _vol_ok(r, 2.0)
        out.append(DetectedPattern(
            symbol=symbol, pattern_name="BREAKOUT_52W_HIGH", timeframe=timeframe,
            detected_at=df.index[-1], entry_price=float(r["Close"]),
            target_price=round(float(r["Close"]) + 3 * atr, 2),
            stop_loss=round(float(r["52w_high"]) * 0.97, 2),
            confidence_score=82 if vc else 58, volume_confirmation=vc,
        ))

    # 52-week low breakdown
    if (pd.notna(r["52w_low"]) and pd.notna(p["52w_low"])
            and float(r["Close"]) <= float(r["52w_low"])
            and float(p["Close"]) > float(p["52w_low"])):
        vc = _vol_ok(r, 2.0)
        out.append(DetectedPattern(
            symbol=symbol, pattern_name="BREAKDOWN_52W_LOW", timeframe=timeframe,
            detected_at=df.index[-1], entry_price=float(r["Close"]),
            target_price=round(float(r["Close"]) - 3 * atr, 2),
            stop_loss=round(float(r["52w_low"]) * 1.03, 2),
            confidence_score=78 if vc else 55, volume_confirmation=vc,
        ))

    # Bollinger Band breakout (upper)
    if (pd.notna(r["bb_upper"])
            and float(r["Close"]) > float(r["bb_upper"])
            and float(p["Close"]) <= float(p["bb_upper"])):
        vc = _vol_ok(r)
        out.append(DetectedPattern(
            symbol=symbol, pattern_name="BREAKOUT_RESISTANCE", timeframe=timeframe,
            detected_at=df.index[-1], entry_price=float(r["Close"]),
            target_price=round(float(r["Close"]) + 2 * atr, 2),
            stop_loss=round(float(r["bb_upper"]) * 0.98, 2),
            confidence_score=68 if vc else 48, volume_confirmation=vc,
        ))

    return out


# ─── Moving average crosses ───────────────────────────────────────────────────

def _ma_crosses(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    r, p = df.iloc[-1], df.iloc[-2]

    if any(pd.isna([r["sma_50"], r["sma_200"], p["sma_50"], p["sma_200"]])):
        return out

    # Golden cross
    if float(r["sma_50"]) > float(r["sma_200"]) and float(p["sma_50"]) <= float(p["sma_200"]):
        out.append(DetectedPattern(
            symbol=symbol, pattern_name="GOLDEN_CROSS", timeframe=timeframe,
            detected_at=df.index[-1], entry_price=float(r["Close"]),
            target_price=None, stop_loss=round(float(r["sma_50"]) * 0.97, 2),
            confidence_score=75, volume_confirmation=False,
        ))

    # Death cross
    if float(r["sma_50"]) < float(r["sma_200"]) and float(p["sma_50"]) >= float(p["sma_200"]):
        out.append(DetectedPattern(
            symbol=symbol, pattern_name="DEATH_CROSS", timeframe=timeframe,
            detected_at=df.index[-1], entry_price=float(r["Close"]),
            target_price=None, stop_loss=round(float(r["sma_50"]) * 1.03, 2),
            confidence_score=72, volume_confirmation=False,
        ))

    return out


# ─── Candlestick patterns (pure math) ────────────────────────────────────────

def _candlesticks(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    r = df.iloc[-1]
    p = df.iloc[-2]

    body      = float(r["body"])
    body_dir  = float(r["body_dir"])
    ul_wick   = float(r["upper_wick"])
    ll_wick   = float(r["lower_wick"])
    crange    = float(r["candle_range"]) or 0.001
    atr       = float(r["atr_14"]) if pd.notna(r["atr_14"]) else 1
    entry     = float(r["Close"])
    vc        = _vol_ok(r)

    # Bullish engulfing
    if (body_dir > 0
            and float(p["body_dir"]) < 0
            and float(r["Open"]) < float(p["Close"])
            and float(r["Close"]) > float(p["Open"])):
        conf = 70 + (20 if vc else 0) + (10 if entry > float(r["sma_50"]) and pd.notna(r["sma_50"]) else 0)
        tgt, sl = _atr_targets(r, True)
        out.append(DetectedPattern(symbol=symbol, pattern_name="BULLISH_ENGULFING",
            timeframe=timeframe, detected_at=df.index[-1], entry_price=entry,
            target_price=tgt, stop_loss=sl, confidence_score=min(conf, 95), volume_confirmation=vc))

    # Bearish engulfing
    if (body_dir < 0
            and float(p["body_dir"]) > 0
            and float(r["Open"]) > float(p["Close"])
            and float(r["Close"]) < float(p["Open"])):
        conf = 70 + (20 if vc else 0)
        tgt, sl = _atr_targets(r, False)
        out.append(DetectedPattern(symbol=symbol, pattern_name="BEARISH_ENGULFING",
            timeframe=timeframe, detected_at=df.index[-1], entry_price=entry,
            target_price=tgt, stop_loss=sl, confidence_score=min(conf, 95), volume_confirmation=vc))

    # Hammer (bullish reversal at bottom)
    if (body / crange < 0.35               # small body
            and ll_wick > 2 * body          # long lower wick
            and ul_wick < 0.1 * crange):   # tiny upper wick
        conf = 62 + (18 if vc else 0)
        tgt, sl = _atr_targets(r, True)
        out.append(DetectedPattern(symbol=symbol, pattern_name="HAMMER",
            timeframe=timeframe, detected_at=df.index[-1], entry_price=entry,
            target_price=tgt, stop_loss=sl, confidence_score=conf, volume_confirmation=vc))

    # Shooting star (bearish reversal at top)
    if (body / crange < 0.35
            and ul_wick > 2 * body
            and ll_wick < 0.1 * crange):
        conf = 62 + (18 if vc else 0)
        tgt, sl = _atr_targets(r, False)
        out.append(DetectedPattern(symbol=symbol, pattern_name="SHOOTING_STAR",
            timeframe=timeframe, detected_at=df.index[-1], entry_price=entry,
            target_price=tgt, stop_loss=sl, confidence_score=conf, volume_confirmation=vc))

    # Doji (indecision)
    if body / crange < 0.1:
        out.append(DetectedPattern(symbol=symbol, pattern_name="DOJI",
            timeframe=timeframe, detected_at=df.index[-1], entry_price=entry,
            target_price=None, stop_loss=None, confidence_score=55, volume_confirmation=vc))

    return out


# ─── RSI Divergence ──────────────────────────────────────────────────────────

def _rsi_divergence(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    window = df.tail(30).copy()

    if window["rsi_14"].isna().sum() > 5:
        return out

    prices = window["Close"].values.astype(float)
    rsi    = window["rsi_14"].values.astype(float)

    price_lows = argrelextrema(prices, np.less, order=3)[0]
    rsi_lows   = argrelextrema(rsi,    np.less, order=3)[0]

    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        if (prices[price_lows[-1]] < prices[price_lows[-2]]
                and rsi[rsi_lows[-1]] > rsi[rsi_lows[-2]]):
            r = df.iloc[-1]
            tgt, sl = _atr_targets(r, True)
            out.append(DetectedPattern(symbol=symbol, pattern_name="BULLISH_DIVERGENCE_RSI",
                timeframe=timeframe, detected_at=df.index[-1], entry_price=float(r["Close"]),
                target_price=tgt, stop_loss=sl, confidence_score=72, volume_confirmation=False))

    price_highs = argrelextrema(prices, np.greater, order=3)[0]
    rsi_highs   = argrelextrema(rsi,    np.greater, order=3)[0]

    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        if (prices[price_highs[-1]] > prices[price_highs[-2]]
                and rsi[rsi_highs[-1]] < rsi[rsi_highs[-2]]):
            r = df.iloc[-1]
            tgt, sl = _atr_targets(r, False)
            out.append(DetectedPattern(symbol=symbol, pattern_name="BEARISH_DIVERGENCE_RSI",
                timeframe=timeframe, detected_at=df.index[-1], entry_price=float(r["Close"]),
                target_price=tgt, stop_loss=sl, confidence_score=70, volume_confirmation=False))

    return out


# ─── MACD Divergence ─────────────────────────────────────────────────────────

def _macd_divergence(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    window = df.tail(30).copy()

    if window["macd"].isna().sum() > 5:
        return out

    prices = window["Close"].values.astype(float)
    macd   = window["macd"].values.astype(float)

    price_lows = argrelextrema(prices, np.less, order=3)[0]
    macd_lows  = argrelextrema(macd,   np.less, order=3)[0]

    if len(price_lows) >= 2 and len(macd_lows) >= 2:
        if (prices[price_lows[-1]] < prices[price_lows[-2]]
                and macd[macd_lows[-1]] > macd[macd_lows[-2]]):
            r = df.iloc[-1]
            tgt, sl = _atr_targets(r, True)
            out.append(DetectedPattern(symbol=symbol, pattern_name="BULLISH_DIVERGENCE_MACD",
                timeframe=timeframe, detected_at=df.index[-1], entry_price=float(r["Close"]),
                target_price=tgt, stop_loss=sl, confidence_score=70, volume_confirmation=False))

    return out


# ─── Double Top / Double Bottom ───────────────────────────────────────────────

def _double_top_bottom(symbol, df, timeframe) -> list[DetectedPattern]:
    out = []
    window = df.tail(60).copy()
    prices = window["Close"].values.astype(float)

    highs = argrelextrema(prices, np.greater, order=5)[0]
    lows  = argrelextrema(prices, np.less,    order=5)[0]

    r = df.iloc[-1]

    # Double top: two similar highs, price just broke below the "neckline"
    if len(highs) >= 2:
        h1, h2 = prices[highs[-2]], prices[highs[-1]]
        if abs(h1 - h2) / h1 < 0.03:          # within 3% of each other
            neckline = min(prices[highs[-2]:highs[-1]])
            if float(r["Close"]) < neckline:
                tgt, sl = _atr_targets(r, False, atr_mult_target=3.0)
                out.append(DetectedPattern(symbol=symbol, pattern_name="DOUBLE_TOP",
                    timeframe=timeframe, detected_at=df.index[-1], entry_price=float(r["Close"]),
                    target_price=tgt, stop_loss=sl, confidence_score=73, volume_confirmation=False))

    # Double bottom: two similar lows, price just broke above neckline
    if len(lows) >= 2:
        l1, l2 = prices[lows[-2]], prices[lows[-1]]
        if abs(l1 - l2) / l1 < 0.03:
            neckline = max(prices[lows[-2]:lows[-1]])
            if float(r["Close"]) > neckline:
                tgt, sl = _atr_targets(r, True, atr_mult_target=3.0)
                out.append(DetectedPattern(symbol=symbol, pattern_name="DOUBLE_BOTTOM",
                    timeframe=timeframe, detected_at=df.index[-1], entry_price=float(r["Close"]),
                    target_price=tgt, stop_loss=sl, confidence_score=75, volume_confirmation=False))

    return out
