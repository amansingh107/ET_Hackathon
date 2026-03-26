from sqlalchemy import BigInteger, Column, Date, String, Numeric, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class QuarterlyResult(Base):
    __tablename__ = "quarterly_results"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    quarter = Column(String(10), nullable=False)      # Q3FY25
    period_end = Column(Date, nullable=False, index=True)
    revenue_cr = Column(Numeric(15, 2))
    ebitda_cr = Column(Numeric(15, 2))
    pat_cr = Column(Numeric(15, 2))
    eps = Column(Numeric(10, 2))
    revenue_growth_yoy = Column(Numeric(6, 2))
    pat_growth_yoy = Column(Numeric(6, 2))
    revenue_vs_est = Column(Numeric(6, 2))
    pat_vs_est = Column(Numeric(6, 2))
    management_commentary = Column(Text)
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "quarter", name="uq_quarterly_results_symbol_quarter"),
    )
