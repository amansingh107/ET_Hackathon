export interface Signal {
  id: number;
  symbol: string;
  signal_type: string;
  score: number;
  title: string;
  summary: string;
  signal_date: string;
  data: Record<string, unknown> | null;
}

export interface SignalDigest {
  date: string;
  total_signals: number;
  top_signals: Signal[];
  by_type: Record<string, string[]>;
}

export interface CompoundedScore {
  symbol: string;
  compounded_score: number | null;
  signal_count: number;
  signals: Signal[];
}
