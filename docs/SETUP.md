# Setup Guide

Step-by-step local development environment setup from zero.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git
- 16 GB RAM recommended (8 GB minimum)

---

## Step 1: Clone and Scaffold

```bash
git clone <repo-url> et-investor-ai
cd et-investor-ai
```

If starting fresh, create the directory structure:
```bash
mkdir -p backend/app/{api,workers,signals,patterns,backtest,llm,models}
mkdir -p backend/scheduler
mkdir -p frontend
mkdir -p data
```

---

## Step 2: Install Ollama and Models

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows — download from https://ollama.com/download and run installer

# Start Ollama server
ollama serve &

# Pull models (run these, they'll download in background)
ollama pull llama3.1:8b        # ~4.7 GB
ollama pull nomic-embed-text   # ~274 MB

# Test it works
curl http://localhost:11434/api/tags
```

---

## Step 3: Start Infrastructure (Docker)

Create `docker-compose.yml`:

```yaml
version: "3.9"

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: etinvestor
      POSTGRES_USER: etuser
      POSTGRES_PASSWORD: etpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  flower:
    image: mher/flower:2.0
    command: celery flower --broker=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

```bash
docker compose up -d
# Verify containers are running
docker compose ps
```

---

## Step 4: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
# OR
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# TA-Lib (special installation)
# Linux/Mac:
sudo apt-get install -y libta-lib-dev  # Ubuntu
pip install TA-Lib

# Windows — download the .whl from:
# https://github.com/cgohlke/talib-build/releases
# Then: pip install TA_Lib-0.4.x-cp311-cp311-win_amd64.whl

# Install Playwright browser
playwright install chromium
```

Create `backend/requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
celery==5.3.6
redis==5.0.4
psycopg2-binary==2.9.9
httpx==0.27.0
beautifulsoup4==4.12.3
playwright==1.44.0
pdfplumber==0.11.1
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# Data
nsepy==0.8.2
nsetools==1.0.11
yfinance==0.2.38
bsedata==1.0.0
pandas==2.2.2
numpy==1.26.4
TA-Lib==0.4.28
pandas-ta==0.3.14b
mplfinance==0.12.10b0
backtesting==0.3.3
scipy==1.13.0
scikit-learn==1.5.0

# LLM / NLP
transformers==4.40.2
torch==2.3.0
sentence-transformers==3.0.0
langchain==0.2.0

# Utilities
pdfplumber==0.11.1
python-dotenv==1.0.1
loguru==0.7.2
```

---

## Step 5: Environment Variables

Create `backend/.env`:
```bash
# Database
DATABASE_URL=postgresql://etuser:etpass@localhost:5432/etinvestor

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# App
DEBUG=true
LOG_LEVEL=INFO
```

---

## Step 6: Database Initialization

```bash
cd backend

# Initialize Alembic
alembic init migrations

# Edit alembic.ini — set sqlalchemy.url to your DATABASE_URL
# Edit migrations/env.py — import your models

# Create initial migration
alembic revision --autogenerate -m "initial schema"

# Run migration
alembic upgrade head

# Verify tables created
docker exec -it et-investor-ai-postgres-1 psql -U etuser -d etinvestor -c "\dt"
```

---

## Step 7: Seed NSE Universe

```bash
cd backend

# Download Nifty 500 list
python -c "
import httpx, csv, io

url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
resp = httpx.get(url, timeout=30)
# Parse and insert into stocks table
print(resp.text[:500])
"

# Or run the seed script
python scripts/seed_universe.py

# Seed 5 years of OHLCV for Nifty 50 (takes ~10-20 min)
python scripts/seed_historical_ohlcv.py --index nifty50

# Run initial backtest suite for Nifty 50 (takes 1-2 hours)
python scripts/run_initial_backtest.py --symbols nifty50
```

---

## Step 8: Start Backend Services

In separate terminals:

```bash
# Terminal 1: FastAPI server
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker (fast tasks)
cd backend
celery -A app.celery_app worker -Q fast,default --concurrency=4 --loglevel=info

# Terminal 3: Celery worker (LLM tasks — single thread)
cd backend
celery -A app.celery_app worker -Q llm --concurrency=1 --loglevel=info

# Terminal 4: Celery Beat (scheduler)
cd backend
celery -A app.celery_app beat --loglevel=info
```

---

## Step 9: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
echo "NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1" >> .env.local

# Start dev server
npm run dev
```

Frontend is now running at `http://localhost:3000`

---

## Step 10: Verify Everything Works

```bash
# API health check
curl http://localhost:8000/api/v1/health

# Test Ollama
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Summarize: Reliance Q3 results strong.", "stream": false}'

# Check Flower (Celery monitoring)
open http://localhost:5555

# Check the frontend
open http://localhost:3000
```

---

## Useful Commands

```bash
# View Celery task queue
celery -A app.celery_app inspect active

# Manually trigger a filing crawl
celery -A app.celery_app call app.workers.filing_crawler.crawl_nse_filings

# Run pattern scan for one stock
celery -A app.celery_app call app.workers.pattern_scanner.scan_stock_patterns --args='["RELIANCE"]'

# Reset and re-run database migrations
alembic downgrade base && alembic upgrade head

# Check DB size
docker exec -it postgres psql -U etuser -d etinvestor -c "
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
"
```
