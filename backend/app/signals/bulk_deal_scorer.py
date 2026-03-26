"""
Scores bulk and block deals and writes Signal rows.
Run via Celery task or directly after fetch_bulk_deals.
"""
from datetime import date
from loguru import logger

from app.celery_app import celery_app
from app.database import db_session
from app.models.deals import BulkBlockDeal
from app.models.signal import Signal

KNOWN_INSTITUTIONS = {
    "MIRAE ASSET", "NIPPON", "SBI MF", "SBI MUTUAL", "HDFC MF", "HDFC MUTUAL",
    "AXIS MF", "AXIS MUTUAL", "ICICI PRUDENTIAL", "KOTAK MF", "KOTAK MUTUAL",
    "DSP", "FRANKLIN", "TATA MF", "UTI MF", "LIC", "GIC", "NPS TRUST",
    "FOREIGN PORTFOLIO", "FPI", "FII",
}

MIN_SCORE = 40


def _score_deal(deal: BulkBlockDeal) -> int:
    score = 0

    # Volume ratio → base score
    ratio = float(deal.volume_ratio or 0)
    if ratio >= 5.0:
        score += 50
    elif ratio >= 2.0:
        score += 35
    elif ratio >= 1.0:
        score += 20
    else:
        score += 5

    # Direction
    score += 20 if deal.buy_sell == "BUY" else 10

    # Known institution
    client = (deal.client_name or "").upper()
    if any(inst in client for inst in KNOWN_INSTITUTIONS):
        score += 15

    # Block > Bulk
    if deal.deal_type == "BLOCK":
        score += 10

    return min(score, 100)


def _deal_summary(deal: BulkBlockDeal, score: int) -> str:
    val = f"₹{deal.deal_value_cr:.1f}Cr" if deal.deal_value_cr else ""
    ratio = f"{deal.volume_ratio:.1f}x avg vol" if deal.volume_ratio else ""
    parts = [p for p in [val, ratio] if p]
    return (
        f"{deal.client_name or 'Unknown'} {deal.buy_sell} {deal.quantity:,} shares "
        f"of {deal.symbol}. {', '.join(parts)}. Score: {score}/100."
    )


@celery_app.task(name="app.signals.bulk_deal_scorer.score_bulk_deals_today")
def score_bulk_deals_today(target_date: str = None):
    """Score all bulk/block deals for a given date (default: today)."""
    d = date.fromisoformat(target_date) if target_date else date.today()

    with db_session() as session:
        deals = session.query(BulkBlockDeal).filter(BulkBlockDeal.deal_date == d).all()
        created = 0

        for deal in deals:
            # Duplicate guard — same signal type for same stock today
            exists = session.query(Signal).filter(
                Signal.symbol == deal.symbol,
                Signal.signal_type == "BULK_DEAL_UNUSUAL",
                Signal.data_json["deal_id"].astext == str(deal.id),
            ).first()
            if exists:
                continue

            score = _score_deal(deal)
            if score < MIN_SCORE:
                continue

            session.add(Signal(
                symbol=deal.symbol,
                signal_type="BULK_DEAL_UNUSUAL",
                score=score,
                title=(
                    f"{'Block' if deal.deal_type == 'BLOCK' else 'Bulk'} deal: "
                    f"{deal.client_name or 'Unknown'} {deal.buy_sell} "
                    f"{deal.quantity:,} shares"
                ),
                summary=_deal_summary(deal, score),
                data_json={"deal_id": deal.id, "volume_ratio": float(deal.volume_ratio or 0)},
            ))
            created += 1

    logger.info(f"Bulk deal scorer: {created} signals created for {d}")
    return f"Created {created} bulk deal signals"
