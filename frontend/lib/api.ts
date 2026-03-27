// Server components need the full URL; browser can use relative
const BASE =
  typeof window === "undefined"
    ? "http://localhost:8000/api/v1"
    : "/api/v1";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

// --- Signals ---
export const api = {
  signals: {
    list: (params?: { min_score?: number; hours?: number; limit?: number }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString();
      return get<import("@/types/signal").Signal[]>(`/signals?${q}`);
    },
    top: (params?: { min_score?: number; hours?: number }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString();
      return get<import("@/types/signal").Signal[]>(`/signals/top?${q}`);
    },
    digest: () => get<import("@/types/signal").SignalDigest>("/signals/digest"),
    compounded: (symbol: string) =>
      get<import("@/types/signal").CompoundedScore>(`/signals/${symbol}/compounded`),
  },

  patterns: {
    today: (min_confidence?: number) =>
      get<import("@/types/pattern").Pattern[]>(
        `/patterns/today?min_confidence=${min_confidence ?? 50}`
      ),
    forSymbol: (symbol: string) =>
      get<import("@/types/pattern").Pattern[]>(`/patterns/${symbol}`),
    backtest: (symbol: string) =>
      get<import("@/types/pattern").BacktestStats[]>(`/patterns/${symbol}/backtest`),
  },

  stocks: {
    list: (params?: { limit?: number; sector?: string }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString();
      return get<import("@/types/stock").Stock[]>(`/stocks?${q}`);
    },
    get: (symbol: string) => get<import("@/types/stock").Stock>(`/stocks/${symbol}`),
    ohlcv: (symbol: string, days?: number) =>
      get<import("@/types/stock").OHLCVBar[]>(`/stocks/${symbol}/ohlcv?days=${days ?? 90}`),
    filings: (symbol: string) => get(`/stocks/${symbol}/filings`),
  },
};
