# Data Sources

All sources are free and publicly accessible. No paid API keys required.

---

## 1. NSE India — Primary Source

**Base URL**: `https://www.nseindia.com`

NSE provides most data as public CSV downloads or JSON endpoints from their website.

### OHLCV Historical Data (via nsepy)
```python
from nsepy import get_history
from datetime import date

df = get_history(
    symbol="RELIANCE",
    start=date(2020, 1, 1),
    end=date.today()
)
# Returns: Date, Symbol, Open, High, Low, Close, Volume, Turnover
```

### Live Quotes (via nsetools)
```python
from nsetools import Nse
nse = Nse()
q = nse.get_quote("RELIANCE")
# Returns: lastPrice, change, pChange, totalTradedVolume, 52weekHigh, etc.
```

### All Traded Symbols
```python
all_stocks = nse.get_stock_codes()
# Returns dict of {SYMBOL: "Company Name"} — ~2000 stocks
```

### Bulk & Block Deals (CSV Download)
```
URL: https://www.nseindia.com/api/bulk-deals?
URL: https://www.nseindia.com/api/block-deals?
Frequency: Daily (after market close ~4 PM IST)
Format: JSON
Fields: symbol, clientName, dealType, quantity, price, remarks
```

### Insider Trading Disclosures
```
URL: https://www.nseindia.com/api/corporates-pit?
Frequency: As disclosed (check every 6 hours)
Format: JSON
Fields: symbol, acquirerName, securityType, noOfSecBought, noOfSecSold, beforeShareholding, afterShareholding, date
```

### Corporate Filings (Exchange Filings)
```
URL: https://www.nseindia.com/api/corporates-corporateActions?
Frequency: Every 15 minutes
Format: JSON
Covers: Dividends, splits, bonuses, AGM notices, board meetings
```

### NSE Indices (Nifty 50, Nifty 500, etc.)
```python
from nsepy import get_history
from nsepy.symbols import nse_index

df = get_history(symbol="NIFTY 50", start=date(2024,1,1), end=date.today(), index=True)
```

### Nifty 500 Stock List (Full NSE Universe)
```
URL: https://archives.nseindia.com/content/indices/ind_nifty500list.csv
This gives you the 500 most liquid stocks — use as primary scanning universe
For full ~2000 stock universe, use nse.get_stock_codes()
```

---

## 2. BSE India — Supplementary Filings Source

**Base URL**: `https://www.bseindia.com`

### BSE Filings via bsedata
```python
from bsedata.bse import BSE
b = BSE(update_codes=True)

# Get company info
b.getQuote("500325")  # BSE code for Reliance

# Get all filings
# BSE has a more comprehensive filing system than NSE for some disclosures
```

### BSE Corporate Announcements
```
URL: https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?strCat=-1&strPrevDate=...&strScrip=...&strSearch=P&strToDate=...&strType=C
Format: JSON
Covers: Results, AGM, board meetings, credit ratings, order wins, capacity additions
Frequency: Every 15 minutes
```

### BSE Bulk Deals
```
URL: https://api.bseindia.com/BseIndiaAPI/api/bdeal/w?
Format: JSON
```

---

## 3. SEBI EDGAR — Regulatory Filings

**Base URL**: `https://www.sebi.gov.in`

### SEBI Orders & Circulars
```
URL: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=13
Type: HTML + PDF
Frequency: Check daily
Use: Regulatory risk signals — if SEBI takes action on a company
```

### Mutual Fund Data (AMFI)
```
URL: https://www.amfiindia.com/spages/NAVAll.txt
Format: Plain text (pipe-separated)
Frequency: Daily after 9 PM IST
Use: Track MF holdings changes, net purchases/sales
```

### FII/FPI Holdings Data
```
URL: https://www.sebi.gov.in/statistics/1368167836647.html
Frequency: Monthly
```

---

## 4. Screener.in — Fundamental Data

**URL**: `https://www.screener.in`

Screener provides public company pages with 10+ years of financials.

### Scraping Strategy
```python
# Screener allows scraping for non-commercial use
# Use httpx + BeautifulSoup
# Rate limit: max 1 request per 3 seconds

URL pattern: https://www.screener.in/company/{SYMBOL}/

# Extracts:
# - Quarterly P&L (Revenue, PAT, EPS)
# - Annual Balance Sheet
# - Cash Flow statements
# - Key ratios (PE, ROE, ROCE, Debt/Equity)
# - Shareholding pattern (promoter, FII, DII, retail)
```

---

## 5. Yahoo Finance — OHLCV Backup

Used as fallback when nsepy is rate-limited or down.

```python
import yfinance as yf

# NSE stocks use .NS suffix
ticker = yf.Ticker("RELIANCE.NS")
df = ticker.history(period="1y", interval="1d")

# For indices
nifty = yf.Ticker("^NSEI")
```

---

## 6. Tickertape — Earnings Transcripts

**URL**: `https://www.tickertape.in`

```
Earnings call transcripts and management commentary are available on company pages.
Scrape: https://www.tickertape.in/stocks/{slug}/transcripts
Use: Feed into LLM for management tone analysis
```

---

## Data Update Frequencies

| Data Type | Source | Frequency | Method |
|---|---|---|---|
| Live quotes | NSE (nsetools) | Every 5 min (market hours) | Python lib |
| OHLCV daily | NSE (nsepy) | Once daily (after 6 PM IST) | Python lib |
| OHLCV intraday | NSE | Every 15 min | Web scrape |
| Bulk/Block deals | NSE | Daily (after 4 PM IST) | API endpoint |
| Insider trades | NSE | Every 6 hours | API endpoint |
| Corp filings | NSE + BSE | Every 15 min | API endpoint |
| Quarterly results | Screener.in | Per earnings season | Web scrape |
| SEBI orders | SEBI | Daily | Web scrape |
| MF NAV | AMFI | Daily (after 9 PM IST) | Text file |
| Shareholding | BSE | Quarterly | Web scrape |

---

## Handling NSE Rate Limits

NSE started blocking automated requests in 2021. Use these techniques:

```python
import httpx
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

async def fetch_nse(url: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS) as client:
        # First hit the homepage to get cookies
        await client.get("https://www.nseindia.com")
        await asyncio.sleep(random.uniform(1, 3))

        response = await client.get(url)
        return response.json()
```

---

## NSE Universe File

Download and store the full stock universe locally:
```
data/nse_universe.csv

Columns: symbol, company_name, series, isin, sector, industry
Source: NSE F&O list + Nifty 500 + SME board
Update: Monthly (manual)
```
