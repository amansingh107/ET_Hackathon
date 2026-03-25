# Database Schema

Uses PostgreSQL 16 with the TimescaleDB extension for time-series data.

---

## Setup

```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable trigram search for filing text
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## Tables

### 1. stocks

Master list of all NSE-listed stocks.

```sql
CREATE TABLE stocks (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL UNIQUE,
    company_name    VARCHAR(255) NOT NULL,
    isin            VARCHAR(12) UNIQUE,
    series          VARCHAR(5),           -- EQ, BE, etc.
    sector          VARCHAR(100),
    industry        VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    market_cap_cr   NUMERIC(15,2),        -- crores
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_sector ON stocks(sector);
```

---

### 2. ohlcv_daily

Daily OHLCV data. TimescaleDB hypertable partitioned by time.

```sql
CREATE TABLE ohlcv_daily (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    open            NUMERIC(12,2),
    high            NUMERIC(12,2),
    low             NUMERIC(12,2),
    close           NUMERIC(12,2),
    volume          BIGINT,
    turnover_cr     NUMERIC(15,2),
    delivery_pct    NUMERIC(5,2),         -- % of volume delivered
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('ohlcv_daily', 'time');

-- Compound index for fast per-symbol queries
CREATE INDEX idx_ohlcv_symbol_time ON ohlcv_daily(symbol, time DESC);

-- Compression policy: compress chunks older than 30 days
SELECT add_compression_policy('ohlcv_daily', INTERVAL '30 days');
```

---

### 3. ohlcv_intraday

15-minute OHLCV. Retained for 90 days, then dropped.

```sql
CREATE TABLE ohlcv_intraday (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    open            NUMERIC(12,2),
    high            NUMERIC(12,2),
    low             NUMERIC(12,2),
    close           NUMERIC(12,2),
    volume          BIGINT
);

SELECT create_hypertable('ohlcv_intraday', 'time');
CREATE INDEX idx_ohlcv_intra_symbol_time ON ohlcv_intraday(symbol, time DESC);

-- Auto-drop chunks older than 90 days
SELECT add_retention_policy('ohlcv_intraday', INTERVAL '90 days');
```

---

### 4. corporate_filings

Raw corporate filings from NSE, BSE, and SEBI.

```sql
CREATE TABLE corporate_filings (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(10) NOT NULL,  -- 'NSE', 'BSE', 'SEBI'
    symbol          VARCHAR(20),
    filing_type     VARCHAR(100) NOT NULL, -- 'Quarterly Results', 'Insider Trading', etc.
    filing_date     TIMESTAMPTZ NOT NULL,
    subject         TEXT,
    content_text    TEXT,                  -- Extracted text from PDF/HTML
    content_url     VARCHAR(500),          -- Original filing URL
    raw_json        JSONB,                 -- Original API response
    is_processed    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_filings_symbol ON corporate_filings(symbol);
CREATE INDEX idx_filings_date ON corporate_filings(filing_date DESC);
CREATE INDEX idx_filings_type ON corporate_filings(filing_type);
CREATE INDEX idx_filings_unprocessed ON corporate_filings(is_processed) WHERE is_processed = FALSE;

-- Full-text search on filing content
CREATE INDEX idx_filings_fts ON corporate_filings USING gin(to_tsvector('english', coalesce(content_text, '')));
```

---

### 5. bulk_block_deals

Bulk and block deal transactions.

```sql
CREATE TABLE bulk_block_deals (
    id              BIGSERIAL PRIMARY KEY,
    deal_date       DATE NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    deal_type       VARCHAR(10) NOT NULL,  -- 'BULK', 'BLOCK'
    client_name     VARCHAR(255),
    buy_sell        VARCHAR(4),            -- 'BUY', 'SELL'
    quantity        BIGINT,
    price           NUMERIC(10,2),
    deal_value_cr   NUMERIC(15,2),         -- quantity * price / 1e7
    avg_volume_30d  BIGINT,               -- populated post-insert
    volume_ratio    NUMERIC(6,2),          -- deal qty / avg_volume_30d
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deals_symbol_date ON bulk_block_deals(symbol, deal_date DESC);
CREATE INDEX idx_deals_volume_ratio ON bulk_block_deals(volume_ratio DESC);
```

---

### 6. insider_trades

NSE Prohibition of Insider Trading (PIT) disclosures.

```sql
CREATE TABLE insider_trades (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    acquirer_name   VARCHAR(255),
    acquirer_type   VARCHAR(50),           -- 'Promoter', 'Director', 'KMP'
    trade_type      VARCHAR(10),           -- 'BUY', 'SELL'
    security_type   VARCHAR(50),
    quantity        BIGINT,
    price           NUMERIC(10,2),
    trade_date      DATE,
    before_holding_pct  NUMERIC(6,3),
    after_holding_pct   NUMERIC(6,3),
    filing_date     DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insider_symbol ON insider_trades(symbol);
CREATE INDEX idx_insider_date ON insider_trades(trade_date DESC);
```

---

### 7. quarterly_results

Parsed quarterly earnings data.

```sql
CREATE TABLE quarterly_results (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    quarter         VARCHAR(10) NOT NULL,  -- 'Q3FY25'
    period_end      DATE NOT NULL,
    revenue_cr      NUMERIC(15,2),
    ebitda_cr       NUMERIC(15,2),
    pat_cr          NUMERIC(15,2),         -- Profit After Tax
    eps             NUMERIC(10,2),
    revenue_growth_yoy  NUMERIC(6,2),      -- %
    pat_growth_yoy      NUMERIC(6,2),      -- %
    revenue_vs_est      NUMERIC(6,2),      -- % beat/miss vs estimate
    pat_vs_est          NUMERIC(6,2),
    management_commentary TEXT,
    source          VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, quarter)
);

CREATE INDEX idx_results_symbol ON quarterly_results(symbol);
CREATE INDEX idx_results_quarter ON quarterly_results(period_end DESC);
```

---

### 8. signals

Scored signals from the Opportunity Radar engine.

```sql
CREATE TYPE signal_type AS ENUM (
    'BULK_DEAL_UNUSUAL',
    'INSIDER_BUY_CLUSTER',
    'INSIDER_SELL_CLUSTER',
    'RESULTS_BEAT',
    'RESULTS_MISS',
    'GUIDANCE_UPGRADE',
    'GUIDANCE_DOWNGRADE',
    'ORDER_WIN',
    'FILING_ANOMALY',
    'REGULATORY_ACTION',
    'MANAGEMENT_TONE_POSITIVE',
    'MANAGEMENT_TONE_NEGATIVE',
    'PROMOTER_BUY',
    'PROMOTER_SELL'
);

CREATE TABLE signals (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    signal_type     signal_type NOT NULL,
    score           SMALLINT NOT NULL,     -- 0-100
    title           VARCHAR(255) NOT NULL,
    summary         TEXT,                  -- LLM-generated plain English summary
    data_json       JSONB,                 -- Raw signal data
    source_filing_id BIGINT REFERENCES corporate_filings(id),
    signal_date     TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_date ON signals(signal_date DESC);
CREATE INDEX idx_signals_score ON signals(score DESC);
CREATE INDEX idx_signals_type ON signals(signal_type);
```

---

### 9. pattern_detections

Chart pattern detections from the Pattern Intelligence engine.

```sql
CREATE TYPE pattern_name AS ENUM (
    'BREAKOUT_52W_HIGH',
    'BREAKOUT_RESISTANCE',
    'BREAKDOWN_52W_LOW',
    'BREAKDOWN_SUPPORT',
    'BULLISH_ENGULFING',
    'BEARISH_ENGULFING',
    'HAMMER',
    'SHOOTING_STAR',
    'DOJI',
    'MORNING_STAR',
    'EVENING_STAR',
    'THREE_WHITE_SOLDIERS',
    'THREE_BLACK_CROWS',
    'CUP_AND_HANDLE',
    'HEAD_AND_SHOULDERS',
    'INVERSE_HEAD_SHOULDERS',
    'DOUBLE_TOP',
    'DOUBLE_BOTTOM',
    'ASCENDING_TRIANGLE',
    'DESCENDING_TRIANGLE',
    'SYMMETRICAL_TRIANGLE',
    'BULLISH_DIVERGENCE_RSI',
    'BEARISH_DIVERGENCE_RSI',
    'BULLISH_DIVERGENCE_MACD',
    'BEARISH_DIVERGENCE_MACD',
    'GOLDEN_CROSS',
    'DEATH_CROSS'
);

CREATE TABLE pattern_detections (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    pattern_name    pattern_name NOT NULL,
    timeframe       VARCHAR(5) NOT NULL,   -- '1D', '1W', '1M'
    detected_at     TIMESTAMPTZ NOT NULL,
    pattern_start   DATE,
    pattern_end     DATE,
    entry_price     NUMERIC(10,2),
    target_price    NUMERIC(10,2),
    stop_loss       NUMERIC(10,2),
    confidence_score SMALLINT,             -- 0-100
    volume_confirmation BOOLEAN,
    plain_english   TEXT,                  -- Ollama-generated explanation
    backtest_win_rate   NUMERIC(5,2),      -- % from historical analysis
    backtest_avg_gain   NUMERIC(6,2),      -- % average gain when pattern wins
    backtest_avg_loss   NUMERIC(6,2),      -- % average loss when pattern loses
    backtest_sample_size INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_symbol ON pattern_detections(symbol);
CREATE INDEX idx_patterns_detected ON pattern_detections(detected_at DESC);
CREATE INDEX idx_patterns_name ON pattern_detections(pattern_name);
CREATE INDEX idx_patterns_confidence ON pattern_detections(confidence_score DESC);
```

---

### 10. pattern_backtest_stats

Pre-computed backtest stats per (pattern, symbol, timeframe).

```sql
CREATE TABLE pattern_backtest_stats (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    pattern_name    pattern_name NOT NULL,
    timeframe       VARCHAR(5) NOT NULL,
    sample_size     INT,
    win_rate        NUMERIC(5,2),          -- %
    avg_gain_pct    NUMERIC(6,2),
    avg_loss_pct    NUMERIC(6,2),
    avg_holding_days INT,
    best_gain_pct   NUMERIC(6,2),
    worst_loss_pct  NUMERIC(6,2),
    last_computed   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, pattern_name, timeframe)
);

CREATE INDEX idx_backtest_stats_symbol ON pattern_backtest_stats(symbol, pattern_name);
```

---

### 11. users

Application users and their preferences.

```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 12. watchlists

User stock watchlists.

```sql
CREATE TABLE watchlists (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol      VARCHAR(20) NOT NULL,
    added_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, symbol)
);
```

---

### 13. alert_rules

User-configured alert thresholds.

```sql
CREATE TABLE alert_rules (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol          VARCHAR(20),           -- NULL = all stocks
    signal_types    signal_type[],         -- NULL = all types
    min_score       SMALLINT DEFAULT 50,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 14. alert_deliveries

Record of alerts sent to users.

```sql
CREATE TABLE alert_deliveries (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id),
    signal_id   BIGINT REFERENCES signals(id),
    channel     VARCHAR(20),               -- 'websocket', 'email'
    delivered_at TIMESTAMPTZ DEFAULT NOW(),
    was_read    BOOLEAN DEFAULT FALSE
);
```

---

## Useful Views

```sql
-- Top signals in the last 24 hours
CREATE VIEW recent_signals AS
SELECT s.*, st.sector, st.industry
FROM signals s
JOIN stocks st ON s.symbol = st.symbol
WHERE s.signal_date > NOW() - INTERVAL '24 hours'
ORDER BY s.score DESC;

-- Latest patterns detected today
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
ORDER BY pd.confidence_score DESC;
```
