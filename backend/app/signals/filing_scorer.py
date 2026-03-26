"""
Keyword-based filing scorer. Runs on unprocessed corporate_filings rows.
No LLM required — uses weighted keyword matching for signal extraction.
LLM (Ollama) enrichment can be layered on top later.
"""
from loguru import logger

from app.celery_app import celery_app
from app.database import db_session
from app.models.filing import CorporateFiling
from app.models.signal import Signal

MIN_SCORE = 40

# (signal_type, score, keywords that must appear)
SIGNAL_RULES: list[tuple[str, int, list[str]]] = [
    ("ORDER_WIN",               70, ["order", "contract", "win", "awarded", "bagged", "secured"]),
    ("GUIDANCE_UPGRADE",        65, ["guidance", "upgrade", "raise", "upward revision", "positive outlook"]),
    ("GUIDANCE_DOWNGRADE",      60, ["guidance", "downgrade", "lower", "downward revision", "cautious"]),
    ("MANAGEMENT_TONE_POSITIVE",50, ["confident", "optimistic", "strong", "robust", "record", "growth"]),
    ("MANAGEMENT_TONE_NEGATIVE",55, ["challenging", "headwind", "pressure", "slowdown", "weak demand"]),
    ("REGULATORY_ACTION",       80, ["sebi", "penalty", "show cause", "adjudication", "violation", "fine"]),
    ("FILING_ANOMALY",          60, ["exceptional", "extraordinary", "one-time", "write-off", "impairment"]),
]

# Filing types and their base weight boost
FILING_TYPE_BOOST: dict[str, int] = {
    "quarterly results": 15,
    "analyst meet":      12,
    "board meeting":     8,
    "credit rating":     10,
    "outcome of board":  8,
    "investor meet":     10,
    "press release":     5,
}


def _keyword_match(text: str, keywords: list[str]) -> bool:
    """True if ANY keyword appears in the lowercased text."""
    tl = text.lower()
    return any(k in tl for k in keywords)


def _filing_type_boost(filing_type: str) -> int:
    ft = (filing_type or "").lower()
    for key, boost in FILING_TYPE_BOOST.items():
        if key in ft:
            return boost
    return 0


def score_single_filing(filing: CorporateFiling) -> list[dict]:
    """Return a list of {signal_type, score, title, summary} dicts for one filing."""
    text = (filing.content_text or "") + " " + (filing.subject or "")
    if len(text.strip()) < 20:
        return []

    results = []
    type_boost = _filing_type_boost(filing.filing_type)

    for signal_type, base_score, keywords in SIGNAL_RULES:
        if not _keyword_match(text, keywords):
            continue

        # Count how many keywords matched for a confidence boost
        tl = text.lower()
        matched = [k for k in keywords if k in tl]
        keyword_boost = min(len(matched) * 3, 12)

        score = min(base_score + type_boost + keyword_boost, 100)
        if score < MIN_SCORE:
            continue

        matched_str = ", ".join(f'"{k}"' for k in matched[:3])
        results.append({
            "signal_type": signal_type,
            "score": score,
            "title": f"{signal_type.replace('_', ' ').title()} detected in {filing.filing_type or 'filing'}",
            "summary": (
                f"Filing from {filing.source} for {filing.symbol} contains signals: {matched_str}. "
                f"Filing: {(filing.subject or '')[:120]}."
            ),
        })

    return results


@celery_app.task(name="app.signals.filing_scorer.score_unprocessed_filings")
def score_unprocessed_filings(batch_size: int = 50):
    """Pick up unprocessed filings, score them, mark as processed."""
    with db_session() as session:
        filings = (
            session.query(CorporateFiling)
            .filter(CorporateFiling.is_processed == False)
            .order_by(CorporateFiling.filing_date.desc())
            .limit(batch_size)
            .all()
        )

        created = 0
        for filing in filings:
            signals = score_single_filing(filing)
            for s in signals:
                session.add(Signal(
                    symbol=filing.symbol,
                    signal_type=s["signal_type"],
                    score=s["score"],
                    title=s["title"],
                    summary=s["summary"],
                    source_filing_id=filing.id,
                    data_json={"filing_type": filing.filing_type, "source": filing.source},
                ))
                created += 1
            filing.is_processed = True

    logger.info(f"Filing scorer: processed {len(filings)} filings, created {created} signals")
    return f"Processed {len(filings)} filings, {created} signals"
