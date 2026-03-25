# Module 1: Opportunity Radar

> A signal-finder, not a summarizer. Surfaces missed opportunities from corporate filings, bulk deals, insider trades, and management commentary.

---

## Overview

The Opportunity Radar continuously monitors multiple data streams, applies scoring logic, runs LLM analysis on text-heavy filings, and surfaces high-confidence signals to users as real-time alerts.

---

## Pipeline Stages

```
[Data Ingestion] → [Text Extraction] → [NLP Analysis] → [Signal Scoring] → [Alert Engine]
```

---

## Stage 1: Data Ingestion Workers

All workers are Celery tasks triggered by Celery Beat.

### File: `backend/app/workers/filing_crawler.py`

```python
"""
Crawls NSE and BSE for new corporate filings every 15 minutes.
Stores raw filings in the corporate_filings table.
"""
import asyncio
import httpx
from celery import shared_task
from app.models import CorporateFiling, db_session

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.nseindia.com/",
    "Accept": "application/json",
}

@shared_task
def crawl_nse_filings():
    """Fetch latest NSE corporate announcements."""
    url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
    async def _fetch():
        async with httpx.AsyncClient(headers=NSE_HEADERS) as client:
            # Warm up cookies
            await client.get("https://www.nseindia.com")
            await asyncio.sleep(2)
            resp = await client.get(url)
            return resp.json()

    data = asyncio.run(_fetch())
    new_count = 0
    with db_session() as session:
        for item in data:
            # Skip if already stored (check by source_id or URL)
            existing = session.query(CorporateFiling).filter_by(
                source="NSE",
                content_url=item.get("attchmntFile")
            ).first()
            if existing:
                continue

            filing = CorporateFiling(
                source="NSE",
                symbol=item.get("symbol"),
                filing_type=item.get("desc"),
                filing_date=item.get("an_dt"),
                subject=item.get("subject"),
                content_url=item.get("attchmntFile"),
                raw_json=item,
                is_processed=False
            )
            session.add(filing)
            new_count += 1
        session.commit()
    return f"Stored {new_count} new NSE filings"


@shared_task
def crawl_bse_filings():
    """Fetch latest BSE corporate announcements."""
    # Similar pattern using BSE API
    # URL: https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
    pass
```

### File: `backend/app/workers/bulk_deals_fetcher.py`

```python
"""
Downloads bulk and block deal data from NSE daily after 4 PM IST.
"""
from celery import shared_task
import httpx
import asyncio
from datetime import date

@shared_task
def fetch_bulk_deals():
    today = date.today().strftime("%d-%m-%Y")
    url = f"https://www.nseindia.com/api/bulk-deals?date={today}"

    async def _fetch():
        async with httpx.AsyncClient(headers=NSE_HEADERS) as client:
            await client.get("https://www.nseindia.com")
            await asyncio.sleep(1.5)
            resp = await client.get(url)
            return resp.json()

    data = asyncio.run(_fetch())
    deals = data.get("data", [])

    with db_session() as session:
        for deal in deals:
            # Compute 30-day average volume for volume_ratio
            avg_vol = get_30d_avg_volume(deal["symbol"])
            qty = int(deal.get("BD_QTY_TRD", 0))

            session.add(BulkBlockDeal(
                deal_date=date.today(),
                symbol=deal["BD_SYMBOL"],
                deal_type="BULK",
                client_name=deal.get("BD_CLIENT_NAME"),
                buy_sell=deal.get("BD_BUY_SELL"),
                quantity=qty,
                price=float(deal.get("BD_TP_VAL", 0)),
                avg_volume_30d=avg_vol,
                volume_ratio=round(qty / avg_vol, 2) if avg_vol else None
            ))
        session.commit()


@shared_task
def fetch_insider_trades():
    """Fetch SEBI PIT (Prohibition of Insider Trading) disclosures from NSE."""
    url = "https://www.nseindia.com/api/corporates-pit?symbol=&from=&to=&type=all"
    # Fetch, parse, store in insider_trades table
    pass
```

---

## Stage 2: Text Extraction

### File: `backend/app/workers/text_extractor.py`

```python
"""
Extracts readable text from PDF and HTML filings.
"""
import pdfplumber
import httpx
from bs4 import BeautifulSoup
from celery import shared_task

@shared_task
def extract_filing_text(filing_id: int):
    """Download and extract text from a filing's attachment."""
    with db_session() as session:
        filing = session.get(CorporateFiling, filing_id)
        if not filing or not filing.content_url:
            return

        url = filing.content_url
        content = httpx.get(url, timeout=30).content

        if url.endswith(".pdf"):
            text = extract_pdf_text(content)
        else:
            text = extract_html_text(content)

        filing.content_text = text[:50000]  # Cap at 50k chars
        session.commit()

    # Trigger NLP analysis
    analyze_filing_nlp.delay(filing_id)


def extract_pdf_text(content: bytes) -> str:
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages[:20]:  # Max 20 pages
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def extract_html_text(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    # Remove scripts, styles, nav
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
```

---

## Stage 3: NLP Analysis

### File: `backend/app/workers/nlp_analyzer.py`

```python
"""
Runs FinBERT sentiment and Ollama LLM extraction on filing text.
"""
from celery import shared_task
from transformers import pipeline
from app.llm.ollama_client import OllamaClient

# Load FinBERT once at module level (downloaded on first use ~440 MB)
finbert = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None
)

ollama = OllamaClient()

@shared_task
def analyze_filing_nlp(filing_id: int):
    with db_session() as session:
        filing = session.get(CorporateFiling, filing_id)
        if not filing or not filing.content_text:
            return

        text = filing.content_text

        # Step 1: FinBERT sentiment on first 512 tokens
        sentiment_results = finbert(text[:2000])
        sentiment = max(sentiment_results[0], key=lambda x: x["score"])

        # Step 2: Ollama signal extraction
        signals = ollama.extract_signals(text, filing.filing_type)

        # Step 3: Score the filing
        score = compute_filing_score(sentiment, signals, filing)

        # Step 4: Create signals
        for signal_data in signals:
            session.add(Signal(
                symbol=filing.symbol,
                signal_type=signal_data["type"],
                score=score,
                title=signal_data["title"],
                summary=signal_data["summary"],
                source_filing_id=filing_id,
                data_json=signal_data
            ))

        filing.is_processed = True
        session.commit()

    # Trigger alert check
    check_alerts_for_new_signal.delay(filing.symbol)


def compute_filing_score(sentiment, signals, filing) -> int:
    """
    Aggregate score 0-100 based on:
    - Sentiment strength
    - Keyword importance (order win, capacity expansion, etc.)
    - Filing type weight
    - Historical context
    """
    base = 0

    # Sentiment contribution (0-30 points)
    if sentiment["label"] == "positive":
        base += int(sentiment["score"] * 30)
    elif sentiment["label"] == "negative":
        base += int(sentiment["score"] * 20)  # Negative = risk signal, also valuable

    # Signal type contribution (0-50 points)
    high_value_keywords = {
        "order": 20, "capacity": 15, "expansion": 15,
        "acquisition": 20, "merger": 20, "guidance": 10,
        "exceptional": 25, "extraordinary": 25, "turnaround": 20
    }
    text_lower = (filing.content_text or "").lower()
    keyword_score = sum(
        v for k, v in high_value_keywords.items() if k in text_lower
    )
    base += min(keyword_score, 50)

    # Filing type weight (0-20 points)
    type_weights = {
        "Quarterly Results": 20,
        "Analyst Meet": 15,
        "Board Meeting": 10,
        "Insider Trading": 18,
        "Credit Rating": 12,
    }
    base += type_weights.get(filing.filing_type, 5)

    return min(base, 100)
```

---

## Stage 4: Bulk Deal Signal Scoring

### File: `backend/app/signals/bulk_deal_scorer.py`

```python
"""
Scores bulk and block deals based on:
- Volume ratio (deal size vs 30-day avg volume)
- Buy vs sell direction
- Known institutional vs retail buyers
- Price vs current market price
"""
from celery import shared_task

VOLUME_RATIO_THRESHOLDS = {
    "extreme": (5.0, 95),   # 5x avg volume → score 95
    "high":    (2.0, 75),   # 2x avg volume → score 75
    "medium":  (1.0, 55),   # 1x avg volume → score 55
    "low":     (0.5, 30),   # 0.5x avg volume → score 30
}

KNOWN_INSTITUTIONS = [
    "MIRAE ASSET", "NIPPON", "SBI MF", "HDFC MF", "AXIS MF",
    "ICICI PRUDENTIAL", "KOTAK MF", "LIC", "GIC", "NPS TRUST",
    "FII", "FPI", "DOMESTIC INSTITUTION"
]

@shared_task
def score_bulk_deals_today():
    with db_session() as session:
        today_deals = session.query(BulkBlockDeal).filter(
            BulkBlockDeal.deal_date == date.today()
        ).all()

        for deal in today_deals:
            score = _score_single_deal(deal)
            if score >= 50:  # Only create signals for meaningful deals
                session.add(Signal(
                    symbol=deal.symbol,
                    signal_type="BULK_DEAL_UNUSUAL",
                    score=score,
                    title=f"{'Bulk' if deal.deal_type == 'BULK' else 'Block'} deal: {deal.client_name} {deal.buy_sell} {deal.quantity:,} shares",
                    summary=_generate_deal_summary(deal, score),
                    data_json={"deal_id": deal.id, "volume_ratio": deal.volume_ratio}
                ))
        session.commit()


def _score_single_deal(deal: BulkBlockDeal) -> int:
    score = 0

    # Volume ratio score
    ratio = deal.volume_ratio or 0
    if ratio >= 5.0:
        score += 50
    elif ratio >= 2.0:
        score += 35
    elif ratio >= 1.0:
        score += 20
    else:
        score += 5

    # Buy deals score higher than sells
    if deal.buy_sell == "BUY":
        score += 20
    else:
        score += 10  # Sells are still signals (risk)

    # Known institution adds confidence
    client_upper = (deal.client_name or "").upper()
    if any(inst in client_upper for inst in KNOWN_INSTITUTIONS):
        score += 15

    # Block deals are more significant than bulk
    if deal.deal_type == "BLOCK":
        score += 10

    return min(score, 100)
```

---

## Stage 5: Insider Trade Signal Scorer

### File: `backend/app/signals/insider_scorer.py`

```python
"""
Detects:
1. Insider buy clusters — multiple insiders buying within 7 days
2. Promoter buying — always a strong signal
3. Unusual sell-off — promoters reducing stake significantly
"""
from datetime import timedelta

@shared_task
def score_insider_trades():
    with db_session() as session:
        # Check for clusters in the past 7 days
        cutoff = date.today() - timedelta(days=7)
        recent = session.query(InsiderTrade).filter(
            InsiderTrade.trade_date >= cutoff,
            InsiderTrade.trade_type == "BUY"
        ).all()

        # Group by symbol
        by_symbol = {}
        for trade in recent:
            by_symbol.setdefault(trade.symbol, []).append(trade)

        for symbol, trades in by_symbol.items():
            if len(trades) >= 2:  # 2+ insiders buying in 7 days
                score = min(50 + len(trades) * 10, 100)
                total_value_cr = sum(
                    (t.quantity * t.price / 1e7) for t in trades
                )
                session.add(Signal(
                    symbol=symbol,
                    signal_type="INSIDER_BUY_CLUSTER",
                    score=score,
                    title=f"{len(trades)} insiders bought ₹{total_value_cr:.1f}Cr worth in 7 days",
                    summary=f"Multiple insiders signal conviction: {', '.join(set(t.acquirer_type for t in trades))}",
                    data_json={"trade_ids": [t.id for t in trades], "total_value_cr": total_value_cr}
                ))
        session.commit()
```

---

## Stage 6: Alert Engine

### File: `backend/app/signals/alert_engine.py`

```python
"""
Matches new signals against user alert rules.
Pushes via WebSocket to connected users.
Queues email digests.
"""
from celery import shared_task
from app.websocket import manager  # WebSocket connection manager

@shared_task
def check_alerts_for_new_signal(symbol: str):
    with db_session() as session:
        # Get latest signal for this symbol
        signal = session.query(Signal).filter_by(
            symbol=symbol
        ).order_by(Signal.created_at.desc()).first()

        if not signal or signal.score < 40:
            return

        # Find users who should receive this alert
        matching_rules = session.query(AlertRule).filter(
            AlertRule.is_active == True,
            AlertRule.min_score <= signal.score,
            (AlertRule.symbol == symbol) | (AlertRule.symbol.is_(None))
        ).all()

        for rule in matching_rules:
            # Check if user watches this symbol
            if rule.symbol is None:  # Global rule — check watchlist
                in_watchlist = session.query(Watchlist).filter_by(
                    user_id=rule.user_id, symbol=symbol
                ).first()
                if not in_watchlist:
                    continue

            # Push WebSocket alert
            asyncio.create_task(
                manager.send_personal_message(
                    user_id=rule.user_id,
                    message={
                        "type": "signal",
                        "symbol": signal.symbol,
                        "score": signal.score,
                        "title": signal.title,
                        "summary": signal.summary,
                        "signal_type": signal.signal_type
                    }
                )
            )

            # Record delivery
            session.add(AlertDelivery(
                user_id=rule.user_id,
                signal_id=signal.id,
                channel="websocket"
            ))
        session.commit()
```

---

## Celery Beat Schedule

### File: `backend/scheduler/schedule.py`

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # Every 15 min during market hours (9 AM - 6 PM IST)
    "crawl-nse-filings": {
        "task": "app.workers.filing_crawler.crawl_nse_filings",
        "schedule": crontab(minute="*/15", hour="9-18"),
    },
    "crawl-bse-filings": {
        "task": "app.workers.filing_crawler.crawl_bse_filings",
        "schedule": crontab(minute="*/15", hour="9-18"),
    },
    # Daily after market close
    "fetch-bulk-deals": {
        "task": "app.workers.bulk_deals_fetcher.fetch_bulk_deals",
        "schedule": crontab(hour=16, minute=30),  # 4:30 PM IST
    },
    "fetch-insider-trades": {
        "task": "app.workers.bulk_deals_fetcher.fetch_insider_trades",
        "schedule": crontab(hour="9,12,15,18", minute=0),
    },
    "score-bulk-deals": {
        "task": "app.signals.bulk_deal_scorer.score_bulk_deals_today",
        "schedule": crontab(hour=17, minute=0),  # 5 PM IST
    },
    "score-insider-trades": {
        "task": "app.signals.insider_scorer.score_insider_trades",
        "schedule": crontab(hour=18, minute=0),
    },
    # Nightly OHLCV refresh
    "fetch-ohlcv-daily": {
        "task": "app.workers.ohlcv_fetcher.fetch_all_daily_ohlcv",
        "schedule": crontab(hour=19, minute=0),  # 7 PM IST
    },
}
```

---

## LLM Extraction Prompt

### File: `backend/app/llm/filing_prompts.py`

```python
FILING_SIGNAL_EXTRACTION_PROMPT = """
You are a financial analyst assistant specialized in Indian stock markets.

Analyze the following corporate filing text and extract actionable signals.

Filing Type: {filing_type}
Company: {symbol}

Filing Text:
{text}

Extract and return a JSON array of signals found in this filing. Each signal should have:
- "type": one of [ORDER_WIN, GUIDANCE_UPGRADE, GUIDANCE_DOWNGRADE, MANAGEMENT_TONE_POSITIVE, MANAGEMENT_TONE_NEGATIVE, FILING_ANOMALY, CAPACITY_EXPANSION, DEBT_REDUCTION, EXCEPTIONAL_ITEM]
- "title": one concise sentence (max 100 chars) describing the signal
- "summary": 2-3 sentences explaining why this matters to an investor
- "confidence": integer 1-10

Rules:
- Only extract signals that are genuinely material to an investor's decision
- Do not summarize; find signals
- If nothing material is found, return an empty array []
- Focus on forward-looking statements, order wins, guidance changes, management tone shifts

Return only valid JSON, no other text.
"""
```
