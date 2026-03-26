from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "et_investor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.ohlcv_fetcher",
        "app.workers.filing_crawler",
        "app.workers.bulk_deals_fetcher",
        "app.signals.bulk_deal_scorer",
        "app.signals.insider_scorer",
        "app.signals.filing_scorer",
        "app.workers.pattern_scanner",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "app.workers.ohlcv_fetcher.*": {"queue": "default"},
        "app.workers.filing_crawler.*": {"queue": "fast"},
        "app.workers.bulk_deals_fetcher.*": {"queue": "fast"},
    },
    beat_schedule={
        # Corp filings — every 15 min during market hours
        "crawl-nse-filings": {
            "task": "app.workers.filing_crawler.crawl_nse_filings",
            "schedule": crontab(minute="*/15", hour="9-18"),
        },
        # Bulk deals — daily at 4:30 PM IST
        "fetch-bulk-deals": {
            "task": "app.workers.bulk_deals_fetcher.fetch_bulk_deals",
            "schedule": crontab(hour=16, minute=30),
        },
        # Insider trades — every 6 hours
        "fetch-insider-trades": {
            "task": "app.workers.bulk_deals_fetcher.fetch_insider_trades",
            "schedule": crontab(hour="9,12,15,18", minute=0),
        },
        # OHLCV — nightly at 7 PM IST
        "fetch-ohlcv-daily": {
            "task": "app.workers.ohlcv_fetcher.fetch_all_daily_ohlcv",
            "schedule": crontab(hour=19, minute=0),
        },
        # Score bulk deals after fetch (5 PM IST)
        "score-bulk-deals": {
            "task": "app.signals.bulk_deal_scorer.score_bulk_deals_today",
            "schedule": crontab(hour=17, minute=0),
        },
        # Score insider trades (6 PM IST)
        "score-insider-trades": {
            "task": "app.signals.insider_scorer.score_insider_trades",
            "schedule": crontab(hour=18, minute=0),
        },
        # Score new filings every 20 min (runs after crawl)
        "score-filings": {
            "task": "app.signals.filing_scorer.score_unprocessed_filings",
            "schedule": crontab(minute="*/20"),
        },
        # Pattern scan nightly at 8 PM IST
        "nightly-pattern-scan": {
            "task": "app.workers.pattern_scanner.scan_all_stocks",
            "schedule": crontab(hour=20, minute=0),
        },
    },
)
