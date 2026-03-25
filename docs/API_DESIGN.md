# API Design

FastAPI backend. All endpoints return JSON. Authentication via JWT Bearer token.

---

## Base URL

```
Development:  http://localhost:8000/api/v1
Production:   https://your-domain.com/api/v1
```

---

## Authentication

```
POST /auth/register
POST /auth/login          → returns { access_token, token_type }
POST /auth/refresh
GET  /auth/me
```

All protected routes require: `Authorization: Bearer <token>`

---

## Module 1: Opportunity Radar

### Signals Feed

```
GET /signals/feed
```
Returns paginated list of recent signals, ordered by score desc.

**Query params:**
- `min_score` (int, default: 50) — minimum signal score
- `symbol` (str, optional) — filter by stock
- `signal_type` (str, optional) — filter by type
- `sector` (str, optional) — filter by sector
- `from_date` (date, optional)
- `page` (int, default: 1)
- `limit` (int, default: 20, max: 100)

**Response:**
```json
{
  "total": 142,
  "page": 1,
  "signals": [
    {
      "id": 1923,
      "symbol": "TATAPOWER",
      "company_name": "Tata Power Company Ltd",
      "sector": "Power",
      "signal_type": "ORDER_WIN",
      "score": 87,
      "title": "Tata Power wins ₹2,800Cr solar project order from NTPC",
      "summary": "Management disclosed a large-ticket renewable order that represents ~18% of FY24 revenue. Order pipeline strengthens the FY26 guidance of 40% revenue growth.",
      "signal_date": "2026-03-25T14:30:00+05:30",
      "source_url": "https://nseindia.com/..."
    }
  ]
}
```

---

### Stock Signals

```
GET /signals/stock/{symbol}
```
All signals for a specific stock, last 90 days.

**Response:**
```json
{
  "symbol": "TATAPOWER",
  "company_name": "Tata Power Company Ltd",
  "signals": [...]
}
```

---

### Daily Digest

```
GET /signals/digest
GET /signals/digest/{date}    (date format: 2026-03-25)
```

**Response:**
```json
{
  "date": "2026-03-25",
  "total_signals": 47,
  "top_signals": [...],
  "sector_breakdown": {
    "Banking": 12,
    "IT": 8,
    "Power": 5
  }
}
```

---

### Bulk & Block Deals

```
GET /signals/bulk-deals
```

**Query params:** `date`, `symbol`, `deal_type` (BULK/BLOCK), `min_volume_ratio`

**Response:**
```json
{
  "deals": [
    {
      "symbol": "ADANIPORTS",
      "deal_date": "2026-03-25",
      "deal_type": "BLOCK",
      "client_name": "MIRAE ASSET MF",
      "buy_sell": "BUY",
      "quantity": 5000000,
      "price": 1342.50,
      "deal_value_cr": 671.25,
      "volume_ratio": 8.3,
      "signal_score": 92
    }
  ]
}
```

---

### Insider Trades

```
GET /signals/insider-trades
```

**Query params:** `symbol`, `acquirer_type` (Promoter/Director/KMP), `trade_type` (BUY/SELL), `from_date`

---

## Module 2: Chart Pattern Intelligence

### Detected Patterns

```
GET /patterns/detected
```
Returns patterns detected in the last 24 hours across all stocks.

**Query params:**
- `symbol` (str, optional)
- `pattern_name` (str, optional)
- `timeframe` (str, default: "1D")
- `min_confidence` (int, default: 60)
- `sector` (str, optional)
- `watchlist_only` (bool, default: false) — filter by user's watchlist

**Response:**
```json
{
  "patterns": [
    {
      "id": 8821,
      "symbol": "TITAN",
      "company_name": "Titan Company Ltd",
      "sector": "Consumer Discretionary",
      "pattern_name": "BREAKOUT_52W_HIGH",
      "timeframe": "1D",
      "detected_at": "2026-03-25T19:00:00+05:30",
      "entry_price": 3542.00,
      "target_price": 3720.00,
      "stop_loss": 3485.00,
      "confidence_score": 84,
      "volume_confirmation": true,
      "plain_english": "Titan broke above its 52-week high of ₹3,530 today on volume that was 3.2x the normal daily average. This is a textbook momentum breakout — the stock had been consolidating for 3 months below this level, and today's move suggests institutional buying stepped in. Watch for the price to hold above ₹3,530 on a closing basis; if it does, the next resistance is around ₹3,720.",
      "backtest": {
        "win_rate": 71,
        "avg_gain_pct": 8.4,
        "avg_loss_pct": 3.1,
        "sample_size": 28,
        "expectancy": 4.1
      }
    }
  ]
}
```

---

### Stock Chart Data

```
GET /patterns/chart/{symbol}
```
Returns OHLCV data + all indicator values + detected patterns for charting.

**Query params:**
- `timeframe` (str, default: "1D")
- `days` (int, default: 180)

**Response:**
```json
{
  "symbol": "TITAN",
  "timeframe": "1D",
  "ohlcv": [
    { "time": 1742860800, "open": 3510, "high": 3562, "low": 3498, "close": 3542, "volume": 1842000 }
  ],
  "indicators": {
    "sma_20": [{ "time": 1742860800, "value": 3420 }],
    "sma_50": [...],
    "rsi_14": [...],
    "volume_sma_20": [...]
  },
  "patterns": [
    {
      "time": 1742860800,
      "pattern_name": "BREAKOUT_52W_HIGH",
      "direction": "bullish",
      "entry": 3542,
      "target": 3720,
      "stop": 3485
    }
  ]
}
```

---

### Pattern Backtest Stats

```
GET /patterns/backtest/{symbol}/{pattern_name}
```

**Query params:** `timeframe` (default: "1D")

**Response:**
```json
{
  "symbol": "TITAN",
  "pattern_name": "BREAKOUT_52W_HIGH",
  "timeframe": "1D",
  "sample_size": 28,
  "win_rate": 71.4,
  "avg_gain_pct": 8.4,
  "avg_loss_pct": 3.1,
  "best_gain_pct": 24.1,
  "worst_loss_pct": -7.8,
  "avg_holding_days": 10,
  "expectancy": 4.1,
  "last_computed": "2026-03-24T23:00:00+05:30"
}
```

---

### Pattern Scanner Heatmap

```
GET /patterns/heatmap
```
Sector-wise pattern activity for the dashboard heatmap.

**Response:**
```json
{
  "sectors": [
    {
      "sector": "Banking",
      "bullish_patterns": 12,
      "bearish_patterns": 3,
      "top_stocks": ["HDFCBANK", "KOTAKBANK"]
    }
  ]
}
```

---

## User / Watchlist

```
GET    /user/watchlist
POST   /user/watchlist          body: { "symbol": "RELIANCE" }
DELETE /user/watchlist/{symbol}
```

```
GET    /user/alerts
POST   /user/alerts             body: { "symbol": null, "signal_types": [], "min_score": 60 }
PUT    /user/alerts/{id}
DELETE /user/alerts/{id}
```

---

## Stocks

```
GET /stocks/search?q=tata           → fuzzy search by name or symbol
GET /stocks/{symbol}                → company info, sector, market cap
GET /stocks/{symbol}/fundamentals   → quarterly results, ratios
GET /stocks/{symbol}/shareholding   → promoter/FII/DII/retail breakdown
```

---

## WebSocket

```
WS /ws/{user_id}?token={jwt_token}
```

Messages pushed from server:

```json
// New high-score signal
{
  "type": "signal",
  "symbol": "TATAPOWER",
  "score": 87,
  "title": "Tata Power wins ₹2,800Cr order",
  "signal_type": "ORDER_WIN"
}

// New pattern detected on watchlist stock
{
  "type": "pattern",
  "symbol": "TITAN",
  "pattern_name": "BREAKOUT_52W_HIGH",
  "confidence_score": 84
}

// Market alert (circuit, halt, index move)
{
  "type": "market_alert",
  "message": "Nifty 50 down 2% — broad-based selling"
}
```

---

## Error Responses

All errors follow:
```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "status": 400
}
```

Common codes:
- `SYMBOL_NOT_FOUND` — stock symbol not in our universe
- `INSUFFICIENT_DATA` — not enough historical data for backtest
- `RATE_LIMITED` — too many requests
- `UNAUTHORIZED` — invalid or expired JWT
