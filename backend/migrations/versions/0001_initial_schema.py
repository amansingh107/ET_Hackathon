"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- stocks ---
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, unique=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("isin", sa.String(12), unique=True),
        sa.Column("series", sa.String(5)),
        sa.Column("sector", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("market_cap_cr", sa.Numeric(15, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_stocks_symbol", "stocks", ["symbol"])
    op.create_index("idx_stocks_sector", "stocks", ["sector"])

    # --- ohlcv_daily (TimescaleDB hypertable) ---
    op.create_table(
        "ohlcv_daily",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("open", sa.Numeric(12, 2)),
        sa.Column("high", sa.Numeric(12, 2)),
        sa.Column("low", sa.Numeric(12, 2)),
        sa.Column("close", sa.Numeric(12, 2)),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("turnover_cr", sa.Numeric(15, 2)),
        sa.Column("delivery_pct", sa.Numeric(5, 2)),
    )
    op.execute("SELECT create_hypertable('ohlcv_daily', 'time', if_not_exists => TRUE)")
    op.create_index("idx_ohlcv_symbol_time", "ohlcv_daily", ["symbol", sa.text("time DESC")])

    # --- ohlcv_intraday ---
    op.create_table(
        "ohlcv_intraday",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("open", sa.Numeric(12, 2)),
        sa.Column("high", sa.Numeric(12, 2)),
        sa.Column("low", sa.Numeric(12, 2)),
        sa.Column("close", sa.Numeric(12, 2)),
        sa.Column("volume", sa.BigInteger()),
    )
    op.execute("SELECT create_hypertable('ohlcv_intraday', 'time', if_not_exists => TRUE)")
    op.create_index("idx_ohlcv_intra_symbol_time", "ohlcv_intraday", ["symbol", sa.text("time DESC")])

    # --- corporate_filings ---
    op.create_table(
        "corporate_filings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(20)),
        sa.Column("filing_type", sa.String(100), nullable=False),
        sa.Column("filing_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject", sa.Text()),
        sa.Column("content_text", sa.Text()),
        sa.Column("content_url", sa.String(500)),
        sa.Column("raw_json", postgresql.JSONB()),
        sa.Column("is_processed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_filings_symbol", "corporate_filings", ["symbol"])
    op.create_index("idx_filings_date", "corporate_filings", [sa.text("filing_date DESC")])
    op.create_index("idx_filings_type", "corporate_filings", ["filing_type"])
    op.create_index(
        "idx_filings_unprocessed", "corporate_filings", ["is_processed"],
        postgresql_where=sa.text("is_processed = FALSE"),
    )
    op.execute(
        "CREATE INDEX idx_filings_fts ON corporate_filings "
        "USING gin(to_tsvector('english', coalesce(content_text, '')))"
    )

    # --- bulk_block_deals ---
    op.create_table(
        "bulk_block_deals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("deal_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("deal_type", sa.String(10), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("buy_sell", sa.String(4)),
        sa.Column("quantity", sa.BigInteger()),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("deal_value_cr", sa.Numeric(15, 2)),
        sa.Column("avg_volume_30d", sa.BigInteger()),
        sa.Column("volume_ratio", sa.Numeric(6, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_deals_symbol_date", "bulk_block_deals", ["symbol", sa.text("deal_date DESC")])
    op.create_index("idx_deals_volume_ratio", "bulk_block_deals", [sa.text("volume_ratio DESC")])

    # --- insider_trades ---
    op.create_table(
        "insider_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("acquirer_name", sa.String(255)),
        sa.Column("acquirer_type", sa.String(50)),
        sa.Column("trade_type", sa.String(10)),
        sa.Column("security_type", sa.String(50)),
        sa.Column("quantity", sa.BigInteger()),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("trade_date", sa.Date()),
        sa.Column("before_holding_pct", sa.Numeric(6, 3)),
        sa.Column("after_holding_pct", sa.Numeric(6, 3)),
        sa.Column("filing_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_insider_symbol", "insider_trades", ["symbol"])
    op.create_index("idx_insider_date", "insider_trades", [sa.text("trade_date DESC")])

    # --- quarterly_results ---
    op.create_table(
        "quarterly_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quarter", sa.String(10), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("revenue_cr", sa.Numeric(15, 2)),
        sa.Column("ebitda_cr", sa.Numeric(15, 2)),
        sa.Column("pat_cr", sa.Numeric(15, 2)),
        sa.Column("eps", sa.Numeric(10, 2)),
        sa.Column("revenue_growth_yoy", sa.Numeric(6, 2)),
        sa.Column("pat_growth_yoy", sa.Numeric(6, 2)),
        sa.Column("revenue_vs_est", sa.Numeric(6, 2)),
        sa.Column("pat_vs_est", sa.Numeric(6, 2)),
        sa.Column("management_commentary", sa.Text()),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("symbol", "quarter", name="uq_quarterly_results_symbol_quarter"),
    )
    op.create_index("idx_results_symbol", "quarterly_results", ["symbol"])
    op.create_index("idx_results_quarter", "quarterly_results", [sa.text("period_end DESC")])

    # --- signals ---
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("data_json", postgresql.JSONB()),
        sa.Column("source_filing_id", sa.BigInteger(), sa.ForeignKey("corporate_filings.id"), nullable=True),
        sa.Column("signal_date", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_signals_symbol", "signals", ["symbol"])
    op.create_index("idx_signals_date", "signals", [sa.text("signal_date DESC")])
    op.create_index("idx_signals_score", "signals", [sa.text("score DESC")])
    op.create_index("idx_signals_type", "signals", ["signal_type"])

    # --- pattern_detections ---
    op.create_table(
        "pattern_detections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("pattern_name", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pattern_start", sa.Date()),
        sa.Column("pattern_end", sa.Date()),
        sa.Column("entry_price", sa.Numeric(10, 2)),
        sa.Column("target_price", sa.Numeric(10, 2)),
        sa.Column("stop_loss", sa.Numeric(10, 2)),
        sa.Column("confidence_score", sa.SmallInteger()),
        sa.Column("volume_confirmation", sa.Boolean()),
        sa.Column("plain_english", sa.Text()),
        sa.Column("backtest_win_rate", sa.Numeric(5, 2)),
        sa.Column("backtest_avg_gain", sa.Numeric(6, 2)),
        sa.Column("backtest_avg_loss", sa.Numeric(6, 2)),
        sa.Column("backtest_sample_size", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_patterns_symbol", "pattern_detections", ["symbol"])
    op.create_index("idx_patterns_detected", "pattern_detections", [sa.text("detected_at DESC")])
    op.create_index("idx_patterns_name", "pattern_detections", ["pattern_name"])
    op.create_index("idx_patterns_confidence", "pattern_detections", [sa.text("confidence_score DESC")])

    # --- pattern_backtest_stats ---
    op.create_table(
        "pattern_backtest_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("pattern_name", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("sample_size", sa.Integer()),
        sa.Column("win_rate", sa.Numeric(5, 2)),
        sa.Column("avg_gain_pct", sa.Numeric(6, 2)),
        sa.Column("avg_loss_pct", sa.Numeric(6, 2)),
        sa.Column("avg_holding_days", sa.Integer()),
        sa.Column("best_gain_pct", sa.Numeric(6, 2)),
        sa.Column("worst_loss_pct", sa.Numeric(6, 2)),
        sa.Column("last_computed", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("symbol", "pattern_name", "timeframe", name="uq_backtest_stats"),
    )
    op.create_index("idx_backtest_stats_symbol", "pattern_backtest_stats", ["symbol", "pattern_name"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # --- watchlists ---
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    # --- alert_rules ---
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20)),
        sa.Column("min_score", sa.SmallInteger(), server_default=sa.text("50")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # --- alert_deliveries ---
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("signal_id", sa.BigInteger(), sa.ForeignKey("signals.id"), nullable=True),
        sa.Column("channel", sa.String(20)),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("was_read", sa.Boolean(), server_default=sa.text("false")),
    )

    # --- Useful views ---
    op.execute("""
        CREATE VIEW recent_signals AS
        SELECT s.*, st.sector, st.industry
        FROM signals s
        JOIN stocks st ON s.symbol = st.symbol
        WHERE s.signal_date > NOW() - INTERVAL '24 hours'
        ORDER BY s.score DESC
    """)

    op.execute("""
        CREATE VIEW today_patterns AS
        SELECT pd.*, st.sector, st.company_name,
               pbs.win_rate, pbs.avg_gain_pct
        FROM pattern_detections pd
        JOIN stocks st ON pd.symbol = st.symbol
        LEFT JOIN pattern_backtest_stats pbs
            ON pd.symbol = pbs.symbol
            AND pd.pattern_name = pbs.pattern_name
            AND pd.timeframe = pbs.timeframe
        WHERE pd.detected_at > NOW() - INTERVAL '24 hours'
        ORDER BY pd.confidence_score DESC
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS today_patterns")
    op.execute("DROP VIEW IF EXISTS recent_signals")
    op.drop_table("alert_deliveries")
    op.drop_table("alert_rules")
    op.drop_table("watchlists")
    op.drop_table("users")
    op.drop_table("pattern_backtest_stats")
    op.drop_table("pattern_detections")
    op.drop_table("signals")
    op.drop_table("quarterly_results")
    op.drop_table("insider_trades")
    op.drop_table("bulk_block_deals")
    op.drop_table("corporate_filings")
    op.drop_table("ohlcv_intraday")
    op.drop_table("ohlcv_daily")
    op.drop_table("stocks")
