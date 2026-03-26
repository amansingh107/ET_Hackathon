import { api } from "@/lib/api";
import { PatternCard } from "@/components/charts/PatternCard";
import { StockChart } from "@/components/charts/StockChart";
import { fmt } from "@/lib/formatters";
import Link from "next/link";

export const revalidate = 60;

export default async function StockChartPage({
  params,
}: {
  params: { symbol: string };
}) {
  const symbol = params.symbol.toUpperCase();

  const [stock, ohlcv, patterns, compounded] = await Promise.all([
    api.stocks.get(symbol).catch(() => null),
    api.stocks.ohlcv(symbol, 180).catch(() => []),
    api.patterns.forSymbol(symbol).catch(() => []),
    api.signals.compounded(symbol).catch(() => null),
  ]);

  const latest = ohlcv[0]; // API returns DESC order

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      {/* Stock header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white">{symbol}</h1>
            {stock && (
              <span className="text-slate-400 text-sm">{stock.company_name}</span>
            )}
            {stock?.sector && (
              <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">
                {stock.sector}
              </span>
            )}
          </div>
          {latest && (
            <p className="text-2xl font-semibold text-white mt-1">
              {fmt.price(latest.close)}
            </p>
          )}
        </div>
        {compounded?.compounded_score != null && (
          <div className="bg-slate-800 rounded-xl p-4 text-center">
            <p className="text-slate-400 text-xs">Conviction Score</p>
            <p className="text-4xl font-bold text-white mt-1">
              {compounded.compounded_score}
            </p>
            <p className="text-slate-500 text-xs mt-1">
              {compounded.signal_count} signal{compounded.signal_count !== 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="bg-slate-900 rounded-xl p-4">
        <StockChart ohlcv={ohlcv} patterns={patterns} />
      </div>

      {/* Patterns */}
      {patterns.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">
            Detected Patterns
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {patterns.map((p) => <PatternCard key={p.id} pattern={p} />)}
          </div>
        </div>
      )}

      {/* Signals */}
      {compounded?.signals && compounded.signals.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-3">Recent Signals</h2>
          <div className="space-y-2">
            {compounded.signals.map((s) => (
              <div key={s.id} className="bg-slate-900 border border-slate-700 rounded-lg p-3 flex gap-3">
                <span className="text-white font-bold tabular-nums text-sm">{s.score}</span>
                <div>
                  <p className="text-white text-sm font-medium">{s.title}</p>
                  <p className="text-slate-400 text-xs mt-0.5 line-clamp-2">{s.summary}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Link href="/charts" className="text-slate-400 text-sm hover:text-white">
        ← Back to patterns
      </Link>
    </div>
  );
}
