# System Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js)                          │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Opportunity │  │    Chart     │  │  Alert   │  │  Portfolio  │  │
│  │    Radar     │  │  Intelligence│  │  Center  │  │  Watchlist  │  │
│  └─────────────┘  └──────────────┘  └──────────┘  └─────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  REST API + WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐  │
│  │  /signals    │  │  /patterns   │  │  /alerts  │  │  /stocks  │  │
│  │  API routes  │  │  API routes  │  │  API      │  │  API      │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  └─────┬─────┘  │
│         └─────────────────┴────────────────┴──────────────┘        │
│                                    │                                 │
│  ┌──────────────────────────────────▼──────────────────────────┐    │
│  │                     Core Services Layer                      │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐   │    │
│  │  │ Signal Scorer │  │Pattern Detector│  │  Alert Engine  │   │    │
│  │  └───────────────┘  └───────────────┘  └────────────────┘   │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐   │    │
│  │  │  LLM Client   │  │  Backtester   │  │ WebSocket Hub  │   │    │
│  │  └───────────────┘  └───────────────┘  └────────────────┘   │    │
│  └──────────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐   ┌─────────▼──────┐   ┌────────▼───────┐
│  PostgreSQL  │   │     Redis      │   │     Ollama     │
│ +TimescaleDB │   │  Cache + Queue │   │  Llama3.1 8B   │
│  (Storage)   │   │   (Celery)     │   │  (Local LLM)   │
└──────────────┘   └────────────────┘   └────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      Celery Worker Pool                              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Filing       │  │ OHLCV        │  │ Bulk/Block   │               │
│  │ Crawler      │  │ Fetcher      │  │ Deal Fetcher │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Insider      │  │ Results      │  │ Pattern      │               │
│  │ Trade Fetcher│  │ Fetcher      │  │ Scanner      │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     External Data Sources                            │
│                                                                      │
│  NSE India   BSE India   SEBI EDGAR   Screener.in   Yahoo Finance   │
│  (Filings,   (Filings,   (Regulatory  (Fundamentals  (OHLCV         │
│   OHLCV,     Bulk Deals)  Orders)      Quarterly)     Backup)        │
│   Insider)                                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Frontend (Next.js 14)
- Renders Opportunity Radar feed (real-time via WebSocket)
- Renders Chart Intelligence view with pattern overlays
- Manages user watchlists and alert preferences
- Displays backtested stats per pattern per stock

### FastAPI Backend
- Exposes REST endpoints for all data queries
- Manages WebSocket connections for live alerts
- Orchestrates calls to Signal Scorer, Pattern Detector, LLM Client
- Authenticates users (JWT)

### Celery Worker Pool
- Runs scheduled data ingestion jobs (every 15 min to daily)
- Runs pattern scans across full NSE universe (nightly)
- Runs LLM inference jobs for filing analysis
- Pushes results to PostgreSQL and triggers alerts

### Celery Beat (Scheduler)
- Manages all cron schedules for workers
- Config-driven schedule definitions

### PostgreSQL + TimescaleDB
- Stores all OHLCV time-series data (TimescaleDB hypertables)
- Stores filing events, signals, pattern detections, alerts
- Stores backtested stats per pattern per stock

### Redis
- Celery task queue and result backend
- Hot cache for frequently accessed stock data
- WebSocket session state

### Ollama (Local LLM)
- Runs Llama 3.1 8B or Mistral 7B locally
- Used for: filing NLP, management commentary sentiment, pattern explanation
- No API key, no cost, fully offline

### FinBERT (HuggingFace)
- Domain-specific financial sentiment model
- Used for: earnings call transcripts, analyst commentary
- Runs locally via transformers library

---

## Data Flow: Opportunity Radar

```
1. Celery Beat triggers filing_crawler every 15 minutes
2. Crawler checks NSE/BSE/SEBI for new filings since last run
3. New filings stored in raw_filings table with PDF/HTML content
4. NLP worker picks up new filings, runs FinBERT + Ollama
5. Extracted signals (sentiment, keywords, anomalies) scored 0-100
6. High-score signals written to signals table
7. Alert Engine checks user watchlists against new signals
8. Matching alerts pushed via WebSocket to connected clients
9. Daily digest compiled at 8 PM IST and stored for email
```

## Data Flow: Chart Pattern Intelligence

```
1. Celery Beat triggers ohlcv_fetcher nightly for all NSE stocks
2. OHLCV data written to TimescaleDB hypertables
3. Pattern scanner runs TA-Lib + custom detectors on all stocks
4. Detected patterns written to pattern_detections table
5. Backtest engine queries historical patterns, computes stats
6. LLM explains pattern in plain English, stores explanation
7. Frontend queries /patterns/detected for dashboard
8. User selects stock — full chart + pattern overlay + stats served
```

---

## Scalability Notes

- TimescaleDB handles millions of OHLCV rows with automatic partitioning
- Redis caching prevents re-fetching live quotes within 15-min windows
- Celery concurrency can be tuned per machine (default: 4 workers)
- Ollama inference is the bottleneck — batch LLM jobs during off-peak hours
- Pattern scanning is embarrassingly parallel — split NSE universe across workers
