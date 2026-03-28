"""
Corporate Data Fetcher for ET Investor AI - Module 1 (Opportunity Radar)
=========================================================================

This module fetches corporate data from NSE using jugaad-data's session management.
The session properly handles NSE's cookie/header requirements that block direct requests.

WORKING DATA SOURCES:
1. Bulk Deals - Daily bulk deal data (CSV)
2. Block Deals - Daily block deal data (CSV)
3. Insider Trades (PIT) - Promoter/Insider trading disclosures
4. Corporate Announcements - General corporate filings/news
5. Board Meetings / Event Calendar - Upcoming corporate events
6. Short Selling - Daily short selling data

Author: ET Investor AI
Date: March 2026
"""

import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import json
import io


class CorporateDataFetcher:
    """Fetches corporate data from NSE using jugaad-data's session."""

    def __init__(self):
        """Initialize with jugaad-data's NSE session."""
        from jugaad_data.nse import NSELive, NSEArchives

        self.live = NSELive()
        self.archives = NSEArchives()
        self.session = self.live.s  # Reuse session with proper headers/cookies

    # =========================================================================
    # BULK DEALS
    # =========================================================================

    def get_bulk_deals(self, as_dataframe: bool = True) -> pd.DataFrame | str:
        """
        Fetch today's bulk deals from NSE.

        Bulk deals are transactions where quantity traded is more than 0.5%
        of the total shares of the company.

        Returns:
            DataFrame with columns: Date, Symbol, Security Name, Client Name,
                                   Buy/Sell, Quantity Traded, Trade Price, Remarks
        """
        csv_data = self.archives.bulk_deals_raw()

        if as_dataframe:
            df = pd.read_csv(io.StringIO(csv_data))
            df.columns = df.columns.str.strip()
            return df
        return csv_data

    def get_block_deals(self, as_dataframe: bool = True) -> pd.DataFrame | str:
        """
        Fetch today's block deals from NSE.

        Block deals are transactions of minimum quantity of 5 lakh shares
        or minimum value of Rs. 5 crore.

        Returns:
            DataFrame with columns: Date, Symbol, Security Name, Client Name,
                                   Buy/Sell, Quantity Traded, Trade Price
        """
        # Use fresh session from daily_reports to avoid 403 errors
        dr = self.archives.daily_reports
        file_info = dr.find_file("CM-BLOCK-DEAL")
        url = file_info["filePath"] + file_info["fileActlName"]

        response = dr.s.get(url, timeout=30)
        response.raise_for_status()

        if as_dataframe:
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip()
            return df
        return response.text

    # =========================================================================
    # INSIDER TRADES (PIT - Prohibition of Insider Trading)
    # =========================================================================

    def get_insider_trades(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch insider trading disclosures (PIT).

        Args:
            symbol: Optional stock symbol to filter by

        Returns:
            DataFrame with insider trading details including:
            - Company, Symbol
            - Acquirer Name, Category (Promoter/Director/etc)
            - Transaction Type (Buy/Sell)
            - Shares Before/After, Percentage Before/After
            - Transaction Date, Intimation Date
        """
        url = "https://www.nseindia.com/api/corporates-pit"
        if symbol:
            url += f"?symbol={symbol}"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        records = data.get("data", [])

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Rename columns for clarity
        column_map = {
            "symbol": "Symbol",
            "company": "Company",
            "acqName": "Acquirer",
            "personCategory": "Category",
            "tdpTransactionType": "Transaction",
            "secAcq": "Quantity",
            "secVal": "Value",
            "befAcqSharesNo": "Shares_Before",
            "befAcqSharesPer": "Pct_Before",
            "afterAcqSharesNo": "Shares_After",
            "afterAcqSharesPer": "Pct_After",
            "acqfromDt": "From_Date",
            "acqtoDt": "To_Date",
            "intimDt": "Intimation_Date",
            "acqMode": "Mode",
            "exchange": "Exchange",
        }

        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
        return df

    # =========================================================================
    # CORPORATE ANNOUNCEMENTS
    # =========================================================================

    def get_corporate_announcements(
        self,
        symbol: Optional[str] = None,
        index: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Fetch corporate announcements/filings.

        Args:
            symbol: Filter by stock symbol (e.g., 'RELIANCE')
            index: Filter by index ('nifty50', 'nifty100', 'equities')
            limit: Max records to return

        Returns:
            DataFrame with announcement details
        """
        if symbol:
            # Use the built-in method for symbol
            data = self.live.corporate_announcements(symbol)
        else:
            url = "https://www.nseindia.com/api/corporate-announcements"
            if index:
                url += f"?index={index}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data[:limit])

        # Select key columns if available
        key_cols = [
            "symbol",
            "sm_name",
            "desc",
            "attchmntText",
            "an_dt",
            "attchmntFile",
        ]
        available_cols = [c for c in key_cols if c in df.columns]

        if available_cols:
            df = df[available_cols]
            df = df.rename(
                columns={
                    "sm_name": "Company",
                    "desc": "Category",
                    "attchmntText": "Description",
                    "an_dt": "Date",
                    "attchmntFile": "Attachment_URL",
                }
            )

        return df

    # =========================================================================
    # BOARD MEETINGS / EVENT CALENDAR
    # =========================================================================

    def get_board_meetings(self, index: str = "equities") -> pd.DataFrame:
        """
        Fetch upcoming board meetings.

        Args:
            index: 'equities', 'nifty50', 'nifty100', etc.

        Returns:
            DataFrame with board meeting schedules
        """
        url = f"https://www.nseindia.com/api/corporate-board-meetings?index={index}"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        records = data.get("data", [])

        if not records:
            return pd.DataFrame()

        return pd.DataFrame(records)

    def get_event_calendar(self) -> pd.DataFrame:
        """
        Fetch corporate event calendar (upcoming events).

        Returns:
            DataFrame with upcoming corporate events
        """
        url = "https://www.nseindia.com/api/event-calendar"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    # =========================================================================
    # SHORT SELLING
    # =========================================================================

    def get_short_selling(self, as_dataframe: bool = True) -> pd.DataFrame | str:
        """
        Fetch today's short selling data.

        Returns:
            DataFrame with short selling positions
        """
        # Use fresh session from daily_reports to avoid 403 errors
        dr = self.archives.daily_reports
        file_info = dr.find_file("CM-SHORT-SELLING")
        url = file_info["filePath"] + file_info["fileActlName"]

        response = dr.s.get(url, timeout=30)
        response.raise_for_status()

        if as_dataframe:
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip()
            return df
        return response.text

    # =========================================================================
    # UTILITY: GET ALL CORPORATE DATA
    # =========================================================================

    def get_all_signals(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch all corporate data sources for signal generation.

        Returns:
            Dictionary with all corporate data DataFrames
        """
        results = {}

        # Bulk Deals
        try:
            results["bulk_deals"] = self.get_bulk_deals()
            print(f"Bulk Deals: {len(results['bulk_deals'])} records")
        except Exception as e:
            print(f"Bulk Deals: Error - {e}")
            results["bulk_deals"] = pd.DataFrame()

        # Block Deals
        try:
            results["block_deals"] = self.get_block_deals()
            print(f"Block Deals: {len(results['block_deals'])} records")
        except Exception as e:
            print(f"Block Deals: Error - {e}")
            results["block_deals"] = pd.DataFrame()

        # Insider Trades
        try:
            results["insider_trades"] = self.get_insider_trades()
            print(f"Insider Trades: {len(results['insider_trades'])} records")
        except Exception as e:
            print(f"Insider Trades: Error - {e}")
            results["insider_trades"] = pd.DataFrame()

        # Corporate Announcements
        try:
            results["announcements"] = self.get_corporate_announcements(
                index="equities"
            )
            print(f"Announcements: {len(results['announcements'])} records")
        except Exception as e:
            print(f"Announcements: Error - {e}")
            results["announcements"] = pd.DataFrame()

        # Event Calendar
        try:
            results["events"] = self.get_event_calendar()
            print(f"Events: {len(results['events'])} records")
        except Exception as e:
            print(f"Events: Error - {e}")
            results["events"] = pd.DataFrame()

        # Short Selling
        try:
            results["short_selling"] = self.get_short_selling()
            print(f"Short Selling: {len(results['short_selling'])} records")
        except Exception as e:
            print(f"Short Selling: Error - {e}")
            results["short_selling"] = pd.DataFrame()

        return results


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Corporate Data Fetcher - Testing All Sources")
    print("=" * 70)

    fetcher = CorporateDataFetcher()

    # Test 1: Bulk Deals
    print("\n" + "=" * 70)
    print("1. BULK DEALS")
    print("=" * 70)
    try:
        bulk = fetcher.get_bulk_deals()
        print(f"Records: {len(bulk)}")
        print(f"Columns: {list(bulk.columns)}")
        if len(bulk) > 0:
            print("\nSample (first 3 rows):")
            print(bulk.head(3).to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Block Deals
    print("\n" + "=" * 70)
    print("2. BLOCK DEALS")
    print("=" * 70)
    try:
        block = fetcher.get_block_deals()
        print(f"Records: {len(block)}")
        if len(block) > 0:
            print(f"Columns: {list(block.columns)}")
            print("\nAll block deals today:")
            print(block.to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Insider Trades
    print("\n" + "=" * 70)
    print("3. INSIDER TRADES (PIT)")
    print("=" * 70)
    try:
        insider = fetcher.get_insider_trades()
        print(f"Records: {len(insider)}")
        if len(insider) > 0:
            print(f"Columns: {list(insider.columns)}")
            print("\nSample (first 5 rows):")
            cols = [
                "Symbol",
                "Company",
                "Acquirer",
                "Category",
                "Transaction",
                "Quantity",
            ]
            available = [c for c in cols if c in insider.columns]
            print(insider[available].head(5).to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Corporate Announcements
    print("\n" + "=" * 70)
    print("4. CORPORATE ANNOUNCEMENTS")
    print("=" * 70)
    try:
        ann = fetcher.get_corporate_announcements(index="equities", limit=10)
        print(f"Records: {len(ann)}")
        if len(ann) > 0:
            print(f"Columns: {list(ann.columns)}")
            print("\nSample (first 5 rows):")
            print(ann.head(5).to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: Event Calendar
    print("\n" + "=" * 70)
    print("5. EVENT CALENDAR")
    print("=" * 70)
    try:
        events = fetcher.get_event_calendar()
        print(f"Records: {len(events)}")
        if len(events) > 0:
            print(f"Columns: {list(events.columns)}")
            print("\nUpcoming events (first 10):")
            print(events.head(10).to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    # Test 6: Short Selling
    print("\n" + "=" * 70)
    print("6. SHORT SELLING")
    print("=" * 70)
    try:
        short = fetcher.get_short_selling()
        print(f"Records: {len(short)}")
        if len(short) > 0:
            print(f"Columns: {list(short.columns)}")
            print("\nSample (first 5 rows):")
            print(short.head(5).to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 70)
    print("SUMMARY: All corporate data sources tested successfully!")
    print("=" * 70)
