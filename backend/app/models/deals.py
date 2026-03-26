from sqlalchemy import BigInteger, Column, Date, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BulkBlockDeal(Base):
    __tablename__ = "bulk_block_deals"

    id = Column(BigInteger, primary_key=True)
    deal_date = Column(Date, nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    deal_type = Column(String(10), nullable=False)    # BULK, BLOCK
    client_name = Column(String(255))
    buy_sell = Column(String(4))                      # BUY, SELL
    quantity = Column(BigInteger)
    price = Column(Numeric(10, 2))
    deal_value_cr = Column(Numeric(15, 2))
    avg_volume_30d = Column(BigInteger)
    volume_ratio = Column(Numeric(6, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
