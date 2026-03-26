"""
Nightly pattern scanner — loads OHLCV from DB, runs detector, stores results.
"""
from datetime import datetime, timezone

import pandas as pd
from loguru import logger
from sqlalchemy import text

from app.celery_app import celery_app
from app.database import db_session
from app.models.stock import Stock
from app.models.ohlcv import OHLCVDaily
from app.models.pattern import PatternDetection, PatternBacktestStats
from app.patterns.detector import detect_all_patterns
from app.patterns.backtest import backtest_pattern


def _load_ohlcv(session, symbol: str, days: int = 365) -> pd.DataFrame:
    rows = (
        session.query(OHLCVDaily)
        .filter(OHLCVDaily.symbol == symbol)
        .order_by(OHLCVDaily.time.asc())
        .limit(days)
        .all()
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "Open":   float(r.open  or 0),
        "High":   float(r.high  or 0),
        "Low":    float(r.low   or 0),
        "Close":  float(r.close or 0),
        "Volume": int(r.volume  or 0),
    } for r in rows], index=[r.time for r in rows])
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_or_compute_backtest(session, symbol: str, pattern_name: str, timeframe: str, df: pd.DataFrame):
    """Return cached backtest stats or compute on the fly."""
    cached = session.query(PatternBacktestStats).filter_by(
        symbol=symbol, pattern_name=pattern_name, timeframe=timeframe,
    ).first()
    if cached:
        return cached

    result = backtest_pattern(symbol, df, pattern_name, timeframe)
    if result is None:
        return None

    stats = PatternBacktestStats(
        symbol=symbol, pattern_name=pattern_name, timeframe=timeframe,
        sample_size=result.sample_size, win_rate=result.win_rate,
        avg_gain_pct=result.avg_gain_pct, avg_loss_pct=result.avg_loss_pct,
        avg_holding_days=result.avg_holding_days, best_gain_pct=result.best_gain_pct,
        worst_loss_pct=result.worst_loss_pct,
    )
    session.add(stats)
    return stats


@celery_app.task(name="app.workers.pattern_scanner.scan_stock_patterns")
def scan_stock_patterns(symbol: str, timeframe: str = "1D"):
    """Scan a single stock for all patterns and store results."""
    with db_session() as session:
        df = _load_ohlcv(session, symbol, days=365)
        if len(df) < 60:
            return f"{symbol}: insufficient data ({len(df)} rows)"

        patterns = detect_all_patterns(symbol, df, timeframe)
        if not patterns:
            return f"{symbol}: no patterns detected"

        created = 0
        for p in patterns:
            # Skip duplicate (same symbol+pattern today)
            exists = session.query(PatternDetection).filter(
                PatternDetection.symbol == symbol,
                PatternDetection.pattern_name == p.pattern_name,
                PatternDetection.timeframe == timeframe,
                PatternDetection.detected_at >= datetime.now(timezone.utc).date().isoformat(),
            ).first()
            if exists:
                continue

            stats = _get_or_compute_backtest(session, symbol, p.pattern_name, timeframe, df)

            session.add(PatternDetection(
                symbol=symbol,
                pattern_name=p.pattern_name,
                timeframe=timeframe,
                detected_at=p.detected_at,
                entry_price=p.entry_price,
                target_price=p.target_price,
                stop_loss=p.stop_loss,
                confidence_score=p.confidence_score,
                volume_confirmation=p.volume_confirmation,
                plain_english=_plain_english(p, stats),
                backtest_win_rate=stats.win_rate if stats else None,
                backtest_avg_gain=stats.avg_gain_pct if stats else None,
                backtest_avg_loss=stats.avg_loss_pct if stats else None,
                backtest_sample_size=stats.sample_size if stats else None,
            ))
            created += 1

    logger.info(f"Pattern scan {symbol}: {created} patterns stored")
    return f"{symbol}: {created} patterns"


@celery_app.task(name="app.workers.pattern_scanner.scan_all_stocks")
def scan_all_stocks():
    """Dispatch per-stock scan tasks for all active stocks."""
    with db_session() as session:
        symbols = [r.symbol for r in session.query(Stock.symbol).filter(Stock.is_active == True).all()]

    logger.info(f"Dispatching pattern scan for {len(symbols)} stocks")
    for symbol in symbols:
        scan_stock_patterns.apply_async(args=[symbol], queue="default")
    return f"Dispatched {len(symbols)} pattern scan tasks"


def _plain_english(p, stats) -> str:
    """Generate a simple rule-based explanation (Ollama can enrich this later)."""
    win_info = ""
    if stats and stats.win_rate is not None:
        win_info = (
            f" Historically on this stock, this pattern has worked {stats.win_rate:.0f}% of the time "
            f"across {stats.sample_size} occurrences, with avg gain of {stats.avg_gain_pct:.1f}%."
        )

    explanations = {
        "GOLDEN_CROSS": (
            f"{p.symbol}'s 50-day average just crossed above its 200-day average — a classic bullish signal "
            f"called the 'Golden Cross'. It suggests the medium-term trend is now stronger than the long-term trend. "
            f"Entry: ₹{p.entry_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
        "DEATH_CROSS": (
            f"{p.symbol}'s 50-day average just crossed below its 200-day average — a 'Death Cross'. "
            f"It signals weakening momentum. Caution advised. Stop if price rises above ₹{p.stop_loss}." + win_info
        ),
        "BREAKOUT_52W_HIGH": (
            f"{p.symbol} just hit a fresh 52-week high at ₹{p.entry_price}. Breakouts at all-time highs often "
            f"continue higher, especially with strong volume. Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
        "BREAKDOWN_52W_LOW": (
            f"{p.symbol} broke to a new 52-week low. Avoid catching a falling knife. "
            f"Wait for stabilization before considering entry." + win_info
        ),
        "BULLISH_ENGULFING": (
            f"A large green candle completely swallowed yesterday's red candle on {p.symbol}. "
            f"This 'Bullish Engulfing' suggests buyers took control. "
            f"Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
        "BEARISH_ENGULFING": (
            f"A large red candle swallowed yesterday's green candle on {p.symbol}. "
            f"Sellers are in control. Consider exiting longs. Stop: ₹{p.stop_loss}." + win_info
        ),
        "HAMMER": (
            f"{p.symbol} formed a Hammer — a small body with a long lower wick. "
            f"Buyers rejected lower prices. Bullish reversal signal. "
            f"Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
        "SHOOTING_STAR": (
            f"{p.symbol} formed a Shooting Star — small body, long upper wick. "
            f"Sellers pushed price down from highs. Bearish reversal signal." + win_info
        ),
        "BULLISH_DIVERGENCE_RSI": (
            f"{p.symbol}'s price made a lower low but RSI made a higher low — Bullish Divergence. "
            f"Momentum is improving even as price dips. Potential reversal signal. "
            f"Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
        "BEARISH_DIVERGENCE_RSI": (
            f"{p.symbol}'s price made a higher high but RSI made a lower high — Bearish Divergence. "
            f"Momentum is weakening. Possible trend reversal ahead." + win_info
        ),
        "DOUBLE_TOP": (
            f"{p.symbol} formed a Double Top — price tried to break higher twice but failed. "
            f"Classic reversal pattern. Bearish below the neckline. Stop: ₹{p.stop_loss}." + win_info
        ),
        "DOUBLE_BOTTOM": (
            f"{p.symbol} formed a Double Bottom — price tested support twice and bounced. "
            f"Strong reversal signal. Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
        ),
    }
    return explanations.get(
        p.pattern_name,
        f"{p.pattern_name.replace('_', ' ').title()} detected on {p.symbol} at ₹{p.entry_price}. "
        f"Target: ₹{p.target_price}, Stop: ₹{p.stop_loss}." + win_info
    )
