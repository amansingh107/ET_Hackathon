import clsx from "clsx";
import { fmt } from "@/lib/formatters";

const TYPE_COLORS: Record<string, string> = {
  BULK_DEAL_UNUSUAL:        "bg-blue-900 text-blue-300",
  INSIDER_BUY_CLUSTER:      "bg-green-900 text-green-300",
  INSIDER_SELL_CLUSTER:     "bg-red-900 text-red-300",
  RESULTS_BEAT:             "bg-emerald-900 text-emerald-300",
  RESULTS_MISS:             "bg-rose-900 text-rose-300",
  ORDER_WIN:                "bg-purple-900 text-purple-300",
  GUIDANCE_UPGRADE:         "bg-teal-900 text-teal-300",
  GUIDANCE_DOWNGRADE:       "bg-orange-900 text-orange-300",
  PROMOTER_BUY:             "bg-indigo-900 text-indigo-300",
  PROMOTER_SELL:            "bg-pink-900 text-pink-300",
  MANAGEMENT_TONE_POSITIVE: "bg-cyan-900 text-cyan-300",
  MANAGEMENT_TONE_NEGATIVE: "bg-amber-900 text-amber-300",
  REGULATORY_ACTION:        "bg-red-900 text-red-300",
  FILING_ANOMALY:           "bg-yellow-900 text-yellow-300",
};

export function SignalTypeBadge({ type }: { type: string }) {
  return (
    <span
      className={clsx(
        "text-xs font-medium rounded px-2 py-0.5",
        TYPE_COLORS[type] ?? "bg-slate-700 text-slate-300"
      )}
    >
      {fmt.signalLabel(type)}
    </span>
  );
}
