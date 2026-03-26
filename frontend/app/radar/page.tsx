import { api } from "@/lib/api";
import { SignalCard } from "@/components/radar/SignalCard";

export const revalidate = 30;

export default async function RadarPage({
  searchParams,
}: {
  searchParams: { min_score?: string; hours?: string };
}) {
  const min_score = Number(searchParams.min_score ?? 40);
  const hours = Number(searchParams.hours ?? 168);

  const signals = await api.signals.list({ min_score, hours, limit: 100 }).catch(() => []);

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Opportunity Radar</h1>
          <p className="text-slate-400 text-sm mt-1">
            {signals.length} signals · sorted by conviction score
          </p>
        </div>

        {/* Filters */}
        <form method="GET" className="flex gap-3 items-center">
          <label className="text-slate-400 text-xs">Min score</label>
          <select
            name="min_score"
            defaultValue={min_score}
            className="bg-slate-800 border border-slate-700 text-white text-xs rounded px-2 py-1"
          >
            {[40, 50, 60, 70, 80].map((v) => (
              <option key={v} value={v}>{v}+</option>
            ))}
          </select>
          <label className="text-slate-400 text-xs">Period</label>
          <select
            name="hours"
            defaultValue={hours}
            className="bg-slate-800 border border-slate-700 text-white text-xs rounded px-2 py-1"
          >
            <option value={24}>24h</option>
            <option value={48}>48h</option>
            <option value={168}>7 days</option>
          </select>
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded"
          >
            Apply
          </button>
        </form>
      </div>

      <div className="space-y-3">
        {signals.length === 0 ? (
          <div className="text-slate-500 text-sm bg-slate-900 rounded-xl p-8 text-center">
            No signals found. Try lowering the min score or increasing the period.
          </div>
        ) : (
          signals.map((s) => <SignalCard key={s.id} signal={s} />)
        )}
      </div>
    </div>
  );
}
