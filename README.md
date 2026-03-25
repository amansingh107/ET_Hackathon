# ET Investor AI — AI Intelligence Layer for the Indian Retail Investor

> Turning ET Markets data into actionable, money-making decisions for India's 14 crore+ demat account holders.

## What This Is

Two AI-powered modules built on top of free, open-source tools:

1. **Opportunity Radar** — A signal-finder, not a summarizer. Continuously monitors corporate filings, quarterly results, bulk/block deals, insider trades, and management commentary to surface missed opportunities as daily alerts.

2. **Chart Pattern Intelligence** — Real-time technical pattern detection across the full NSE universe with plain-English explanations and historical back-tested success rates per pattern per stock.

## Documentation Index

| File | What It Covers |
|---|---|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Full system design, component diagram, data flow |
| [TECH_STACK.md](./docs/TECH_STACK.md) | Every library, tool, and framework used (all free/OSS) |
| [DATA_SOURCES.md](./docs/DATA_SOURCES.md) | All data sources, APIs, scraping targets, update frequencies |
| [DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) | PostgreSQL + TimescaleDB schema with all tables |
| [API_DESIGN.md](./docs/API_DESIGN.md) | All FastAPI endpoints, request/response shapes |
| [MODULE_1_OPPORTUNITY_RADAR.md](./docs/MODULE_1_OPPORTUNITY_RADAR.md) | Opportunity Radar — full build guide |
| [MODULE_2_CHART_PATTERN_INTELLIGENCE.md](./docs/MODULE_2_CHART_PATTERN_INTELLIGENCE.md) | Chart Pattern Intelligence — full build guide |
| [SIGNAL_SCORING.md](./docs/SIGNAL_SCORING.md) | Signal scoring logic, weights, thresholds |
| [LLM_INTEGRATION.md](./docs/LLM_INTEGRATION.md) | Ollama setup, prompt engineering, FinBERT usage |
| [BACKTESTING.md](./docs/BACKTESTING.md) | Backtesting engine design and methodology |
| [FRONTEND.md](./docs/FRONTEND.md) | Next.js frontend structure, pages, components |
| [SETUP.md](./docs/SETUP.md) | Step-by-step local dev environment setup |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Docker Compose, production deployment on free tiers |

## Project Structure

```
et-investor-ai/
├── docs/                          # All documentation (this suite)
├── backend/
│   ├── app/
│   │   ├── api/                   # FastAPI route handlers
│   │   ├── workers/               # Celery async tasks
│   │   ├── signals/               # Opportunity Radar signal engine
│   │   ├── patterns/              # Chart pattern detection
│   │   ├── backtest/              # Backtesting engine
│   │   └── llm/                   # Ollama + FinBERT integration
│   ├── models/                    # SQLAlchemy DB models
│   ├── scheduler/                 # Celery Beat cron config
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   ├── components/
│   └── package.json
├── data/
│   └── nse_universe.csv           # Full NSE stock symbol list
├── docker-compose.yml
└── README.md
```

## Build Order

1. Environment setup → `SETUP.md`
2. Database schema → `DATABASE_SCHEMA.md`
3. Data sources → `DATA_SOURCES.md`
4. Module 1 (Opportunity Radar) → `MODULE_1_OPPORTUNITY_RADAR.md`
5. Module 2 (Chart Patterns) → `MODULE_2_CHART_PATTERN_INTELLIGENCE.md`
6. LLM layer → `LLM_INTEGRATION.md`
7. Frontend → `FRONTEND.md`
8. Deployment → `DEPLOYMENT.md`

## Constraints

- Zero paid services
- Zero paid APIs
- All AI runs locally via Ollama
- All data from public NSE/BSE/SEBI sources
