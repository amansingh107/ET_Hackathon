# Backtesting Engine

Computes historical success rates for each (pattern, stock, timeframe) combination using 5 years of OHLCV data.

---

## Design Principles

1. **Per-stock, per-pattern stats** — "Bullish Engulfing on RELIANCE has 68% win rate" is more useful than a generic market-wide rate
2. **No survivorship bias** — include all historical occurrences, even when the stock later underperformed
3. **Forward-looking metric** — measure outcome N days *after* pattern, not during
4. **Win definition** — price closes above entry price by more than 2% within holding_days

---

## Engine Implementation

### File: `backend/app/backtest/engine.py`

```python
"""
Backtesting engine for chart patterns.
For each (symbol, pattern, timeframe):
  1. Scan historical data for all occurrences of the pattern
  2. For each occurrence, measure outcome at 5, 10, 20 days forward
  3. Compute win rate, avg gain, avg loss, best/worst
  4. Store in pattern_backtest_stats table
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from app.patterns.detector import detect_all_patterns

# How many days forward to measure outcome
HOLDING_PERIODS = [5, 10, 20]  # trading days
PRIMARY_HOLDING_PERIOD = 10     # Use 10-day outcome as primary metric

# Win = price rises more than this % within holding period
WIN_THRESHOLD_PCT = 2.0


@dataclass
class BacktestStats:
    symbol: str
    pattern_name: str
    timeframe: str
    sample_size: int
    win_rate: float          # % of occurrences that hit WIN_THRESHOLD
    avg_gain_pct: float      # average % gain on winning trades
    avg_loss_pct: float      # average % loss on losing trades
    best_gain_pct: float
    worst_loss_pct: float
    avg_holding_days: int
    expectancy: float        # (win_rate * avg_gain) - (loss_rate * avg_loss)


def backtest_pattern_on_stock(
    symbol: str,
    pattern_name: str,
    df: pd.DataFrame,
    timeframe: str = "1D",
    holding_days: int = PRIMARY_HOLDING_PERIOD
) -> Optional[BacktestStats]:
    """
    Scan df for all historical occurrences of pattern_name.
    Measure forward returns at holding_days.
    Minimum 10 occurrences required for meaningful stats.
    """
    occurrences = _find_historical_occurrences(df, pattern_name)

    if len(occurrences) < 10:
        return None  # Insufficient history

    gains = []
    for occ_idx in occurrences:
        entry_price = df["Close"].iloc[occ_idx]

        # Forward price at holding_days (or last available if near end of data)
        forward_idx = min(occ_idx + holding_days, len(df) - 1)
        exit_price = df["Close"].iloc[forward_idx]

        pct_change = (exit_price - entry_price) / entry_price * 100
        gains.append(pct_change)

    wins = [g for g in gains if g >= WIN_THRESHOLD_PCT]
    losses = [g for g in gains if g < WIN_THRESHOLD_PCT]

    win_rate = len(wins) / len(gains) * 100
    avg_gain = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 0.0
    expectancy = (win_rate / 100 * avg_gain) - ((1 - win_rate / 100) * avg_loss)

    return BacktestStats(
        symbol=symbol,
        pattern_name=pattern_name,
        timeframe=timeframe,
        sample_size=len(gains),
        win_rate=round(win_rate, 1),
        avg_gain_pct=round(avg_gain, 2),
        avg_loss_pct=round(avg_loss, 2),
        best_gain_pct=round(max(gains), 2),
        worst_loss_pct=round(min(gains), 2),
        avg_holding_days=holding_days,
        expectancy=round(expectancy, 2)
    )


def _find_historical_occurrences(df: pd.DataFrame, pattern_name: str) -> list[int]:
    """
    Scan the full dataframe bar by bar.
    For each bar i, check if pattern was detected using [0:i] history.
    Returns list of bar indices where pattern fired.

    This is O(n²) but runs nightly in background — acceptable.
    For very long histories, use a rolling window approach.
    """
    occurrences = []
    min_bars = 60  # Need at least 60 bars of history for most indicators

    for i in range(min_bars, len(df) - 20):  # Leave 20 bars for forward measurement
        window = df.iloc[:i+1].copy()
        patterns = detect_all_patterns("__backtest__", window, timeframe="1D")
        if any(p.pattern_name == pattern_name for p in patterns):
            # Avoid double-counting consecutive detections
            if occurrences and i - occurrences[-1] < 5:
                continue
            occurrences.append(i)

    return occurrences
```

---

## Batch Backtest Runner

### File: `backend/app/backtest/batch_runner.py`

```python
"""
Nightly batch: compute/refresh backtest stats for all active pattern+stock combinations.
Run this once during initial setup (takes hours), then incrementally nightly.
"""
from celery import shared_task, group
from app.backtest.engine import backtest_pattern_on_stock

ALL_PATTERNS = [
    "BULLISH_ENGULFING", "BEARISH_ENGULFING",
    "HAMMER", "SHOOTING_STAR", "DOJI",
    "MORNING_STAR", "EVENING_STAR",
    "THREE_WHITE_SOLDIERS", "THREE_BLACK_CROWS",
    "BREAKOUT_52W_HIGH", "BREAKDOWN_52W_LOW",
    "GOLDEN_CROSS", "DEATH_CROSS",
    "BULLISH_DIVERGENCE_RSI", "BEARISH_DIVERGENCE_RSI",
    "DOUBLE_TOP", "DOUBLE_BOTTOM",
    "HEAD_AND_SHOULDERS", "INVERSE_HEAD_SHOULDERS",
]


@shared_task
def run_full_backtest_suite():
    """
    Schedule: Weekly on Sunday night (most compute-intensive task).
    Run per-stock per-pattern backtests for all active stocks.
    """
    symbols = get_active_symbols()

    for symbol in symbols:
        run_stock_backtest.delay(symbol)


@shared_task
def run_stock_backtest(symbol: str):
    """Compute backtest stats for all patterns on a single stock."""
    df = load_ohlcv_from_db(symbol, days=365 * 5)  # 5 years
    if len(df) < 252:  # Need at least 1 year
        return

    with db_session() as session:
        for pattern_name in ALL_PATTERNS:
            stats = backtest_pattern_on_stock(symbol, pattern_name, df)
            if stats is None:
                continue

            # Upsert into pattern_backtest_stats
            existing = session.query(PatternBacktestStats).filter_by(
                symbol=symbol,
                pattern_name=pattern_name,
                timeframe="1D"
            ).first()

            if existing:
                existing.sample_size = stats.sample_size
                existing.win_rate = stats.win_rate
                existing.avg_gain_pct = stats.avg_gain_pct
                existing.avg_loss_pct = stats.avg_loss_pct
                existing.best_gain_pct = stats.best_gain_pct
                existing.worst_loss_pct = stats.worst_loss_pct
                existing.last_computed = datetime.now()
            else:
                session.add(PatternBacktestStats(
                    symbol=symbol,
                    pattern_name=pattern_name,
                    timeframe="1D",
                    sample_size=stats.sample_size,
                    win_rate=stats.win_rate,
                    avg_gain_pct=stats.avg_gain_pct,
                    avg_loss_pct=stats.avg_loss_pct,
                    best_gain_pct=stats.best_gain_pct,
                    worst_loss_pct=stats.worst_loss_pct,
                ))
        session.commit()
```

---

## Optimized Approach for Initial Setup

Full backtest for 500 stocks × 20 patterns is expensive. Use this phased approach:

### Phase 1: Nifty 50 only (Day 1)
```python
NIFTY50 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "KOTAKBANK", "HINDUNILVR", "BAJFINANCE", "BHARTIARTL", "ITC",
    # ... etc
]
```

### Phase 2: Nifty 500 (Week 1)
Expand to 500 stocks.

### Phase 3: Full NSE universe (Ongoing)
Add remaining 1500+ stocks incrementally.

---

## Backtest Stats Display

How to present stats to users:

```
Bullish Engulfing on RELIANCE (Daily, last 5 years)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Occurrences: 34
Win Rate:    68%   (23 of 34 times)
Avg Gain:    +6.2% (on winners, held 10 days)
Avg Loss:    -2.8% (on losers, held 10 days)
Best:       +24.1%  Worst: -8.3%
Expectancy:  +1.2% per trade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Past performance does not guarantee future results.
   Historical data used for educational purposes only.
```

---

## Limitations and Disclosures

Always display with backtest data:

1. **Lookback bias**: Patterns are detected using indicators that require historical data — in live trading you'd use real-time data which may differ slightly
2. **Slippage**: No slippage or transaction costs modeled
3. **Liquidity**: Small-cap stocks may have insufficient liquidity to execute at detected prices
4. **Sample size**: Stats with < 20 occurrences have high variance — treat as indicative only
5. **Regime changes**: A pattern that worked in 2019–2021 bull market may not work in bear markets
