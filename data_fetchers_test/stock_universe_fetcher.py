"""
NSE Stock Universe Fetcher
Uses: nsetools library + NSE CSV downloads

Fetches complete list of NSE-listed stocks.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
import pandas as pd
import httpx

console = Console()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# NSE URLs for stock lists
NIFTY_500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
NIFTY_50_URL = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_all_stock_codes() -> dict:
    """Fetch all NSE stock codes using nsetools."""
    console.print(
        "\n[bold blue]Fetching all NSE stock codes via nsetools...[/bold blue]"
    )

    try:
        from nsetools import Nse

        nse = Nse()

        stock_codes = nse.get_stock_codes()

        # Remove the header entry
        if "SYMBOL" in stock_codes:
            del stock_codes["SYMBOL"]

        console.print(f"[green]✓ Fetched {len(stock_codes)} stock codes[/green]")
        return stock_codes

    except Exception as e:
        console.print(f"[red]Failed to fetch stock codes: {e}[/red]")
        return {}


def fetch_nifty_500_list() -> pd.DataFrame:
    """Fetch Nifty 500 constituents from NSE archives."""
    console.print("\n[bold blue]Fetching Nifty 500 list from NSE...[/bold blue]")

    try:
        df = pd.read_csv(NIFTY_500_URL)
        console.print(f"[green]✓ Fetched {len(df)} Nifty 500 stocks[/green]")
        return df

    except Exception as e:
        console.print(f"[red]Failed to fetch Nifty 500 list: {e}[/red]")
        return pd.DataFrame()


def fetch_nifty_50_list() -> pd.DataFrame:
    """Fetch Nifty 50 constituents from NSE archives."""
    console.print("\n[bold blue]Fetching Nifty 50 list from NSE...[/bold blue]")

    try:
        df = pd.read_csv(NIFTY_50_URL)
        console.print(f"[green]✓ Fetched {len(df)} Nifty 50 stocks[/green]")
        return df

    except Exception as e:
        console.print(f"[red]Failed to fetch Nifty 50 list: {e}[/red]")
        return pd.DataFrame()


def fetch_index_list(index_name: str) -> pd.DataFrame:
    """Fetch constituents for any NSE index."""
    console.print(f"\n[bold blue]Fetching {index_name} constituents...[/bold blue]")

    # Map of index names to CSV file names
    index_map = {
        "NIFTY 50": "ind_nifty50list",
        "NIFTY NEXT 50": "ind_niftynext50list",
        "NIFTY 100": "ind_nifty100list",
        "NIFTY 200": "ind_nifty200list",
        "NIFTY 500": "ind_nifty500list",
        "NIFTY BANK": "ind_niftybanklist",
        "NIFTY IT": "ind_niftyitlist",
        "NIFTY AUTO": "ind_niftyautolist",
        "NIFTY PHARMA": "ind_niftypharmalist",
        "NIFTY FMCG": "ind_niftyfmcglist",
        "NIFTY METAL": "ind_niftymetallist",
        "NIFTY REALTY": "ind_niftyrealtylist",
        "NIFTY ENERGY": "ind_niftyenergylist",
        "NIFTY INFRA": "ind_niftyinfralist",
        "NIFTY PSU BANK": "ind_niftypsubanklist",
        "NIFTY MEDIA": "ind_niftymedialist",
        "NIFTY MIDCAP 50": "ind_niftymidcap50list",
        "NIFTY SMALLCAP 50": "ind_niftysmallcap50list",
    }

    filename = index_map.get(index_name.upper())
    if not filename:
        console.print(f"[yellow]Unknown index: {index_name}[/yellow]")
        return pd.DataFrame()

    url = f"https://archives.nseindia.com/content/indices/{filename}.csv"

    try:
        df = pd.read_csv(url)
        console.print(f"[green]✓ Fetched {len(df)} stocks for {index_name}[/green]")
        return df
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        return pd.DataFrame()


def display_stock_universe_stats(stock_codes: dict, nifty500: pd.DataFrame):
    """Display statistics about the stock universe."""

    table = Table(title="NSE Stock Universe Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total NSE Stocks", f"{len(stock_codes):,}")
    table.add_row("Nifty 500 Stocks", f"{len(nifty500):,}")

    if not nifty500.empty and "Industry" in nifty500.columns:
        sectors = nifty500["Industry"].nunique()
        table.add_row("Unique Sectors", f"{sectors}")

    console.print(table)


def display_sector_breakdown(df: pd.DataFrame):
    """Display sector-wise breakdown."""
    if df.empty or "Industry" not in df.columns:
        return

    sector_counts = df["Industry"].value_counts().head(15)

    table = Table(title="Top 15 Sectors in Nifty 500")
    table.add_column("Sector", style="cyan")
    table.add_column("Count", justify="right")

    for sector, count in sector_counts.items():
        table.add_row(sector, str(count))

    console.print(table)


def display_sample_stocks(df: pd.DataFrame, n: int = 10):
    """Display sample stocks from the list."""
    if df.empty:
        return

    table = Table(title=f"Sample Stocks (First {n})")

    # Add columns based on available data
    columns = ["Symbol", "Company Name", "Industry", "Series"]
    for col in columns:
        if col in df.columns:
            table.add_column(col)

    for _, row in df.head(n).iterrows():
        row_data = []
        for col in columns:
            if col in df.columns:
                row_data.append(str(row[col]))
        table.add_row(*row_data)

    console.print(table)


def save_output(data, filename: str):
    """Save data to file."""
    filepath = OUTPUT_DIR / filename

    if isinstance(data, pd.DataFrame):
        data.to_csv(filepath, index=False)
    elif isinstance(data, dict):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    console.print(f"[dim]Saved to {filepath}[/dim]")


def main():
    console.print("[bold magenta]═══ NSE Stock Universe Test ═══[/bold magenta]")

    # Fetch all stock codes
    stock_codes = fetch_all_stock_codes()

    # Fetch Nifty 500 (primary universe for this project)
    nifty500 = fetch_nifty_500_list()

    # Fetch Nifty 50
    nifty50 = fetch_nifty_50_list()

    # Display statistics
    display_stock_universe_stats(stock_codes, nifty500)

    # Display sector breakdown
    display_sector_breakdown(nifty500)

    # Display sample stocks
    display_sample_stocks(nifty500)

    # Fetch a sector-specific index
    bank_stocks = fetch_index_list("NIFTY BANK")
    if not bank_stocks.empty:
        console.print("\n[bold]Nifty Bank Constituents:[/bold]")
        display_sample_stocks(bank_stocks, 12)

    # Save outputs
    save_output(stock_codes, "all_stock_codes.json")
    save_output(nifty500, "nifty500_list.csv")
    save_output(nifty50, "nifty50_list.csv")

    console.print("\n[bold green]═══ Stock Universe Test Complete ═══[/bold green]")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
