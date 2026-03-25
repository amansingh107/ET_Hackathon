# Deployment

All free-tier deployment options. No credit card required.

---

## Option A: Single Machine (Recommended for Hackathon)

Run everything on one machine using Docker Compose. Best for demo/hackathon — easiest to control and debug.

### Full `docker-compose.yml`

```yaml
version: "3.9"

services:
  # ─── Infrastructure ───────────────────────────────────────
  postgres:
    image: timescale/timescaledb:latest-pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: etinvestor
      POSTGRES_USER: etuser
      POSTGRES_PASSWORD: etpass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U etuser -d etinvestor"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  # ─── Backend ──────────────────────────────────────────────
  api:
    build: ./backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://etuser:etpass@postgres:5432/etinvestor
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker-fast:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://etuser:etpass@postgres:5432/etinvestor
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    depends_on:
      - postgres
      - redis
    command: celery -A app.celery_app worker -Q fast,default --concurrency=4

  worker-llm:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://etuser:etpass@postgres:5432/etinvestor
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    depends_on:
      - postgres
      - redis
    command: celery -A app.celery_app worker -Q llm --concurrency=1

  beat:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://etuser:etpass@postgres:5432/etinvestor
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A app.celery_app beat --loglevel=info

  flower:
    image: mher/flower:2.0
    restart: unless-stopped
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/0
    depends_on:
      - redis

  # ─── Frontend ─────────────────────────────────────────────
  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
      NEXT_PUBLIC_WS_URL: ws://localhost:8000/api/v1

  # ─── Reverse Proxy ────────────────────────────────────────
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - api
      - frontend

volumes:
  postgres_data:
  redis_data:
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for TA-Lib
RUN apt-get update && apt-get install -y \
    gcc g++ make libta-lib-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### `nginx.conf`

```nginx
server {
    listen 80;

    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
    }
}
```

### Deploy

```bash
# Build and start everything
docker compose up -d --build

# Run DB migrations
docker compose exec api alembic upgrade head

# Seed initial data
docker compose exec api python scripts/seed_universe.py
docker compose exec api python scripts/seed_historical_ohlcv.py

# View logs
docker compose logs -f api
docker compose logs -f worker-fast
```

---

## Option B: Free Cloud Deployment

If you need the app publicly accessible:

### Backend — Railway (free tier)
```
https://railway.app
- Deploy backend as a service (connect GitHub repo)
- Add PostgreSQL plugin (free 500 MB)
- Add Redis plugin (free)
- Set environment variables in Railway dashboard
- Free tier: 500 hours/month, $5 credit
```

### Frontend — Vercel (free tier)
```
https://vercel.com
- Import Next.js project from GitHub
- Set NEXT_PUBLIC_API_URL to Railway backend URL
- Unlimited deployments on free tier
```

### LLM — NOT deployable on free cloud
```
Ollama requires a real machine with RAM.
For demo: run Ollama locally and expose via ngrok:
  ngrok http 11434

Set OLLAMA_BASE_URL to your ngrok URL in the deployed backend.
```

---

## Production Considerations

### Database Backups
```bash
# Daily backup script
pg_dump -U etuser -d etinvestor -Fc > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -U etuser -d etinvestor backup_20260325.dump
```

### Monitoring
```
- Flower UI: http://localhost:5555 (Celery tasks)
- FastAPI docs: http://localhost:8000/docs (Swagger UI)
- TimescaleDB dashboard: use pgAdmin (free)
```

### Environment-Specific Config
```bash
# Development
DEBUG=true
LOG_LEVEL=DEBUG

# Production
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=<long-random-string>
```

### NSE Scraping in Production
```python
# Use a rotating delay to avoid IP blocks
import random, asyncio

async def polite_fetch(url):
    await asyncio.sleep(random.uniform(2, 5))  # 2-5s delay
    return await fetch(url)
```
