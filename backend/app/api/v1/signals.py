from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.signal import Signal
from app.signals.compound import compound_scores

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_signals(
    symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    min_score: int = Query(40, ge=0, le=100),
    hours: int = Query(24, le=168),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        db.query(Signal)
        .filter(Signal.signal_date >= cutoff, Signal.score >= min_score, Signal.is_active == True)
        .order_by(desc(Signal.score), desc(Signal.signal_date))
    )
    if symbol:
        q = q.filter(Signal.symbol == symbol.upper())
    if signal_type:
        q = q.filter(Signal.signal_type == signal_type.upper())

    signals = q.limit(limit).all()
    return [_fmt(s) for s in signals]


@router.get("/top")
def top_signals(
    min_score: int = Query(60, ge=40, le=100),
    hours: int = Query(24, le=168),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """Top signals of the last N hours — the Opportunity Radar feed."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = (
        db.query(Signal)
        .filter(Signal.signal_date >= cutoff, Signal.score >= min_score, Signal.is_active == True)
        .order_by(desc(Signal.score))
        .limit(limit)
        .all()
    )
    return [_fmt(s) for s in signals]


@router.get("/digest")
def daily_digest(db: Session = Depends(get_db)):
    """Today's signal digest — top 10 signals grouped by sector."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    signals = (
        db.query(Signal)
        .filter(Signal.signal_date >= cutoff, Signal.score >= 60, Signal.is_active == True)
        .order_by(desc(Signal.score))
        .all()
    )
    top_10 = [_fmt(s) for s in signals[:10]]
    by_type: dict[str, list] = {}
    for s in signals:
        by_type.setdefault(s.signal_type, []).append(s.symbol)

    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total_signals": len(signals),
        "top_signals": top_10,
        "by_type": {k: list(set(v)) for k, v in by_type.items()},
    }


@router.get("/{symbol}/compounded")
def compounded_score(symbol: str, hours: int = 48, db: Session = Depends(get_db)):
    """Return the compounded conviction score for a stock."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = (
        db.query(Signal)
        .filter(
            Signal.symbol == symbol.upper(),
            Signal.signal_date >= cutoff,
            Signal.is_active == True,
        )
        .all()
    )
    if not signals:
        return {"symbol": symbol.upper(), "compounded_score": None, "signals": []}

    score = compound_scores([s.score for s in signals])
    return {
        "symbol": symbol.upper(),
        "compounded_score": score,
        "signal_count": len(signals),
        "signals": [_fmt(s) for s in signals],
    }


def _fmt(s: Signal) -> dict:
    return {
        "id": s.id,
        "symbol": s.symbol,
        "signal_type": s.signal_type,
        "score": s.score,
        "title": s.title,
        "summary": s.summary,
        "signal_date": s.signal_date.isoformat() if s.signal_date else None,
        "data": s.data_json,
    }
