# Data Source Analysis - ET Investor AI

## Executive Summary

All required data sources are working and production-ready.

---

## 1. OHLCV Data (jugaad-data)

**File:** `ohlcv_fetcher.py`

### Source
- **Library**: `jugaad-data` (Python wrapper around NSE APIs)
- **Data**: Open, High, Low, Close, Volume, VWAP, Delivery %, No. of Trades

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Chart Pattern Intelligence** | PRIMARY - All pattern detection needs OHLCV | CRITICAL |
| **Backtesting Engine** | PRIMARY - Historical data for win rate calculation | CRITICAL |

### Reliability

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| NSE changes API endpoints | MEDIUM | jugaad-data is actively maintained |
| Rate limiting | LOW | Built-in delays in library |

### Data Quality
- RELIANCE 2023: 248 trading days (correct)
- OHLCV values match NSE website
- Delivery % included

---

## 2. Corporate Data (jugaad-data session)

**File:** `corporate_data_fetcher.py`

### Working Sources

| Data Type | Method | Records/Day |
|-----------|--------|-------------|
| Bulk Deals | `NSEArchives.bulk_deals_raw()` | 200+ |
| Block Deals | `NSEDailyReports.find_file()` | ~10 |
| Insider Trades | Session + `/api/corporates-pit` | 180+ |
| Announcements | `NSELive.corporate_announcements()` | 20+ |
| Event Calendar | Session + `/api/event-calendar` | 70+ |
| Short Selling | `NSEDailyReports.find_file()` | 120+ |

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Opportunity Radar** | PRIMARY - All signal sources | CRITICAL |

### Key Insight
By reusing `jugaad-data`'s session (which handles NSE cookies/headers), we can access any NSE API endpoint.

---

## 3. Stock Universe (NSE Direct)

**File:** `stock_universe_fetcher.py`

### Source
- NSE public CSV files
- Nifty 500, Nifty 50, Nifty Bank constituents

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Chart Pattern Intelligence** | Defines scan universe | HIGH |
| **Opportunity Radar** | Sector mapping | MEDIUM |

### Reliability: HIGH
- Archive URLs stable for years
- List composition changes quarterly (expected)

---

## 4. Fundamentals (Screener.in)

**File:** `fundamentals_fetcher.py`

### Source
- Web scraping from Screener.in
- P/E, P/B, ROCE, ROE, quarterly results, shareholding

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Opportunity Radar** | Fundamental context for signals | HIGH |

### Reliability: MEDIUM
- HTML structure may change
- Rate-limited scraping (1 req/3s)

---

## 5. BSE Live Quotes

**File:** `bse_live_quotes.py`

### Source
- BSE India API via `bsedata` library
- Current price, change %, volume, market cap

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Opportunity Radar** | Live price for alerts | MEDIUM |

### Reliability: MEDIUM
- Good backup for live quotes

---

## 6. Mutual Fund NAV (AMFI)

**File:** `amfi_nav_fetcher.py`

### Source
- AMFI official text file
- 14,000+ mutual fund NAVs

### Module Usage

| Module | Usage | Importance |
|--------|-------|------------|
| **Opportunity Radar** | Track MF flows | LOW |

### Reliability: HIGH
- Official industry source
- Same format for 10+ years

---

## Module Readiness

### Module 2: Chart Pattern Intelligence - READY

| Required Data | Source | Status |
|---------------|--------|--------|
| Daily OHLCV (5 years) | jugaad-data | WORKING |
| Stock universe (500 stocks) | NSE direct | WORKING |
| Index OHLCV | jugaad-data | WORKING |
| Volume data | jugaad-data | WORKING |

### Module 1: Opportunity Radar - READY

| Required Data | Source | Status |
|---------------|--------|--------|
| Bulk/Block deals | jugaad-data | WORKING |
| Insider trades | jugaad-data | WORKING |
| Announcements | jugaad-data | WORKING |
| Event calendar | jugaad-data | WORKING |
| Fundamentals | Screener.in | WORKING |
| Live quotes | BSE | WORKING |

---

## Data Refresh Schedule

| Data Type | Update Frequency | Best Time to Fetch |
|-----------|------------------|-------------------|
| Daily OHLCV | Once daily | 7 PM IST |
| Bulk/Block deals | Once daily | 5 PM IST |
| Corporate filings | Every 15 min | Market hours |
| Live quotes | Every 5 min | Market hours |
| MF NAV | Once daily | 10 PM IST |
| Stock universe | Monthly | 1st of month |

---

## Summary

| Data Source | File | Reliability |
|-------------|------|-------------|
| NSE OHLCV | `ohlcv_fetcher.py` | HIGH |
| Corporate Data | `corporate_data_fetcher.py` | HIGH |
| Stock Universe | `stock_universe_fetcher.py` | HIGH |
| Fundamentals | `fundamentals_fetcher.py` | MEDIUM |
| BSE Quotes | `bse_live_quotes.py` | MEDIUM |
| MF NAV | `amfi_nav_fetcher.py` | HIGH |
