export interface Pattern {
  id: number;
  symbol: string;
  pattern_name: string;
  timeframe: string;
  detected_at: string;
  entry_price: number | null;
  target_price: number | null;
  stop_loss: number | null;
  confidence_score: number;
  volume_confirmation: boolean;
  plain_english: string | null;
  backtest_win_rate: number | null;
  backtest_avg_gain: number | null;
  backtest_sample_size: number | null;
}

export interface BacktestStats {
  pattern_name: string;
  timeframe: string;
  sample_size: number;
  win_rate: number | null;
  avg_gain_pct: number | null;
  avg_loss_pct: number | null;
  avg_holding_days: number | null;
  best_gain_pct: number | null;
  worst_loss_pct: number | null;
}
