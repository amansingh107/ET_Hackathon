"""
Fetches NSE bulk deals, block deals, and insider trades.
"""
import asyncio
import random
from datetime import date, datetime, timezone

import httpx
from loguru import logger
from sqlalchemy import func

from app.celery_app import celery_app
from app.database import db_session
from app.models.deals import BulkBlockDeal
from app.models.insider import InsiderTrade
from app.models.ohlcv import OHLCVDaily

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


async def _nse_get(url: str) -> dict | list:
    async with httpx.AsyncClient(headers=NSE_HEADERS, timeout=30, follow_redirects=True) as client:
        await client.get("https://www.nseindia.com")
        await asyncio.sleep(random.uniform(1.5, 3.0))
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def _get_30d_avg_volume(session, symbol: str) -> int | None:
    """Fetch 30-day average volume from ohlcv_daily."""
    result = session.query(func.avg(OHLCVDaily.volume)).filter(
        OHLCVDaily.symbol == symbol,
    ).scalar()
    return int(result) if result else None


@celery_app.task(name="app.workers.bulk_deals_fetcher.fetch_bulk_deals")
def fetch_bulk_deals():
    """Fetch today's bulk and block deals from NSE."""
    today_str = date.today().strftime("%d-%m-%Y")
    results = {"bulk": 0, "block": 0}

    for deal_type, endpoint in [
        ("BULK", f"https://www.nseindia.com/api/bulk-deals?date={today_str}"),
        ("BLOCK", f"https://www.nseindia.com/api/block-deals?date={today_str}"),
    ]:
        try:
            data = asyncio.run(_nse_get(endpoint))
            deals = data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"Failed to fetch {deal_type} deals: {e}")
            continue

        with db_session() as session:
            for deal in deals:
                symbol = deal.get("BD_SYMBOL") or deal.get("symbol", "")
                if not symbol:
                    continue

                qty = int(deal.get("BD_QTY_TRD") or deal.get("quantity") or 0)
                price = float(deal.get("BD_TP_VAL") or deal.get("price") or 0)
                deal_value_cr = round((qty * price) / 1e7, 2) if qty and price else None

                # Skip duplicate
                exists = session.query(BulkBlockDeal).filter(
                    BulkBlockDeal.deal_date == date.today(),
                    BulkBlockDeal.symbol == symbol,
                    BulkBlockDeal.deal_type == deal_type,
                    BulkBlockDeal.client_name == (deal.get("BD_CLIENT_NAME") or deal.get("clientName")),
                ).first()
                if exists:
                    continue

                avg_vol = _get_30d_avg_volume(session, symbol)
                volume_ratio = round(qty / avg_vol, 2) if avg_vol and qty else None

                session.add(BulkBlockDeal(
                    deal_date=date.today(),
                    symbol=symbol,
                    deal_type=deal_type,
                    client_name=deal.get("BD_CLIENT_NAME") or deal.get("clientName"),
                    buy_sell=deal.get("BD_BUY_SELL") or deal.get("buySell"),
                    quantity=qty,
                    price=price,
                    deal_value_cr=deal_value_cr,
                    avg_volume_30d=avg_vol,
                    volume_ratio=volume_ratio,
                ))
                results[deal_type.lower()] += 1

    msg = f"Bulk: {results['bulk']} new, Block: {results['block']} new"
    logger.info(msg)
    return msg


@celery_app.task(name="app.workers.bulk_deals_fetcher.fetch_insider_trades")
def fetch_insider_trades():
    """Fetch NSE PIT (insider trading) disclosures."""
    url = "https://www.nseindia.com/api/corporates-pit?symbol=&from=&to=&type=all"
    try:
        data = asyncio.run(_nse_get(url))
    except Exception as e:
        logger.error(f"Insider trades fetch failed: {e}")
        return f"Failed: {e}"

    records = data.get("data", []) if isinstance(data, dict) else data
    new_count = 0

    with db_session() as session:
        for rec in records:
            symbol = rec.get("symbol", "")
            if not symbol:
                continue

            # Parse trade date
            raw_date = rec.get("date") or rec.get("tdpTransactionType") or ""
            try:
                trade_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date() if raw_date else None
            except ValueError:
                trade_date = None

            # Deduplicate
            exists = session.query(InsiderTrade).filter(
                InsiderTrade.symbol == symbol,
                InsiderTrade.acquirer_name == rec.get("personName"),
                InsiderTrade.trade_date == trade_date,
            ).first()
            if exists:
                continue

            qty_bought = int(rec.get("noOfSecBought") or 0)
            qty_sold = int(rec.get("noOfSecSold") or 0)
            qty = qty_bought or qty_sold
            trade_type = "BUY" if qty_bought > 0 else "SELL"

            session.add(InsiderTrade(
                symbol=symbol,
                acquirer_name=rec.get("personName"),
                acquirer_type=rec.get("category"),
                trade_type=trade_type,
                security_type=rec.get("secType"),
                quantity=qty,
                price=float(rec.get("price") or 0) or None,
                trade_date=trade_date,
                before_holding_pct=float(rec.get("beforeShareholding") or 0) or None,
                after_holding_pct=float(rec.get("afterShareholding") or 0) or None,
            ))
            new_count += 1

    msg = f"Stored {new_count} new insider trades"
    logger.info(msg)
    return msg
