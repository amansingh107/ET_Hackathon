"""
Manual trigger endpoints for data ingestion tasks.
Useful for testing without waiting for Celery Beat.
"""
from fastapi import APIRouter, BackgroundTasks
from app.workers.filing_crawler import crawl_nse_filings
from app.workers.bulk_deals_fetcher import fetch_bulk_deals, fetch_insider_trades
from app.workers.ohlcv_fetcher import fetch_stock_ohlcv
from app.signals.bulk_deal_scorer import score_bulk_deals_today
from app.signals.insider_scorer import score_insider_trades
from app.signals.filing_scorer import score_unprocessed_filings

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/filings/nse")
def trigger_nse_filings():
    """Manually trigger NSE filing crawl (runs as Celery task)."""
    task = crawl_nse_filings.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/deals/bulk")
def trigger_bulk_deals():
    """Manually trigger bulk/block deals fetch."""
    task = fetch_bulk_deals.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/insider-trades")
def trigger_insider_trades():
    """Manually trigger insider trades fetch."""
    task = fetch_insider_trades.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/ohlcv/{symbol}")
def trigger_ohlcv(symbol: str, days: int = 30):
    """Manually trigger OHLCV fetch for a single stock."""
    task = fetch_stock_ohlcv.apply_async(args=[symbol.upper(), days])
    return {"task_id": task.id, "status": "queued", "symbol": symbol.upper()}


# --- Signal scoring triggers ---

@router.post("/score/bulk-deals")
def trigger_score_bulk_deals():
    task = score_bulk_deals_today.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/score/insider-trades")
def trigger_score_insider_trades():
    task = score_insider_trades.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/score/filings")
def trigger_score_filings(batch_size: int = 50):
    task = score_unprocessed_filings.delay(batch_size)
    return {"task_id": task.id, "status": "queued"}


# --- Sync versions (run inline, no Celery worker needed) ---

@router.post("/score/filings/sync")
def trigger_score_filings_sync(batch_size: int = 50):
    """Score filings synchronously — no Celery worker needed."""
    result = score_unprocessed_filings(batch_size)
    return {"result": result}


@router.post("/score/insider-trades/sync")
def trigger_score_insider_sync():
    result = score_insider_trades()
    return {"result": result}


@router.post("/score/bulk-deals/sync")
def trigger_score_bulk_sync():
    result = score_bulk_deals_today()
    return {"result": result}


@router.post("/patterns/scan/{symbol}")
def trigger_pattern_scan(symbol: str):
    """Scan a single stock for patterns (sync, no Celery needed)."""
    from app.workers.pattern_scanner import scan_stock_patterns
    result = scan_stock_patterns(symbol.upper())
    return {"result": result}


@router.post("/patterns/scan-all")
def trigger_scan_all():
    from app.workers.pattern_scanner import scan_all_stocks
    task = scan_all_stocks.delay()
    return {"task_id": task.id, "status": "queued"}
