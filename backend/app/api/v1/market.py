"""
Market Data API Endpoints
Provides real-time market data with fetch timestamps
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date, timedelta
from pydantic import BaseModel
from typing import List, Any, Optional

from app.services.ohlcv_service import OHLCVService
from app.services.corporate_service import CorporateDataService
from app.services.market_service import MarketDataService

router = APIRouter(prefix="/market", tags=["market"])

# Initialize services
ohlcv_service = OHLCVService()
corporate_service = CorporateDataService()
market_service = MarketDataService()


# Response Models
class DataResponse(BaseModel):
    data: Any
    fetch_time: str
    count: Optional[int] = None
    data_date: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# MARKET STATUS
# ============================================================================


@router.get("/status", response_model=DataResponse)
def get_market_status():
    """Get current market status (open/closed, Nifty value)."""
    return market_service.get_market_status()


@router.get("/indices", response_model=DataResponse)
def get_all_indices():
    """Get all NSE indices with current values."""
    return market_service.get_all_indices()


# ============================================================================
# STOCK UNIVERSE
# ============================================================================


@router.get("/nifty500", response_model=DataResponse)
def get_nifty500():
    """Get Nifty 500 constituents list."""
    return market_service.get_nifty500_list()


@router.get("/nifty50", response_model=DataResponse)
def get_nifty50():
    """Get Nifty 50 constituents list."""
    return market_service.get_nifty50_list()


# ============================================================================
# OHLCV DATA
# ============================================================================


@router.get("/ohlcv/{symbol}", response_model=DataResponse)
def get_stock_ohlcv(
    symbol: str,
    days: int = Query(30, ge=1, le=1825, description="Number of days (max 5 years)"),
):
    """
    Get historical OHLCV data for a stock.

    - **symbol**: NSE stock symbol (e.g., RELIANCE, TCS)
    - **days**: Number of days of history (default 30, max 1825)
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    return ohlcv_service.get_stock_ohlcv(
        symbol=symbol.upper(), start_date=start_date, end_date=end_date
    )


@router.get("/ohlcv/index/{index_name}", response_model=DataResponse)
def get_index_ohlcv(
    index_name: str,
    days: int = Query(30, ge=1, le=1825, description="Number of days"),
):
    """
    Get historical OHLCV data for an index.

    - **index_name**: Index name (e.g., NIFTY 50, NIFTY BANK)
    - **days**: Number of days of history
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # URL decode common index names
    index_map = {
        "NIFTY50": "NIFTY 50",
        "NIFTY_50": "NIFTY 50",
        "NIFTYBANK": "NIFTY BANK",
        "NIFTY_BANK": "NIFTY BANK",
    }
    index_name = index_map.get(index_name.upper(), index_name)

    return ohlcv_service.get_index_ohlcv(
        index_name=index_name, start_date=start_date, end_date=end_date
    )


@router.get("/quote/{symbol}", response_model=DataResponse)
def get_stock_quote(symbol: str):
    """
    Get current/latest quote for a stock.

    - **symbol**: NSE stock symbol
    """
    return ohlcv_service.get_stock_quote(symbol.upper())


# ============================================================================
# CORPORATE DATA
# ============================================================================


@router.get("/bulk-deals", response_model=DataResponse)
def get_bulk_deals():
    """
    Get today's bulk deals.

    Bulk deals are transactions where quantity > 0.5% of total shares.
    """
    return corporate_service.get_bulk_deals()


@router.get("/block-deals", response_model=DataResponse)
def get_block_deals():
    """
    Get today's block deals.

    Block deals are transactions of min 5 lakh shares or Rs. 5 crore value.
    """
    return corporate_service.get_block_deals()


@router.get("/insider-trades", response_model=DataResponse)
def get_insider_trades(symbol: Optional[str] = None):
    """
    Get insider trading disclosures (PIT).

    - **symbol**: Optional filter by stock symbol
    """
    return corporate_service.get_insider_trades(symbol.upper() if symbol else None)


@router.get("/announcements", response_model=DataResponse)
def get_announcements(
    index: str = Query("equities", description="Filter: equities, nifty50, etc."),
):
    """
    Get corporate announcements/filings.

    - **index**: Filter by index (equities, nifty50, nifty100)
    """
    return corporate_service.get_announcements(index)


@router.get("/events", response_model=DataResponse)
def get_event_calendar():
    """Get upcoming corporate events (board meetings, AGMs, etc.)."""
    return corporate_service.get_event_calendar()


@router.get("/short-selling", response_model=DataResponse)
def get_short_selling():
    """Get daily short selling positions."""
    return corporate_service.get_short_selling()
