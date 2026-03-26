from sqlalchemy import Boolean, Column, Date, Integer, SmallInteger, String, Numeric, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

PATTERN_NAMES = [
    "BREAKOUT_52W_HIGH", "BREAKOUT_RESISTANCE", "BREAKDOWN_52W_LOW", "BREAKDOWN_SUPPORT",
    "BULLISH_ENGULFING", "BEARISH_ENGULFING", "HAMMER", "SHOOTING_STAR", "DOJI",
    "MORNING_STAR", "EVENING_STAR", "THREE_WHITE_SOLDIERS", "THREE_BLACK_CROWS",
    "CUP_AND_HANDLE", "HEAD_AND_SHOULDERS", "INVERSE_HEAD_SHOULDERS",
    "DOUBLE_TOP", "DOUBLE_BOTTOM", "ASCENDING_TRIANGLE", "DESCENDING_TRIANGLE",
    "SYMMETRICAL_TRIANGLE", "BULLISH_DIVERGENCE_RSI", "BEARISH_DIVERGENCE_RSI",
    "BULLISH_DIVERGENCE_MACD", "BEARISH_DIVERGENCE_MACD", "GOLDEN_CROSS", "DEATH_CROSS",
]


class PatternDetection(Base):
    __tablename__ = "pattern_detections"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    pattern_name = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False)     # 1D, 1W, 1M
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    pattern_start = Column(Date)
    pattern_end = Column(Date)
    entry_price = Column(Numeric(10, 2))
    target_price = Column(Numeric(10, 2))
    stop_loss = Column(Numeric(10, 2))
    confidence_score = Column(SmallInteger, index=True)
    volume_confirmation = Column(Boolean)
    plain_english = Column(Text)
    backtest_win_rate = Column(Numeric(5, 2))
    backtest_avg_gain = Column(Numeric(6, 2))
    backtest_avg_loss = Column(Numeric(6, 2))
    backtest_sample_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatternBacktestStats(Base):
    __tablename__ = "pattern_backtest_stats"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    pattern_name = Column(String(50), nullable=False)
    timeframe = Column(String(5), nullable=False)
    sample_size = Column(Integer)
    win_rate = Column(Numeric(5, 2))
    avg_gain_pct = Column(Numeric(6, 2))
    avg_loss_pct = Column(Numeric(6, 2))
    avg_holding_days = Column(Integer)
    best_gain_pct = Column(Numeric(6, 2))
    worst_loss_pct = Column(Numeric(6, 2))
    last_computed = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "pattern_name", "timeframe", name="uq_backtest_stats"),
    )
