# Data Fetchers - ET Investor AI

Production-ready data fetchers for Indian stock market data. All sources tested and working.

## Quick Start

```bash
cd data_fetchers_test
source venv/bin/activate
pip install -r requirements.txt
```

## Available Fetchers

| File | Purpose | Module |
|------|---------|--------|
| `ohlcv_fetcher.py` | Stock & Index OHLCV data (5 years history) | Module 2 |
| `corporate_data_fetcher.py` | Bulk/Block deals, Insider trades, Announcements | Module 1 |
| `stock_universe_fetcher.py` | Nifty 500/50/Bank constituent lists | Both |
| `fundamentals_fetcher.py` | P/E, P/B, ROE, Quarterly results (Screener.in) | Module 1 |
| `bse_live_quotes.py` | Real-time stock quotes from BSE | Module 1 |
| `amfi_nav_fetcher.py` | Mutual fund NAV data (14,000+ funds) | Module 1 |

## Usage Examples

### OHLCV Data (Module 2 - Chart Pattern Intelligence)

```python
from ohlcv_fetcher import JugaadOHLCVFetcher
from datetime import date, timedelta

fetcher = JugaadOHLCVFetcher()

# Fetch stock OHLCV (1 year)
end_date = date(2025, 3, 27)
start_date = end_date - timedelta(days=365)
df = fetcher.fetch_stock_ohlcv("RELIANCE", start_date, end_date)
# Returns: date, open, high, low, close, volume, vwap, delivery_pct

# Fetch index OHLCV
df = fetcher.fetch_index_ohlcv("NIFTY 50", start_date, end_date)
```

### Corporate Data (Module 1 - Opportunity Radar)

```python
from corporate_data_fetcher import CorporateDataFetcher

fetcher = CorporateDataFetcher()

# Bulk deals (200+ records/day)
bulk_deals = fetcher.get_bulk_deals()

# Block deals
block_deals = fetcher.get_block_deals()

# Insider trades (180+ records/day)
insider_trades = fetcher.get_insider_trades()

# Corporate announcements
announcements = fetcher.get_corporate_announcements()

# Upcoming board meetings
events = fetcher.get_event_calendar()

# Short selling positions
short_selling = fetcher.get_short_selling()

# Get all signals at once
all_data = fetcher.get_all_signals()
```

### Stock Universe

```python
from stock_universe_fetcher import get_nifty500, get_nifty50

nifty500 = get_nifty500()  # Returns DataFrame with Symbol, Company, Industry
nifty50 = get_nifty50()
```

### Fundamentals (Screener.in)

```python
from fundamentals_fetcher import get_stock_fundamentals

data = get_stock_fundamentals("RELIANCE")
# Returns: P/E, P/B, ROE, ROCE, Quarterly results, Shareholding pattern
```

### BSE Live Quotes

```python
from bse_live_quotes import get_quote

quote = get_quote("TCS")
# Returns: Price, Change%, Volume, Market Cap, 52W High/Low
```

### Mutual Fund NAV

```python
from amfi_nav_fetcher import get_all_nav

nav_data = get_all_nav()
# Returns: 14,000+ mutual fund NAVs with scheme codes
```

## Data Source Summary

| Data Type | Source | Reliability |
|-----------|--------|-------------|
| OHLCV (Stocks) | NSE via jugaad-data | HIGH |
| OHLCV (Indices) | NSE via jugaad-data | HIGH |
| Bulk Deals | NSE Archives | HIGH |
| Block Deals | NSE Daily Reports | HIGH |
| Insider Trades | NSE API | HIGH |
| Announcements | NSE API | HIGH |
| Stock Lists | NSE Direct | HIGH |
| Live Quotes | BSE | MEDIUM |
| Fundamentals | Screener.in | MEDIUM |
| MF NAV | AMFI | HIGH |

## File Structure

```
data_fetchers_test/
├── ohlcv_fetcher.py           # OHLCV data (stocks + indices)
├── corporate_data_fetcher.py  # All corporate data
├── stock_universe_fetcher.py  # Index constituents
├── fundamentals_fetcher.py    # Screener.in scraper
├── bse_live_quotes.py         # BSE real-time quotes
├── amfi_nav_fetcher.py        # Mutual fund NAV
├── requirements.txt           # Dependencies
├── DATA_SOURCE_ANALYSIS.md    # Detailed analysis
└── output/                    # Test output files
```

## Dependencies

Core library: `jugaad-data` - handles NSE session management (cookies, headers, TLS).

See `requirements.txt` for full list.
