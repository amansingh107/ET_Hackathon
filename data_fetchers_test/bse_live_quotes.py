"""
BSE Company Info Fetcher
Uses: bsedata library

Fetches company information and quotes from BSE.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Popular BSE stock codes (scrip codes)
# Format: {NSE_SYMBOL: BSE_CODE}
BSE_CODES = {
    "RELIANCE": "500325",
    "TCS": "532540",
    "HDFCBANK": "500180",
    "INFY": "500209",
    "ICICIBANK": "532174",
    "HINDUNILVR": "500696",
    "SBIN": "500112",
    "BHARTIARTL": "532454",
    "KOTAKBANK": "500247",
    "ITC": "500875",
    "LT": "500510",
    "AXISBANK": "532215",
    "WIPRO": "507685",
    "MARUTI": "532500",
    "TITAN": "500114",
    "TATAPOWER": "500400",
}


def get_bse_client():
    """Initialize BSE client."""
    try:
        from bsedata.bse import BSE

        bse = BSE(update_codes=True)
        console.print("[green]✓ BSE client initialized[/green]")
        return bse
    except Exception as e:
        console.print(f"[red]Failed to initialize BSE client: {e}[/red]")
        return None


def fetch_company_quote(bse, scrip_code: str) -> dict:
    """Fetch quote for a company using BSE scrip code."""
    console.print(f"\n[bold blue]Fetching BSE quote for {scrip_code}...[/bold blue]")

    try:
        quote = bse.getQuote(scrip_code)

        if quote:
            console.print(
                f"[green]✓ Got quote for {quote.get('companyName', scrip_code)}[/green]"
            )
            return quote
        else:
            console.print(f"[yellow]No quote data for {scrip_code}[/yellow]")
            return {}

    except Exception as e:
        console.print(f"[red]Failed to fetch quote: {e}[/red]")
        return {}


def fetch_top_gainers(bse) -> list:
    """Fetch top gainers from BSE."""
    console.print("\n[bold blue]Fetching BSE Top Gainers...[/bold blue]")

    try:
        gainers = bse.topGainers()
        console.print(f"[green]✓ Fetched {len(gainers)} top gainers[/green]")
        return gainers
    except Exception as e:
        console.print(f"[red]Failed to fetch gainers: {e}[/red]")
        return []


def fetch_top_losers(bse) -> list:
    """Fetch top losers from BSE."""
    console.print("\n[bold blue]Fetching BSE Top Losers...[/bold blue]")

    try:
        losers = bse.topLosers()
        console.print(f"[green]✓ Fetched {len(losers)} top losers[/green]")
        return losers
    except Exception as e:
        console.print(f"[red]Failed to fetch losers: {e}[/red]")
        return []


def display_quote_details(quote: dict):
    """Display detailed quote information."""
    if not quote:
        return

    console.print(f"\n[bold]Quote Details: {quote.get('companyName', 'N/A')}[/bold]")

    table = Table(show_header=False, box=None)
    table.add_column("Field", style="dim")
    table.add_column("Value")

    # Helper to safely format numeric values
    def safe_float(val, default=0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default

    fields = [
        ("Security Code", quote.get("securityID", "N/A")),
        ("Company Name", quote.get("companyName", "N/A")),
        ("Current Price", f"₹{safe_float(quote.get('currentValue')):,.2f}"),
        ("Change", f"{safe_float(quote.get('change')):+.2f}"),
        ("% Change", f"{safe_float(quote.get('pChange')):+.2f}%"),
        ("Open", f"₹{safe_float(quote.get('open')):,.2f}"),
        ("High", f"₹{safe_float(quote.get('high')):,.2f}"),
        ("Low", f"₹{safe_float(quote.get('low')):,.2f}"),
        ("Previous Close", f"₹{safe_float(quote.get('previousClose')):,.2f}"),
        ("52W High", f"₹{safe_float(quote.get('52weekHigh')):,.2f}"),
        ("52W Low", f"₹{safe_float(quote.get('52weekLow')):,.2f}"),
        ("Total Traded Value", quote.get("totalTradedValue", "N/A")),
        ("Total Traded Qty", quote.get("totalTradedQuantity", "N/A")),
        ("Market Cap (Cr)", quote.get("marketCapFull", "N/A")),
        ("Free Float Cap (Cr)", quote.get("marketCapFreeFloat", "N/A")),
        ("Industry", quote.get("industry", "N/A")),
        ("Group", quote.get("group", "N/A")),
        ("Face Value", quote.get("faceValue", "N/A")),
    ]

    for field, value in fields:
        if value and value != "N/A":
            table.add_row(field, str(value))

    console.print(table)


def display_quotes_table(quotes: list):
    """Display multiple quotes in a table."""
    if not quotes:
        return

    table = Table(title="BSE Stock Quotes")
    table.add_column("Code", style="cyan")
    table.add_column("Company", width=25)
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("% Change", justify="right")
    table.add_column("Volume", justify="right")

    for quote in quotes:
        change = float(quote.get("change", 0))
        pchange = float(quote.get("pChange", 0))

        change_style = "green" if change >= 0 else "red"
        change_prefix = "+" if change >= 0 else ""

        table.add_row(
            quote.get("securityID", "N/A"),
            quote.get("companyName", "N/A")[:25],
            f"₹{float(quote.get('currentValue', 0)):,.2f}",
            f"[{change_style}]{change_prefix}{change:.2f}[/{change_style}]",
            f"[{change_style}]{change_prefix}{pchange:.2f}%[/{change_style}]",
            str(quote.get("totalTradedQuantity", "N/A")),
        )

    console.print(table)


def display_movers_table(movers: list, title: str):
    """Display top movers (gainers/losers)."""
    if not movers:
        return

    table = Table(title=title)
    table.add_column("Code")
    table.add_column("Company", width=25)
    table.add_column("Price", justify="right")
    table.add_column("% Change", justify="right")

    for mover in movers[:10]:
        pchange = float(mover.get("pChange", mover.get("percentChange", 0)))
        change_style = "green" if pchange >= 0 else "red"

        table.add_row(
            str(mover.get("scripCode", mover.get("securityID", "N/A"))),
            str(mover.get("scripName", mover.get("companyName", "N/A")))[:25],
            f"₹{float(mover.get('ltp', mover.get('currentValue', 0))):,.2f}",
            f"[{change_style}]{pchange:+.2f}%[/{change_style}]",
        )

    console.print(table)


def save_output(data, filename: str):
    """Save data to JSON file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"[dim]Saved to {filepath}[/dim]")


def main():
    console.print("[bold magenta]═══ BSE Company Info Test ═══[/bold magenta]")

    bse = get_bse_client()
    if not bse:
        return False

    # Fetch quotes for multiple companies
    all_quotes = []
    for symbol, code in list(BSE_CODES.items())[:5]:
        quote = fetch_company_quote(bse, code)
        if quote:
            quote["nse_symbol"] = symbol
            all_quotes.append(quote)

    # Display quotes table
    display_quotes_table(all_quotes)

    # Display detailed quote for first company
    if all_quotes:
        display_quote_details(all_quotes[0])

    # Fetch top gainers
    gainers = fetch_top_gainers(bse)
    display_movers_table(gainers, "BSE Top Gainers")

    # Fetch top losers
    losers = fetch_top_losers(bse)
    display_movers_table(losers, "BSE Top Losers")

    # Save outputs
    save_output(
        {
            "timestamp": datetime.now().isoformat(),
            "quotes": all_quotes,
            "top_gainers": gainers,
            "top_losers": losers,
        },
        "bse_company_info.json",
    )

    console.print("\n[bold green]═══ BSE Company Info Test Complete ═══[/bold green]")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
