"""
Corporate Data Service for ET Investor AI
Fetches bulk deals, block deals, insider trades, announcements from NSE
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from io import StringIO
from loguru import logger


class CorporateDataService:
    """Service for fetching corporate data (bulk deals, insider trades, etc.)."""

    def __init__(self):
        self._init_jugaad()

    def _init_jugaad(self):
        """Initialize jugaad-data components."""
        try:
            from jugaad_data.nse import NSELive, NSEArchives

            self._live = NSELive()
            self._archives = NSEArchives()
            self._session = self._live.s
            self._available = True
        except ImportError:
            logger.warning(
                "jugaad-data not installed. Corporate data service unavailable."
            )
            self._available = False

    def get_bulk_deals(self) -> Dict[str, Any]:
        """
        Fetch today's bulk deals.

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
            csv_data = self._archives.bulk_deals_raw()
            df = pd.read_csv(StringIO(csv_data))
            df.columns = df.columns.str.strip()

            # Rename for consistency
            df = df.rename(
                columns={
                    "Date": "date",
                    "Symbol": "symbol",
                    "Security Name": "company",
                    "Client Name": "client",
                    "Buy/Sell": "action",
                    "Quantity Traded": "quantity",
                    "Trade Price / Wght. Avg. Price": "price",
                }
            )

            records = df.to_dict(orient="records")

            # Get the data date from first record
            data_date = records[0].get("date", "N/A") if records else "N/A"

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "data_date": data_date,
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching bulk deals: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_block_deals(self) -> Dict[str, Any]:
        """
        Fetch today's block deals.

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
            dr = self._archives.daily_reports
            file_info = dr.find_file("CM-BLOCK-DEAL")
            url = file_info["filePath"] + file_info["fileActlName"]

            response = dr.s.get(url, timeout=30)
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))
            df.columns = df.columns.str.strip()

            df = df.rename(
                columns={
                    "Date": "date",
                    "Symbol": "symbol",
                    "Security Name": "company",
                    "Client Name": "client",
                    "Buy/Sell": "action",
                    "Quantity Traded": "quantity",
                    "Trade Price / Wght. Avg. Price": "price",
                }
            )

            records = df.to_dict(orient="records")
            data_date = records[0].get("date", "N/A") if records else "N/A"

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "data_date": data_date,
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching block deals: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_insider_trades(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch insider trading disclosures (PIT).

        Args:
            symbol: Optional stock symbol to filter

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
            url = "https://www.nseindia.com/api/corporates-pit"
            if symbol:
                url += f"?symbol={symbol}"

            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            records = data.get("data", [])

            # Flatten and clean records
            cleaned = []
            for r in records:
                cleaned.append(
                    {
                        "symbol": r.get("symbol"),
                        "company": r.get("company"),
                        "acquirer": r.get("acqName"),
                        "category": r.get("personCategory"),
                        "transaction": r.get("tdpTransactionType"),
                        "quantity": r.get("secAcq"),
                        "value": r.get("secVal"),
                        "shares_before": r.get("befAcqSharesNo"),
                        "pct_before": r.get("befAcqSharesPer"),
                        "shares_after": r.get("afterAcqSharesNo"),
                        "pct_after": r.get("afterAcqSharesPer"),
                        "from_date": r.get("acqfromDt"),
                        "to_date": r.get("acqtoDt"),
                        "intimation_date": r.get("intimDt"),
                        "mode": r.get("acqMode"),
                    }
                )

            # Get the latest intimation date
            data_date = cleaned[0].get("intimation_date", "N/A") if cleaned else "N/A"

            return {
                "data": cleaned,
                "fetch_time": fetch_time.isoformat(),
                "data_date": data_date,
                "count": len(cleaned),
            }

        except Exception as e:
            logger.error(f"Error fetching insider trades: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_announcements(self, index: str = "equities") -> Dict[str, Any]:
        """
        Fetch corporate announcements.

        Args:
            index: Filter by index ('equities', 'nifty50', etc.)

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
            url = f"https://www.nseindia.com/api/corporate-announcements?index={index}"
            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            records = response.json()

            # Clean records
            cleaned = []
            for r in records:
                cleaned.append(
                    {
                        "symbol": r.get("symbol"),
                        "company": r.get("sm_name"),
                        "category": r.get("desc"),
                        "description": r.get("attchmntText"),
                        "date": r.get("an_dt"),
                        "attachment_url": r.get("attchmntFile"),
                    }
                )

            data_date = cleaned[0].get("date", "N/A") if cleaned else "N/A"

            return {
                "data": cleaned,
                "fetch_time": fetch_time.isoformat(),
                "data_date": data_date,
                "count": len(cleaned),
            }

        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_event_calendar(self) -> Dict[str, Any]:
        """
        Fetch upcoming corporate events.

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
            url = "https://www.nseindia.com/api/event-calendar"
            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            records = response.json()

            cleaned = []
            for r in records:
                cleaned.append(
                    {
                        "symbol": r.get("symbol"),
                        "company": r.get("company"),
                        "purpose": r.get("purpose"),
                        "description": r.get("bm_desc"),
                        "date": r.get("date"),
                    }
                )

            return {
                "data": cleaned,
                "fetch_time": fetch_time.isoformat(),
                "count": len(cleaned),
            }

        except Exception as e:
            logger.error(f"Error fetching event calendar: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }

    def get_short_selling(self) -> Dict[str, Any]:
        """
        Fetch short selling data.

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
            dr = self._archives.daily_reports
            file_info = dr.find_file("CM-SHORT-SELLING")
            url = file_info["filePath"] + file_info["fileActlName"]

            response = dr.s.get(url, timeout=30)
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))
            df.columns = df.columns.str.strip()

            records = df.to_dict(orient="records")

            return {
                "data": records,
                "fetch_time": fetch_time.isoformat(),
                "count": len(records),
            }

        except Exception as e:
            logger.error(f"Error fetching short selling: {e}")
            return {
                "data": [],
                "fetch_time": fetch_time.isoformat(),
                "count": 0,
                "error": str(e),
            }
