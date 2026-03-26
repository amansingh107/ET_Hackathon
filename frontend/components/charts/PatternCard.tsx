import { Pattern } from "@/types/pattern";
import { fmt } from "@/lib/formatters";
import clsx from "clsx";

const BULLISH_PATTERNS = new Set([
  "BULLISH_ENGULFING", "HAMMER", "MORNING_STAR", "THREE_WHITE_SOLDIERS",
  "BREAKOUT_52W_HIGH", "BREAKOUT_RESISTANCE", "GOLDEN_CROSS",
  "BULLISH_DIVERGENCE_RSI", "BULLISH_DIVERGENCE_MACD", "DOUBLE_BOTTOM",
  "INVERSE_HEAD_SHOULDERS",
]);

export function PatternCard({ pattern }: { pattern: Pattern }) {
  const bullish = BULLISH_PATTERNS.has(pattern.pattern_name);

  return (
    <div className={clsx(
      "border rounded-xl p-4 bg-slate-900",
      bullish ? "border-green-800 hover:border-green-600" : "border-red-900 hover:border-red-700",
      "transition-colors"
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={clsx(
            "text-lg font-bold",
            bullish ? "text-green-400" : "text-red-400"
          )}>
            {bullish ? "▲" : "▼"}
          </span>
          <div>
            <p className="font-bold text-white">{fmt.patternLabel(pattern.pattern_name)}</p>
            <p className="text-slate-400 text-xs">{pattern.symbol} · {pattern.timeframe}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-white font-bold text-sm">
            Conf: {pattern.confidence_score}
            {pattern.volume_confirmation && (
              <span className="ml-1 text-xs text-green-400">Vol✓</span>
            )}
          </p>
          {pattern.backtest_win_rate != null && (
            <p className="text-slate-400 text-xs">
              {pattern.backtest_win_rate.toFixed(0)}% win · {pattern.backtest_sample_size} samples
            </p>
          )}
        </div>
      </div>

      {pattern.plain_english && (
        <p className="mt-3 text-slate-300 text-sm leading-relaxed line-clamp-4">
          {pattern.plain_english}
        </p>
      )}

      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div className="bg-slate-800 rounded p-2 text-center">
          <p className="text-slate-400">Entry</p>
          <p className="text-white font-medium">{fmt.price(pattern.entry_price)}</p>
        </div>
        <div className="bg-slate-800 rounded p-2 text-center">
          <p className="text-green-400">Target</p>
          <p className="text-white font-medium">{fmt.price(pattern.target_price)}</p>
        </div>
        <div className="bg-slate-800 rounded p-2 text-center">
          <p className="text-red-400">Stop</p>
          <p className="text-white font-medium">{fmt.price(pattern.stop_loss)}</p>
        </div>
      </div>
    </div>
  );
}
