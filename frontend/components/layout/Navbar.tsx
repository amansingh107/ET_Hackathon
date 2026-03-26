import Link from "next/link";

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 bg-slate-900 border-b border-slate-700 flex items-center px-6 gap-8">
      <Link href="/dashboard" className="font-bold text-white text-lg tracking-tight">
        ET Investor AI
      </Link>
      <div className="flex gap-6 text-sm">
        <Link href="/dashboard" className="text-slate-300 hover:text-white transition-colors">
          Dashboard
        </Link>
        <Link href="/radar" className="text-slate-300 hover:text-white transition-colors">
          Opportunity Radar
        </Link>
        <Link href="/charts" className="text-slate-300 hover:text-white transition-colors">
          Chart Patterns
        </Link>
      </div>
      <div className="ml-auto text-xs text-slate-500">NSE · Live Data</div>
    </nav>
  );
}
