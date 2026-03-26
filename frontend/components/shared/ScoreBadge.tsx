import clsx from "clsx";

export function ScoreBadge({ score }: { score: number }) {
  return (
    <span
      className={clsx(
        "text-xs font-bold rounded-md px-2 py-1 min-w-[2.5rem] text-center tabular-nums",
        score >= 75 ? "bg-red-500 text-white" :
        score >= 60 ? "bg-orange-500 text-white" :
        score >= 40 ? "bg-yellow-500 text-black" :
        "bg-slate-600 text-slate-300"
      )}
    >
      {score}
    </span>
  );
}
