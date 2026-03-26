"""
Seeds fake signals for testing the signals API.
Run: python3 scripts/seed_test_signals.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from app.database import db_session
from app.models.signal import Signal
from loguru import logger

TEST_SIGNALS = [
    dict(symbol="RELIANCE", signal_type="BULK_DEAL_UNUSUAL",  score=82,
         title="Block deal: SBI MF BUY 1,20,00,000 shares",
         summary="SBI Mutual Fund bought 1.2Cr shares of RELIANCE. ₹302Cr deal, 3.2x avg vol."),
    dict(symbol="INFY",     signal_type="ORDER_WIN",          score=75,
         title="Order Win detected in press release",
         summary='Filing contains signals: "contract", "awarded", "secured". Deal announced via press release.'),
    dict(symbol="HDFCBANK", signal_type="INSIDER_BUY_CLUSTER", score=78,
         title="2 insiders buy ₹45.2Cr in 7 days",
         summary="Promoter, Director traded buy for HDFCBANK. Total: ₹45.2Cr across 2 transactions."),
    dict(symbol="TCS",      signal_type="RESULTS_BEAT",       score=70,
         title="Results Beat detected in quarterly results",
         summary='Strong PAT beat vs estimates. Keywords: "record", "robust", "growth".'),
    dict(symbol="WIPRO",    signal_type="MANAGEMENT_TONE_POSITIVE", score=55,
         title="Management Tone Positive detected in analyst meet",
         summary='Analyst meet filing contains: "confident", "strong", "optimistic".'),
    dict(symbol="RELIANCE", signal_type="PROMOTER_BUY",       score=88,
         title="Promoter buy ₹1200Cr — stake up 0.8%",
         summary="Mukesh Ambani bought shares worth ₹1200Cr. Holding increased from 48.1% to 48.9%."),
    dict(symbol="TATAMOTORS", signal_type="GUIDANCE_UPGRADE", score=65,
         title="Guidance Upgrade in board meeting outcome",
         summary='Management raised FY26 guidance. Keywords: "upgrade", "upward revision", "positive outlook".'),
    dict(symbol="ICICIBANK", signal_type="BULK_DEAL_UNUSUAL", score=60,
         title="Bulk deal: FPI BUY 80,00,000 shares",
         summary="Foreign Portfolio Investor bought 80L shares of ICICIBANK. ₹128Cr, 2.1x avg vol."),
]

def main():
    with db_session() as session:
        for s in TEST_SIGNALS:
            session.add(Signal(
                **s,
                signal_date=datetime.now(timezone.utc),
                is_active=True,
            ))
    logger.info(f"Seeded {len(TEST_SIGNALS)} test signals")

if __name__ == "__main__":
    main()
