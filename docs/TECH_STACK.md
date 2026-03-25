# Technology Stack

Everything listed here is free and open-source.

---

## Backend

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Primary backend language |
| FastAPI | 0.111+ | REST API framework, async, WebSocket support |
| SQLAlchemy | 2.0+ | ORM for PostgreSQL |
| Alembic | 1.13+ | Database migrations |
| Celery | 5.3+ | Distributed task queue |
| Celery Beat | 5.3+ | Cron-style task scheduler |
| Pydantic | 2.0+ | Data validation and serialization |
| python-jose | 3.3+ | JWT authentication |
| passlib | 1.7+ | Password hashing |
| httpx | 0.27+ | Async HTTP client for scraping/APIs |
| BeautifulSoup4 | 4.12+ | HTML parsing for scrapers |
| Playwright | 1.44+ | Browser automation for JS-heavy pages |
| pdfplumber | 0.11+ | Extract text from SEBI/BSE PDF filings |
| python-multipart | 0.0.9+ | File upload handling |

## Data & Finance Libraries

| Tool | Version | Purpose |
|---|---|---|
| nsepy | 0.8+ | NSE India historical OHLCV data |
| nsetools | 1.0+ | NSE live quotes, market status |
| yfinance | 0.2+ | Yahoo Finance OHLCV (backup source) |
| bsedata | 1.0+ | BSE India corporate data |
| pandas | 2.2+ | Data manipulation |
| numpy | 1.26+ | Numerical computation |
| TA-Lib | 0.4+ | 150+ technical indicators and candlestick patterns |
| pandas-ta | 0.3+ | Pure Python TA alternative (no C deps) |
| mplfinance | 0.12+ | Candlestick chart generation |
| backtesting.py | 0.3+ | Backtesting framework |
| scipy | 1.13+ | Peak detection (support/resistance) |
| scikit-learn | 1.5+ | ML clustering for S/R zones |

## AI / LLM

| Tool | Version | Purpose |
|---|---|---|
| Ollama | Latest | Local LLM runtime (zero cost) |
| Llama 3.1 8B | Latest | General filing analysis, pattern explanation |
| Mistral 7B | Latest | Lightweight alternative if RAM < 16 GB |
| transformers | 4.40+ | HuggingFace model runner |
| FinBERT | ProsusAI | Financial sentiment classification |
| sentence-transformers | 3.0+ | Semantic search over filings |
| LangChain | 0.2+ | LLM chain orchestration |

## Database

| Tool | Version | Purpose |
|---|---|---|
| PostgreSQL | 16+ | Primary relational database |
| TimescaleDB | 2.15+ | Time-series extension for OHLCV data |
| Redis | 7.2+ | Celery broker, result backend, cache |
| psycopg2-binary | 2.9+ | PostgreSQL Python driver |
| redis-py | 5.0+ | Redis Python client |

## Frontend

| Tool | Version | Purpose |
|---|---|---|
| Next.js | 14+ | React framework (App Router) |
| React | 18+ | UI library |
| TypeScript | 5.4+ | Type safety |
| TailwindCSS | 3.4+ | Utility-first CSS |
| TradingView Lightweight Charts | 4.1+ | High-performance financial charts (free) |
| Recharts | 2.12+ | General charts (signal scores, stats) |
| SWR | 2.2+ | Data fetching and caching |
| Zustand | 4.5+ | Global state management |
| socket.io-client | 4.7+ | WebSocket for live alerts |

## DevOps / Infrastructure

| Tool | Version | Purpose |
|---|---|---|
| Docker | 24+ | Containerization |
| Docker Compose | 2.27+ | Multi-service orchestration |
| Nginx | 1.26+ | Reverse proxy |
| Flower | 2.0+ | Celery task monitoring UI |

---

## Installation Notes

### TA-Lib on Windows
TA-Lib has C dependencies. Use the pre-built wheel:
```bash
pip install TA-Lib --find-links https://github.com/cgohlke/talib-build/releases
```

### TA-Lib on Linux/Mac
```bash
# Ubuntu
sudo apt-get install libta-lib-dev
pip install TA-Lib

# Mac
brew install ta-lib
pip install TA-Lib
```

### Ollama Setup
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1:8b       # ~4.7 GB — recommended
ollama pull mistral:7b         # ~4.1 GB — if RAM-constrained
ollama pull nomic-embed-text   # ~274 MB — for embeddings
```

### Playwright Setup
```bash
pip install playwright
playwright install chromium
```

### FinBERT Setup
```python
# First run will download the model (~440 MB)
from transformers import pipeline
sentiment = pipeline("text-classification", model="ProsusAI/finbert")
```

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 20 GB | 50 GB |
| GPU | Not required | NVIDIA (speeds Ollama 5-10x) |

> With 8 GB RAM: use `mistral:7b` instead of `llama3.1:8b`. Both give excellent results.
