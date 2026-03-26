from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.pattern import PatternDetection, PatternBacktestStats

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("")
def list_patterns(
    symbol: Optional[str] = None,
    pattern_name: Optional[str] = None,
    min_confidence: int = Query(50, ge=0, le=100),
    hours: int = Query(24, le=168),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        db.query(PatternDetection)
        .filter(PatternDetection.detected_at >= cutoff,
                PatternDetection.confidence_score >= min_confidence)
        .order_by(desc(PatternDetection.confidence_score), desc(PatternDetection.detected_at))
    )
    if symbol:
        q = q.filter(PatternDetection.symbol == symbol.upper())
    if pattern_name:
        q = q.filter(PatternDetection.pattern_name == pattern_name.upper())
    return [_fmt(p) for p in q.limit(limit).all()]


@router.get("/today")
def today_patterns(
    min_confidence: int = Query(60, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """All patterns detected in the last 24 hours, sorted by confidence."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (
        db.query(PatternDetection)
        .filter(PatternDetection.detected_at >= cutoff,
                PatternDetection.confidence_score >= min_confidence)
        .order_by(desc(PatternDetection.confidence_score))
        .all()
    )
    return [_fmt(p) for p in rows]


@router.get("/{symbol}")
def stock_patterns(
    symbol: str,
    hours: int = Query(168, le=720),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(PatternDetection)
        .filter(PatternDetection.symbol == symbol.upper(),
                PatternDetection.detected_at >= cutoff)
        .order_by(desc(PatternDetection.detected_at))
        .all()
    )
    return [_fmt(p) for p in rows]


@router.get("/{symbol}/backtest")
def symbol_backtest_stats(symbol: str, db: Session = Depends(get_db)):
    """Return all backtest stats for a symbol, sorted by win rate."""
    rows = (
        db.query(PatternBacktestStats)
        .filter(PatternBacktestStats.symbol == symbol.upper())
        .order_by(desc(PatternBacktestStats.win_rate))
        .all()
    )
    return [
        {
            "pattern_name": r.pattern_name,
            "timeframe": r.timeframe,
            "sample_size": r.sample_size,
            "win_rate": float(r.win_rate) if r.win_rate else None,
            "avg_gain_pct": float(r.avg_gain_pct) if r.avg_gain_pct else None,
            "avg_loss_pct": float(r.avg_loss_pct) if r.avg_loss_pct else None,
            "avg_holding_days": r.avg_holding_days,
            "best_gain_pct": float(r.best_gain_pct) if r.best_gain_pct else None,
            "worst_loss_pct": float(r.worst_loss_pct) if r.worst_loss_pct else None,
        }
        for r in rows
    ]


def _fmt(p: PatternDetection) -> dict:
    return {
        "id": p.id,
        "symbol": p.symbol,
        "pattern_name": p.pattern_name,
        "timeframe": p.timeframe,
        "detected_at": p.detected_at.isoformat() if p.detected_at else None,
        "entry_price": float(p.entry_price) if p.entry_price else None,
        "target_price": float(p.target_price) if p.target_price else None,
        "stop_loss": float(p.stop_loss) if p.stop_loss else None,
        "confidence_score": p.confidence_score,
        "volume_confirmation": p.volume_confirmation,
        "plain_english": p.plain_english,
        "backtest_win_rate": float(p.backtest_win_rate) if p.backtest_win_rate else None,
        "backtest_avg_gain": float(p.backtest_avg_gain) if p.backtest_avg_gain else None,
        "backtest_sample_size": p.backtest_sample_size,
    }
