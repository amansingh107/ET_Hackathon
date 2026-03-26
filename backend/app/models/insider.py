from sqlalchemy import BigInteger, Column, Date, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.database import Base


class InsiderTrade(Base):
    __tablename__ = "insider_trades"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    acquirer_name = Column(String(255))
    acquirer_type = Column(String(50))        # Promoter, Director, KMP
    trade_type = Column(String(10))           # BUY, SELL
    security_type = Column(String(50))
    quantity = Column(BigInteger)
    price = Column(Numeric(10, 2))
    trade_date = Column(Date, index=True)
    before_holding_pct = Column(Numeric(6, 3))
    after_holding_pct = Column(Numeric(6, 3))
    filing_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
