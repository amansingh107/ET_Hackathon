"""
OHLCV Data Service for ET Investor AI
Fetches stock and index OHLCV data from NSE using jugaad-data
"""

import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class OHLCVService:
    """Service for fetching OHLCV (Open, High, Low, Close, Volume) data."""

    def __init__(self):
        self._init_jugaad()

    def _init_jugaad(self):
        """Initialize jugaad-data components."""
        try:
            from jugaad_data.nse import stock_df, NSELive

            self._stock_df = stock_df
            self._live = NSELive()
            self._available = True
        except ImportError:
            logger.warning("jugaad-data not installed. OHLCV service unavailable.")
            self._available = False

    def get_stock_ohlcv(
        self, symbol: str, start_date: date, end_date: date, series: str = "EQ"
    ) -> Dict[str, Any]:
        """
        Fetch stock OHLCV data.

        Args:
            symbol: NSE stock symbol (e.g., 'RELIANCE')
            start_date: Start date
            end_date: End date
            series: Stock series ('EQ' for equity)

        Returns:
            Dict with 'data', 'fetch_time', 'symbol', 'count'
        """
        fetch_time = datetime.now()

        if not self._available:
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
                "count": 0,
                "error": "OHLCV service not available",
            }

        try:
            df = self._stock_df(
                symbol=symbol, from_date=start_date, to_date=end_date, series=series
            )

            if df.empty:
                return {
                    "data": [],
                    "fetch_time": fetch_time.isoformat(),
                    "symbol": symbol,
                    "count": 0,
                }

            # Standardize column names
            df = df.rename(
                columns={
                    "DATE": "date",
                    "OPEN": "open",
                    "HIGH": "high",
                    "LOW": "low",
                    "CLOSE": "close",
                    "VOLUME": "volume",
                    "VWAP": "vwap",
                    "DELIVERY %": "delivery_pct",
                    "NO OF TRADES": "trades",
                }
            )

            # Convert date to string for JSON serialization
            if "date" in df.columns:
                df["date"] = df["date"].astype(str)

            # Select relevant columns
            cols = [
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "vwap",
                "delivery_pct",
                "trades",
            ]
            available_cols = [c for c in cols if c in df.columns]
            df = df[available_cols]

            records = df.to_dict(orient="records")

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
                "count": len(records),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
                "count": 0,
                "error": str(e),
            }

    def get_index_ohlcv(
        self, index_name: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        Fetch index OHLCV data.

        Args:
            index_name: Index name (e.g., 'NIFTY 50', 'NIFTY BANK')
            start_date: Start date
            end_date: End date

        Returns:
            Dict with 'data', 'fetch_time', 'index', 'count'
        """
        fetch_time = datetime.now()

        if not self._available:
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "index": index_name,
                "count": 0,
                "error": "OHLCV service not available",
            }

        try:
            from jugaad_data.nse import index_df

            df = index_df(symbol=index_name, from_date=start_date, to_date=end_date)

            if df.empty:
                return {
                    "data": [],
                    "fetch_time": fetch_time.isoformat(),
                    "index": index_name,
                    "count": 0,
                }

            # Standardize
            df = df.rename(
                columns={
                    "HistoricalDate": "date",
                    "OPEN": "open",
                    "HIGH": "high",
                    "LOW": "low",
                    "CLOSE": "close",
                }
            )

            if "date" in df.columns:
                df["date"] = df["date"].astype(str)

            cols = ["date", "open", "high", "low", "close"]
            available_cols = [c for c in cols if c in df.columns]
            df = df[available_cols]

            records = df.to_dict(orient="records")

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "index": index_name,
                "count": len(records),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching index OHLCV for {index_name}: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "index": index_name,
                "count": 0,
                "error": str(e),
            }

    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current/latest stock quote.

        Args:
            symbol: NSE stock symbol

        Returns:
            Dict with current price info and fetch_time
        """
        fetch_time = datetime.now()

        if not self._available:
            return {
                "data": None,
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
                "error": "Service not available",
            }

        try:
            quote = self._live.stock_quote(symbol)

            price_info = quote.get("priceInfo", {})

            return {
                "data": {
                    "symbol": symbol,
                    "open": price_info.get("open"),
                    "high": price_info.get("intraDayHighLow", {}).get("max"),
                    "low": price_info.get("intraDayHighLow", {}).get("min"),
                    "close": price_info.get("close"),
                    "last_price": price_info.get("lastPrice"),
                    "change": price_info.get("change"),
                    "pct_change": price_info.get("pChange"),
                    "prev_close": price_info.get("previousClose"),
                },
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
            }

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {
                "data": None,
                "fetch_time": fetch_time.isoformat(),
                "symbol": symbol,
                "error": str(e),
            }
