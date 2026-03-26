from sqlalchemy import Boolean, Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    company_name = Column(String(255), nullable=False)
    isin = Column(String(12), unique=True)
    series = Column(String(5))
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    market_cap_cr = Column(Numeric(15, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
