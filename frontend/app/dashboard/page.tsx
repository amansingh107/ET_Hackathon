import { api } from "@/lib/api";
import { SignalCard } from "@/components/radar/SignalCard";
import { PatternCard } from "@/components/charts/PatternCard";
import Link from "next/link";

export const revalidate = 60;

export default async function DashboardPage() {
  let digest = null;
  let patterns: Awaited<ReturnType<typeof api.patterns.today>> = [];
  let digestError = "";
  let patternsError = "";

  try {
    digest = await api.signals.digest();
  } catch (e: unknown) {
    digestError = e instanceof Error ? e.message : String(e);
  }

  try {
    patterns = await api.patterns.today(50);
  } catch (e: unknown) {
    patternsError = e instanceof Error ? e.message : String(e);
  }

  const topSignals = digest?.top_signals?.slice(0, 6) ?? [];
  const topPatterns = patterns.slice(0, 6);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">
            {digest?.total_signals ?? 0} signals today · {patterns.length} patterns detected
          </p>
        </div>
        <div className="text-xs text-slate-500">
          {new Date().toLocaleDateString("en-IN", { dateStyle: "long" })}
        </div>
      </div>

      {/* API error banners */}
      {digestError && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-3 text-sm text-red-300">
          Signals API error: {digestError}
        </div>
      )}
      {patternsError && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-3 text-sm text-red-300">
          Patterns API error: {patternsError}
        </div>
      )}

      {/* Signal type summary pills */}
      {digest?.by_type && Object.keys(digest.by_type).length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(digest.by_type).map(([type, symbols]) => (
            <div key={type} className="bg-slate-800 rounded-lg px-3 py-1.5 text-xs">
              <span className="text-slate-400">{type.replace(/_/g, " ")}: </span>
              <span className="text-white font-medium">{(symbols as string[]).join(", ")}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top Signals */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Top Signals Today</h2>
            <Link href="/radar" className="text-blue-400 text-sm hover:text-blue-300">
              View all →
            </Link>
          </div>
          {topSignals.length === 0 ? (
            <div className="text-slate-500 text-sm bg-slate-900 rounded-xl p-6 text-center">
              No signals yet.{" "}
              <code className="text-xs text-slate-400">
                python3 scripts/seed_test_signals.py
              </code>
            </div>
          ) : (
            <div className="space-y-3">
              {topSignals.map((s) => (
                <SignalCard key={s.id} signal={s} />
              ))}
            </div>
          )}
        </div>

        {/* Top Patterns */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Patterns Detected</h2>
            <Link href="/charts" className="text-blue-400 text-sm hover:text-blue-300">
              View all →
            </Link>
          </div>
          {topPatterns.length === 0 ? (
            <div className="text-slate-500 text-sm bg-slate-900 rounded-xl p-6 text-center">
              No patterns yet.{" "}
              <code className="text-xs text-slate-400">
                curl -X POST .../ingest/patterns/scan/RELIANCE
              </code>
            </div>
          ) : (
            <div className="space-y-3">
              {topPatterns.map((p) => (
                <PatternCard key={p.id} pattern={p} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
