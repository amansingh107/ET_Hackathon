# Frontend

Next.js 14 (App Router), TypeScript, TailwindCSS, TradingView Lightweight Charts.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                   # Root layout (navbar, sidebar, WebSocket init)
│   ├── page.tsx                     # Dashboard redirect
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/
│   │   └── page.tsx                 # Main dashboard
│   ├── radar/
│   │   └── page.tsx                 # Opportunity Radar full view
│   ├── charts/
│   │   ├── page.tsx                 # Pattern Intelligence dashboard
│   │   └── [symbol]/page.tsx        # Individual stock chart view
│   ├── watchlist/
│   │   └── page.tsx
│   └── alerts/
│       └── page.tsx
├── components/
│   ├── radar/
│   │   ├── SignalFeed.tsx            # Live signal feed with scores
│   │   ├── SignalCard.tsx            # Individual signal card
│   │   ├── BulkDealTable.tsx         # Bulk/block deals table
│   │   ├── InsiderTradeTable.tsx
│   │   └── SectorHeatmap.tsx        # Sector activity heatmap
│   ├── charts/
│   │   ├── StockChart.tsx           # TradingView chart with pattern overlays
│   │   ├── PatternCard.tsx          # Detected pattern card with explanation
│   │   ├── BacktestStats.tsx        # Win rate, avg gain/loss display
│   │   ├── PatternHeatmap.tsx       # NSE-wide pattern activity
│   │   └── IndicatorPanel.tsx       # RSI, MACD sub-charts
│   ├── shared/
│   │   ├── StockSearch.tsx          # Autocomplete stock search
│   │   ├── ScoreBadge.tsx           # Color-coded 0-100 score badge
│   │   ├── SignalTypeBadge.tsx      # Signal type pill (ORDER_WIN, etc.)
│   │   ├── AlertBell.tsx            # Live alert notification bell
│   │   └── SectorBadge.tsx
│   └── layout/
│       ├── Navbar.tsx
│       ├── Sidebar.tsx
│       └── WebSocketProvider.tsx    # Global WS connection
├── lib/
│   ├── api.ts                       # API client (typed fetch wrappers)
│   ├── websocket.ts                 # WebSocket singleton
│   └── formatters.ts                # ₹ formatting, date, % etc.
├── hooks/
│   ├── useSignals.ts
│   ├── usePatterns.ts
│   ├── useWatchlist.ts
│   └── useAlerts.ts
├── store/
│   └── alertStore.ts                # Zustand store for live alerts
└── types/
    ├── signal.ts
    ├── pattern.ts
    └── stock.ts
```

---

## Key Pages

### Dashboard (`/dashboard`)

```
┌─────────────────────────────────────────────────────────────┐
│  Top Signals Today          │  Pattern Activity              │
│  ┌──────────────────────┐   │  ┌──────────────────────────┐  │
│  │ 🔴 87  TATAPOWER     │   │  │  Sector Heatmap          │  │
│  │ ORDER_WIN            │   │  │  [Banking: 12 patterns]  │  │
│  │ ₹2,800Cr solar order │   │  │  [IT: 8 patterns]        │  │
│  └──────────────────────┘   │  │  [Power: 5 patterns]     │  │
│  ┌──────────────────────┐   │  └──────────────────────────┘  │
│  │ 🟠 75  TITAN         │   │                                │
│  │ BREAKOUT_52W_HIGH    │   │  Today's Top Breakouts         │
│  │ Vol: 3.2x avg        │   │  ┌──────────────────────────┐  │
│  └──────────────────────┘   │  │ TITAN  ₹3,542  +1.8%     │  │
│                             │  │ 71% historical win rate  │  │
│  Bulk Deals Today           │  └──────────────────────────┘  │
│  [Table]                    │                                │
└─────────────────────────────────────────────────────────────┘
```

---

### Opportunity Radar (`/radar`)

Full-page signal feed with filters:

```
Filters: [All Sectors ▼] [All Signal Types ▼] [Score: 50+] [Today ▼]

Signal #1 — Score: 87                              2:30 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TATAPOWER  |  Power  |  ORDER_WIN

Tata Power wins ₹2,800Cr solar project order from NTPC

Management disclosed a large-ticket renewable order that represents ~18%
of FY24 revenue. Order pipeline strengthens the FY26 guidance of 40%
revenue growth.

[View Filing]  [Add to Watchlist]  [View Chart →]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Stock Chart View (`/charts/[symbol]`)

```
TITAN  ₹3,542  +1.8% ▲              [1D] [1W] [1M] [3M] [1Y] [5Y]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│                                                              │
│            [TradingView Lightweight Chart]                   │
│              OHLCV Candlesticks                              │
│              SMA 20 / 50 / 200 overlays                     │
│              Pattern markers (▲ for bullish, ▼ for bearish)  │
│              Support/Resistance lines                         │
│                                                              │
│  [RSI sub-chart]                                            │
│  [Volume bar chart]                                          │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detected Patterns Today
┌──────────────────────────────────────────────────────────┐
│  52-Week High Breakout  |  Confidence: 84  |  Vol: ✓    │
│                                                          │
│  "Titan broke above its 52-week high of ₹3,530 today    │
│  on volume that was 3.2x the normal daily average..."   │
│                                                          │
│  Historical on TITAN (28 occurrences, 5 years):         │
│  Win Rate: 71%  |  Avg Gain: +8.4%  |  Avg Loss: -3.1%  │
│  Entry: ₹3,542  Target: ₹3,720  Stop: ₹3,485           │
└──────────────────────────────────────────────────────────┘
```

---

## StockChart Component

```tsx
// components/charts/StockChart.tsx
"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
} from "lightweight-charts";

interface OHLCVBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PatternMarker {
  time: number;
  pattern_name: string;
  direction: "bullish" | "bearish";
  entry: number;
  target: number;
  stop: number;
}

interface Props {
  symbol: string;
  ohlcv: OHLCVBar[];
  sma20: { time: number; value: number }[];
  sma50: { time: number; value: number }[];
  sma200: { time: number; value: number }[];
  rsi: { time: number; value: number }[];
  patterns: PatternMarker[];
}

export function StockChart({ symbol, ohlcv, sma20, sma50, sma200, rsi, patterns }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chart.current = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
      },
    });

    const candleSeries = chart.current.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    candleSeries.setData(ohlcv);

    // SMA overlays
    const sma20Series = chart.current.addLineSeries({ color: "#3b82f6", lineWidth: 1 });
    sma20Series.setData(sma20);

    const sma50Series = chart.current.addLineSeries({ color: "#f59e0b", lineWidth: 1 });
    sma50Series.setData(sma50);

    const sma200Series = chart.current.addLineSeries({ color: "#8b5cf6", lineWidth: 2 });
    sma200Series.setData(sma200);

    // Pattern markers
    const markers = patterns.map((p) => ({
      time: p.time,
      position: p.direction === "bullish" ? "belowBar" : "aboveBar",
      color: p.direction === "bullish" ? "#22c55e" : "#ef4444",
      shape: p.direction === "bullish" ? "arrowUp" : "arrowDown",
      text: p.pattern_name.replace(/_/g, " "),
    }));
    candleSeries.setMarkers(markers);

    return () => chart.current?.remove();
  }, [ohlcv, patterns]);

  return (
    <div className="rounded-xl bg-slate-900 p-4">
      <div ref={chartRef} className="w-full" />
    </div>
  );
}
```

---

## SignalCard Component

```tsx
// components/radar/SignalCard.tsx
import { Signal } from "@/types/signal";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { SignalTypeBadge } from "@/components/shared/SignalTypeBadge";

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className="border border-slate-700 rounded-xl p-4 bg-slate-900 hover:border-slate-500 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <ScoreBadge score={signal.score} />
          <div>
            <span className="font-bold text-white">{signal.symbol}</span>
            <span className="text-slate-400 text-sm ml-2">{signal.company_name}</span>
          </div>
          <SignalTypeBadge type={signal.signal_type} />
        </div>
        <span className="text-slate-500 text-xs whitespace-nowrap">
          {formatTime(signal.signal_date)}
        </span>
      </div>

      <p className="mt-2 text-white font-medium">{signal.title}</p>
      <p className="mt-1 text-slate-400 text-sm leading-relaxed">{signal.summary}</p>

      <div className="mt-3 flex gap-2">
        <a href={signal.source_url} target="_blank"
           className="text-xs text-blue-400 hover:text-blue-300">
          View Filing →
        </a>
        <button className="text-xs text-slate-400 hover:text-white">
          + Watchlist
        </button>
        <a href={`/charts/${signal.symbol}`}
           className="text-xs text-slate-400 hover:text-white ml-auto">
          View Chart →
        </a>
      </div>
    </div>
  );
}
```

---

## ScoreBadge Component

```tsx
// components/shared/ScoreBadge.tsx
export function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 75 ? "bg-red-500 text-white" :
    score >= 60 ? "bg-orange-500 text-white" :
    score >= 40 ? "bg-yellow-500 text-black" :
    "bg-slate-600 text-slate-300";

  return (
    <span className={`${color} text-xs font-bold rounded-md px-2 py-1 min-w-[2.5rem] text-center`}>
      {score}
    </span>
  );
}
```

---

## WebSocket Provider

```tsx
// components/layout/WebSocketProvider.tsx
"use client";
import { useEffect } from "react";
import { useAlertStore } from "@/store/alertStore";
import { getToken } from "@/lib/auth";

export function WebSocketProvider({ userId }: { userId: string }) {
  const addAlert = useAlertStore((s) => s.addAlert);

  useEffect(() => {
    const token = getToken();
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${userId}?token=${token}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "signal" || msg.type === "pattern") {
        addAlert(msg);
        // Browser notification if permitted
        if (Notification.permission === "granted") {
          new Notification(`${msg.symbol} — Score ${msg.score}`, {
            body: msg.title,
            icon: "/favicon.ico",
          });
        }
      }
    };

    return () => ws.close();
  }, [userId]);

  return null;
}
```

---

## package.json Dependencies

```json
{
  "dependencies": {
    "next": "14.2.3",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "typescript": "5.4.5",
    "tailwindcss": "3.4.3",
    "lightweight-charts": "4.1.7",
    "recharts": "2.12.7",
    "swr": "2.2.5",
    "zustand": "4.5.2",
    "socket.io-client": "4.7.5",
    "date-fns": "3.6.0",
    "clsx": "2.1.1"
  }
}
```
