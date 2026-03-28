"""
Market Data Service for ET Investor AI
Fetches market status, stock universe, and other market-wide data
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger
import requests


class MarketDataService:
    """Service for fetching market-wide data."""

    def __init__(self):
        self._init_jugaad()

    def _init_jugaad(self):
        """Initialize jugaad-data components."""
        try:
            from jugaad_data.nse import NSELive

            self._live = NSELive()
            self._session = self._live.s
            self._available = True
        except ImportError:
            logger.warning(
                "jugaad-data not installed. Market data service unavailable."
            )
            self._available = False

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status.

        Returns:
            Dict with market status and fetch_time
        """
        fetch_time = datetime.now()

        if not self._available:
            return {
                "data": None,
                "fetch_time": fetch_time.isoformat(),
                "error": "Service not available",
            }

        try:
            status = self._live.market_status()

            # Extract key info
            market_state = status.get("marketState", [])
            nifty_info = None
            for m in market_state:
                if m.get("market") == "Capital Market":
                    nifty_info = m
                    break

            return {
                "data": {
                    "status": nifty_info.get("marketStatus")
                    if nifty_info
                    else "Unknown",
                    "message": nifty_info.get("marketStatusMessage")
                    if nifty_info
                    else "",
                    "trade_date": nifty_info.get("tradeDate") if nifty_info else "",
                    "nifty_last": nifty_info.get("last") if nifty_info else None,
                    "nifty_change": nifty_info.get("variation") if nifty_info else None,
                    "nifty_pct_change": nifty_info.get("percentChange")
                    if nifty_info
                    else None,
                },
                "fetch_time": fetch_time.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching market status: {e}")
            return {"data": None, "fetch_time": fetch_time.isoformat(), "error": str(e)}

    def get_nifty500_list(self) -> Dict[str, Any]:
        """
        Get Nifty 500 constituents.

        Returns:
            Dict with 'data', 'fetch_time', 'count'
        """
        fetch_time = datetime.now()

        try:
            url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/csv,application/csv,text/plain",
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            records = df.to_dict(orient="records")

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching Nifty 500 list: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_nifty50_list(self) -> Dict[str, Any]:
        """
        Get Nifty 50 constituents.

        Returns:
            Dict with 'data', 'fetch_time', 'count'
        """
        fetch_time = datetime.now()

        try:
            url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/csv,application/csv,text/plain",
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            records = df.to_dict(orient="records")

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching Nifty 50 list: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_all_indices(self) -> Dict[str, Any]:
        """
        Get all NSE indices with current values.

        Returns:
            Dict with 'data', 'fetch_time', 'count'
        """
        fetch_time = datetime.now()

        if not self._available:
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": "Service not available",
            }

        try:
            indices = self._live.all_indices()

            records = []
            for idx in indices.get("data", []):
                records.append(
                    {
                        "index": idx.get("index"),
                        "last": idx.get("last"),
                        "change": idx.get("variation"),
                        "pct_change": idx.get("percentChange"),
                        "open": idx.get("open"),
                        "high": idx.get("high"),
                        "low": idx.get("low"),
                        "prev_close": idx.get("previousClose"),
                    }
                )

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching all indices: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }
