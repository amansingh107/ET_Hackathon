"""
Detects insider buy/sell clusters and scores them.
Clusters = 2+ insiders trading the same direction within 7 days.
"""
from datetime import date, timedelta
from loguru import logger

from app.celery_app import celery_app
from app.database import db_session
from app.models.insider import InsiderTrade
from app.models.signal import Signal

MIN_SCORE = 40

ACQUIRER_BASE = {
    "promoter": 65,
    "director": 50,
    "kmp": 50,
    "key managerial": 50,
    "relative": 35,
    "associate": 35,
}


def _base_score(acquirer_type: str) -> int:
    t = (acquirer_type or "").lower()
    for key, score in ACQUIRER_BASE.items():
        if key in t:
            return score
    return 40


def _cluster_multiplier(count: int) -> float:
    if count >= 4:
        return 1.7
    if count == 3:
        return 1.5
    if count == 2:
        return 1.3
    return 1.0


def _value_bonus(total_value_cr: float) -> int:
    if total_value_cr >= 100:
        return 35
    if total_value_cr >= 50:
        return 25
    if total_value_cr >= 10:
        return 15
    return 0


def _stake_bonus(trades: list[InsiderTrade]) -> int:
    max_change = 0.0
    for t in trades:
        if t.before_holding_pct is not None and t.after_holding_pct is not None:
            change = float(t.after_holding_pct) - float(t.before_holding_pct)
            if change > max_change:
                max_change = change
    if max_change >= 2.0:
        return 20
    if max_change >= 1.0:
        return 10
    return 0


@celery_app.task(name="app.signals.insider_scorer.score_insider_trades")
def score_insider_trades():
    """Detect clusters in the last 7 days and score them."""
    cutoff = date.today() - timedelta(days=7)

    with db_session() as session:
        recent = session.query(InsiderTrade).filter(
            InsiderTrade.trade_date >= cutoff,
        ).all()

        # Group by (symbol, trade_type)
        groups: dict[tuple, list] = {}
        for t in recent:
            key = (t.symbol, t.trade_type or "BUY")
            groups.setdefault(key, []).append(t)

        created = 0
        for (symbol, trade_type), trades in groups.items():
            # Single promoter buys still count; cluster multiplier kicks in for 2+
            base = max(_base_score(t.acquirer_type) for t in trades)
            multiplier = _cluster_multiplier(len(trades))
            score = int(base * multiplier)

            total_value_cr = sum(
                float(t.quantity or 0) * float(t.price or 0) / 1e7
                for t in trades
            )
            score += _value_bonus(total_value_cr)
            score += _stake_bonus(trades)
            score = min(score, 100)

            if score < MIN_SCORE:
                continue

            signal_type = (
                "INSIDER_BUY_CLUSTER" if trade_type == "BUY"
                else "INSIDER_SELL_CLUSTER"
            )
            acquirer_types = ", ".join(
                sorted(set(t.acquirer_type or "Unknown" for t in trades))
            )

            # Deduplicate: skip if we already have this signal in last 7 days
            exists = session.query(Signal).filter(
                Signal.symbol == symbol,
                Signal.signal_type == signal_type,
                Signal.signal_date >= (
                    date.today() - timedelta(days=7)
                ).isoformat(),
            ).first()
            if exists:
                continue

            session.add(Signal(
                symbol=symbol,
                signal_type=signal_type,
                score=score,
                title=(
                    f"{len(trades)} insider{'s' if len(trades) > 1 else ''} "
                    f"{trade_type.lower()} ₹{total_value_cr:.1f}Cr in 7 days"
                ),
                summary=(
                    f"{acquirer_types} traded {trade_type.lower()} for {symbol}. "
                    f"Total: ₹{total_value_cr:.1f}Cr across {len(trades)} transaction(s). "
                    f"Score: {score}/100."
                ),
                data_json={
                    "trade_ids": [t.id for t in trades],
                    "total_value_cr": round(total_value_cr, 2),
                    "acquirer_types": acquirer_types,
                    "cluster_size": len(trades),
                },
            ))
            created += 1

    logger.info(f"Insider scorer: {created} signals created")
    return f"Created {created} insider signals"
