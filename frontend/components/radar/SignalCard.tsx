import Link from "next/link";
import { Signal } from "@/types/signal";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { SignalTypeBadge } from "@/components/shared/SignalTypeBadge";
import { fmt } from "@/lib/formatters";

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className="border border-slate-700 rounded-xl p-4 bg-slate-900 hover:border-slate-500 transition-colors">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <ScoreBadge score={signal.score} />
          <span className="font-bold text-white text-lg">{signal.symbol}</span>
          <SignalTypeBadge type={signal.signal_type} />
        </div>
        <span className="text-slate-500 text-xs">{fmt.timeAgo(signal.signal_date)}</span>
      </div>

      <p className="mt-2 text-white font-medium">{signal.title}</p>
      <p className="mt-1 text-slate-400 text-sm leading-relaxed line-clamp-3">{signal.summary}</p>

      <div className="mt-3 flex gap-4 text-xs">
        <Link href={`/charts/${signal.symbol}`} className="text-blue-400 hover:text-blue-300">
          View Chart →
        </Link>
      </div>
    </div>
  );
}
