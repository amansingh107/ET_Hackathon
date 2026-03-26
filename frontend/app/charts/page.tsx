import { api } from "@/lib/api";
import { PatternCard } from "@/components/charts/PatternCard";
import Link from "next/link";

export const revalidate = 60;

export default async function ChartsPage() {
  const patterns = await api.patterns.today(50).catch(() => []);

  // Group by symbol
  const bySymbol: Record<string, typeof patterns> = {};
  for (const p of patterns) {
    (bySymbol[p.symbol] ??= []).push(p);
  }
  const symbols = Object.keys(bySymbol).sort(
    (a, b) =>
      Math.max(...bySymbol[b].map((p) => p.confidence_score)) -
      Math.max(...bySymbol[a].map((p) => p.confidence_score))
  );

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Chart Pattern Intelligence</h1>
        <p className="text-slate-400 text-sm mt-1">
          {patterns.length} patterns across {symbols.length} stocks · with backtested win rates
        </p>
      </div>

      {symbols.length === 0 ? (
        <div className="text-slate-500 text-sm bg-slate-900 rounded-xl p-8 text-center">
          No patterns yet. Seed OHLCV data and run the pattern scanner.
        </div>
      ) : (
        <div className="space-y-8">
          {symbols.map((symbol) => (
            <div key={symbol}>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-white">{symbol}</h2>
                <Link
                  href={`/charts/${symbol}`}
                  className="text-blue-400 text-sm hover:text-blue-300"
                >
                  View chart →
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {bySymbol[symbol].map((p) => (
                  <PatternCard key={p.id} pattern={p} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
