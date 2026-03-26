from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, SmallInteger, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base

# Signal types as a plain string column (Enum defined via Alembic migration)
SIGNAL_TYPES = [
    "BULK_DEAL_UNUSUAL",
    "INSIDER_BUY_CLUSTER",
    "INSIDER_SELL_CLUSTER",
    "RESULTS_BEAT",
    "RESULTS_MISS",
    "GUIDANCE_UPGRADE",
    "GUIDANCE_DOWNGRADE",
    "ORDER_WIN",
    "FILING_ANOMALY",
    "REGULATORY_ACTION",
    "MANAGEMENT_TONE_POSITIVE",
    "MANAGEMENT_TONE_NEGATIVE",
    "PROMOTER_BUY",
    "PROMOTER_SELL",
]


class Signal(Base):
    __tablename__ = "signals"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)
    score = Column(SmallInteger, nullable=False)           # 0-100
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    data_json = Column(JSONB)
    source_filing_id = Column(BigInteger, ForeignKey("corporate_filings.id"), nullable=True)
    signal_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
