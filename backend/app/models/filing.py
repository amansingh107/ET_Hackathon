from sqlalchemy import BigInteger, Boolean, Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class CorporateFiling(Base):
    __tablename__ = "corporate_filings"

    id = Column(BigInteger, primary_key=True)
    source = Column(String(10), nullable=False)       # NSE, BSE, SEBI
    symbol = Column(String(20), index=True)
    filing_type = Column(String(100), nullable=False, index=True)
    filing_date = Column(DateTime(timezone=True), nullable=False, index=True)
    subject = Column(Text)
    content_text = Column(Text)
    content_url = Column(String(500))
    raw_json = Column(JSONB)
    is_processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
