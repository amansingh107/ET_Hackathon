export interface Stock {
  symbol: string;
  company_name: string;
  sector: string | null;
  industry: string | null;
  is_active: boolean;
}

export interface OHLCVBar {
  time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}
