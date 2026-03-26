"""
Simple walk-forward backtest for each pattern.
For each historical occurrence, checks outcome N days later.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

from app.patterns.detector import detect_all_patterns
from app.patterns.indicators import compute_indicators


@dataclass
class BacktestResult:
    pattern_name: str
    symbol: str
    timeframe: str
    sample_size: int
    win_rate: float       # %
    avg_gain_pct: float
    avg_loss_pct: float
    avg_holding_days: int
    best_gain_pct: float
    worst_loss_pct: float


def backtest_pattern(
    symbol: str,
    df: pd.DataFrame,
    pattern_name: str,
    timeframe: str = "1D",
    hold_days: int = 10,
    min_samples: int = 3,
) -> Optional[BacktestResult]:
    """
    Walk forward: for each day in history where pattern was detected,
    measure the return hold_days later.
    """
    if len(df) < 120:
        return None

    df = compute_indicators(df.copy())
    outcomes: list[float] = []

    # Slide a window across history (skip last 20 bars = out-of-sample)
    for i in range(60, len(df) - hold_days - 1):
        window = df.iloc[:i]
        patterns = detect_all_patterns(symbol, window, timeframe)
        found = any(p.pattern_name == pattern_name for p in patterns)
        if not found:
            continue

        entry_price = float(df.iloc[i]["Close"])
        exit_price  = float(df.iloc[i + hold_days]["Close"])
        if entry_price <= 0:
            continue

        pct_return = (exit_price - entry_price) / entry_price * 100
        outcomes.append(pct_return)

    if len(outcomes) < min_samples:
        return None

    arr = np.array(outcomes)
    wins = arr[arr > 0]
    losses = arr[arr <= 0]

    return BacktestResult(
        pattern_name=pattern_name,
        symbol=symbol,
        timeframe=timeframe,
        sample_size=len(arr),
        win_rate=round(len(wins) / len(arr) * 100, 1),
        avg_gain_pct=round(float(wins.mean()), 2) if len(wins) else 0.0,
        avg_loss_pct=round(float(losses.mean()), 2) if len(losses) else 0.0,
        avg_holding_days=hold_days,
        best_gain_pct=round(float(arr.max()), 2),
        worst_loss_pct=round(float(arr.min()), 2),
    )
