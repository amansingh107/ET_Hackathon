"""
AMFI NAV Data Fetcher
Uses: Direct AMFI text file download

Fetches mutual fund NAV data from AMFI (Association of Mutual Funds in India).
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from io import StringIO

sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
import httpx
import pandas as pd

console = Console()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# AMFI NAV URL
AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


async def fetch_nav_data() -> str:
    """Fetch NAV data from AMFI."""
    console.print("\n[bold blue]Fetching AMFI NAV Data...[/bold blue]")

    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=60.0, follow_redirects=True
        ) as client:
            response = await client.get(AMFI_NAV_URL)

            if response.status_code == 200:
                console.print("[green]✓ Fetched NAV data[/green]")
                return response.text
            else:
                console.print(f"[yellow]Status {response.status_code}[/yellow]")
                return ""

    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        return ""


def parse_nav_data(raw_data: str) -> list:
    """Parse AMFI NAV text data into structured format."""
    if not raw_data:
        return []

    funds = []
    current_amc = ""
    current_category = ""

    lines = raw_data.strip().split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # AMC headers don't have semicolons
        if ";" not in line:
            # This is either AMC name or category
            if (
                line.startswith("Open Ended")
                or line.startswith("Close Ended")
                or line.startswith("Interval")
            ):
                current_category = line
            else:
                current_amc = line
            continue

        # Parse fund data line
        parts = line.split(";")
        if len(parts) >= 6:
            try:
                fund = {
                    "scheme_code": parts[0],
                    "isin_div_payout": parts[1] if len(parts) > 1 else "",
                    "isin_div_reinvest": parts[2] if len(parts) > 2 else "",
                    "scheme_name": parts[3] if len(parts) > 3 else "",
                    "nav": float(parts[4])
                    if parts[4] and parts[4] not in ["N.A.", "-"]
                    else None,
                    "date": parts[5] if len(parts) > 5 else "",
                    "amc": current_amc,
                    "category": current_category,
                }
                funds.append(fund)
            except (ValueError, IndexError):
                continue

    console.print(f"[green]✓ Parsed {len(funds)} mutual funds[/green]")
    return funds


def get_fund_stats(funds: list) -> dict:
    """Get statistics about the funds."""
    stats = {
        "total_funds": len(funds),
        "amcs": set(),
        "categories": {},
        "avg_nav": 0,
        "highest_nav": None,
        "lowest_nav": None,
    }

    navs = []
    for fund in funds:
        stats["amcs"].add(fund.get("amc", ""))

        category = fund.get("category", "Unknown")
        stats["categories"][category] = stats["categories"].get(category, 0) + 1

        nav = fund.get("nav")
        if nav and nav > 0:
            navs.append((nav, fund))

    if navs:
        navs.sort(key=lambda x: x[0])
        stats["lowest_nav"] = navs[0][1]
        stats["highest_nav"] = navs[-1][1]
        stats["avg_nav"] = sum(n[0] for n in navs) / len(navs)

    stats["total_amcs"] = len(stats["amcs"])
    stats["amcs"] = list(stats["amcs"])[:10]  # Just first 10 for display

    return stats


def search_funds(funds: list, query: str) -> list:
    """Search for funds by name."""
    query_lower = query.lower()
    return [f for f in funds if query_lower in f.get("scheme_name", "").lower()]


def get_funds_by_amc(funds: list, amc_name: str) -> list:
    """Get all funds from a specific AMC."""
    amc_lower = amc_name.lower()
    return [f for f in funds if amc_lower in f.get("amc", "").lower()]


def display_funds_table(funds: list, title: str = "Mutual Funds"):
    """Display funds in a table."""
    if not funds:
        console.print("[yellow]No funds to display[/yellow]")
        return

    table = Table(title=title)
    table.add_column("Code", style="cyan", width=8)
    table.add_column("Scheme Name", max_width=45)
    table.add_column("NAV", justify="right")
    table.add_column("Date", width=12)
    table.add_column("AMC", max_width=20)

    for fund in funds[:20]:
        nav = fund.get("nav")
        nav_str = f"₹{nav:,.4f}" if nav else "N/A"

        table.add_row(
            fund.get("scheme_code", "N/A"),
            fund.get("scheme_name", "N/A")[:45],
            nav_str,
            fund.get("date", "N/A"),
            fund.get("amc", "N/A")[:20],
        )

    console.print(table)

    if len(funds) > 20:
        console.print(f"[dim]... and {len(funds) - 20} more funds[/dim]")


def display_stats(stats: dict):
    """Display fund statistics."""
    console.print("\n[bold]AMFI NAV Statistics[/bold]")

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    table.add_row("Total Funds", f"{stats['total_funds']:,}")
    table.add_row("Total AMCs", str(stats["total_amcs"]))
    table.add_row("Average NAV", f"₹{stats['avg_nav']:,.2f}")

    if stats["highest_nav"]:
        table.add_row(
            "Highest NAV",
            f"₹{stats['highest_nav']['nav']:,.2f} ({stats['highest_nav']['scheme_name'][:30]}...)",
        )

    console.print(table)

    # Category breakdown
    console.print("\n[bold]Top Categories:[/bold]")
    sorted_cats = sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_cats[:10]:
        console.print(f"  {cat[:50]}: {count:,} funds")


def save_output(data, filename: str):
    """Save data to JSON file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"[dim]Saved to {filepath}[/dim]")


async def main_async():
    """Async main function."""
    console.print("[bold magenta]═══ AMFI NAV Data Test ═══[/bold magenta]")

    # Fetch raw data
    raw_data = await fetch_nav_data()

    if not raw_data:
        console.print("[red]Failed to fetch data[/red]")
        return False

    # Parse data
    funds = parse_nav_data(raw_data)

    # Get stats
    stats = get_fund_stats(funds)
    display_stats(stats)

    # Display sample funds
    display_funds_table(funds[:20], "Sample Funds (First 20)")

    # Search for specific funds
    console.print("\n[bold]Searching for 'Nifty 50 Index' funds...[/bold]")
    nifty_funds = search_funds(funds, "Nifty 50 Index")
    display_funds_table(nifty_funds, "Nifty 50 Index Funds")

    # Get funds from a specific AMC
    console.print("\n[bold]Getting HDFC Mutual Fund schemes...[/bold]")
    hdfc_funds = get_funds_by_amc(funds, "HDFC")
    display_funds_table(hdfc_funds[:15], "HDFC Mutual Fund Schemes")

    # Save output
    save_output(
        {
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_funds": stats["total_funds"],
                "total_amcs": stats["total_amcs"],
                "avg_nav": stats["avg_nav"],
            },
            "sample_funds": funds[:100],  # Save first 100 for sample
            "nifty_50_funds": nifty_funds,
        },
        "amfi_nav_data.json",
    )

    console.print("\n[bold green]═══ AMFI NAV Test Complete ═══[/bold green]")

    return True


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
