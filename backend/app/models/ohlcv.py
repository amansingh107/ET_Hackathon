from sqlalchemy import BigInteger, Column, String, Numeric, DateTime
from app.database import Base


class OHLCVDaily(Base):
    __tablename__ = "ohlcv_daily"

    # TimescaleDB hypertable — composite PK on (time, symbol)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(12, 2))
    high = Column(Numeric(12, 2))
    low = Column(Numeric(12, 2))
    close = Column(Numeric(12, 2))
    volume = Column(BigInteger)
    turnover_cr = Column(Numeric(15, 2))
    delivery_pct = Column(Numeric(5, 2))


class OHLCVIntraday(Base):
    __tablename__ = "ohlcv_intraday"

    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(12, 2))
    high = Column(Numeric(12, 2))
    low = Column(Numeric(12, 2))
    close = Column(Numeric(12, 2))
    volume = Column(BigInteger)
