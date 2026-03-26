"""
Signal compounding — combines multiple signals on the same stock.
"""
from datetime import datetime, timedelta, timezone
from app.database import db_session
from app.models.signal import Signal


def compound_scores(scores: list[int]) -> int:
    """
    Compound N scores using diminishing returns.
    Each additional signal adds 30% of its value × remaining room.
    """
    if not scores:
        return 0
    sorted_scores = sorted(scores, reverse=True)
    compound = sorted_scores[0]
    for s in sorted_scores[1:]:
        remaining = 100 - compound
        compound += int(0.30 * remaining * (s / 100))
    return min(compound, 100)


def get_compounded_score(symbol: str, hours: int = 48) -> int | None:
    """Return the compounded score for a symbol across all recent signals."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with db_session() as session:
        signals = (
            session.query(Signal)
            .filter(
                Signal.symbol == symbol,
                Signal.signal_date >= cutoff,
                Signal.is_active == True,
            )
            .all()
        )
        if not signals:
            return None
        return compound_scores([s.score for s in signals])
