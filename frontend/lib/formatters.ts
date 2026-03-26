import { formatDistanceToNow } from "date-fns";

export const fmt = {
  price: (n: number | null) =>
    n == null ? "—" : `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`,

  pct: (n: number | null) =>
    n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`,

  timeAgo: (iso: string) =>
    formatDistanceToNow(new Date(iso), { addSuffix: true }),

  patternLabel: (name: string) =>
    name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),

  signalLabel: (type: string) =>
    type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
};
