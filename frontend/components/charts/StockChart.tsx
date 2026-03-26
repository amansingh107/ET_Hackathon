"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, CandlestickData, Time } from "lightweight-charts";
import { OHLCVBar } from "@/types/stock";
import { Pattern } from "@/types/pattern";

const BULLISH = new Set([
  "BULLISH_ENGULFING","HAMMER","BREAKOUT_52W_HIGH","BREAKOUT_RESISTANCE",
  "GOLDEN_CROSS","BULLISH_DIVERGENCE_RSI","BULLISH_DIVERGENCE_MACD","DOUBLE_BOTTOM",
]);

interface Props {
  ohlcv: OHLCVBar[];
  patterns?: Pattern[];
}

function toUnixDay(iso: string): Time {
  // lightweight-charts expects "YYYY-MM-DD" for day bars
  return iso.slice(0, 10) as Time;
}

export function StockChart({ ohlcv, patterns = [] }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current || ohlcv.length === 0) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 420,
      layout: { background: { color: "#0f172a" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: false },
    });
    chartRef.current = chart;

    const candles = ohlcv
      .filter((b) => b.open && b.high && b.low && b.close)
      .map((b) => ({
        time: toUnixDay(b.time),
        open: b.open!,
        high: b.high!,
        low: b.low!,
        close: b.close!,
      }))
      .sort((a, b) => (a.time < b.time ? -1 : 1));

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e", downColor: "#ef4444",
      borderVisible: false, wickUpColor: "#22c55e", wickDownColor: "#ef4444",
    });
    candleSeries.setData(candles as CandlestickData[]);

    // SMA 20
    const sma20 = chart.addLineSeries({ color: "#3b82f6", lineWidth: 1, title: "SMA20" });
    const closes = candles.map((c) => c.close);
    sma20.setData(
      candles.slice(19).map((c, i) => ({
        time: c.time,
        value: closes.slice(i, i + 20).reduce((a, b) => a + b, 0) / 20,
      }))
    );

    // Pattern markers
    if (patterns.length > 0) {
      const markers = patterns
        .filter((p) => p.entry_price)
        .map((p) => ({
          time: toUnixDay(p.detected_at),
          position: BULLISH.has(p.pattern_name) ? ("belowBar" as const) : ("aboveBar" as const),
          color: BULLISH.has(p.pattern_name) ? "#22c55e" : "#ef4444",
          shape: BULLISH.has(p.pattern_name) ? ("arrowUp" as const) : ("arrowDown" as const),
          text: p.pattern_name.replace(/_/g, " "),
        }))
        .sort((a, b) => (a.time < b.time ? -1 : 1));
      candleSeries.setMarkers(markers);
    }

    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      chart.applyOptions({ width: ref.current!.clientWidth });
    });
    observer.observe(ref.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [ohlcv, patterns]);

  return <div ref={ref} className="w-full rounded-lg overflow-hidden" />;
}
