"""
Screener.in Quarterly Results & Financials Fetcher
Uses: Web scraping with httpx + BeautifulSoup

Fetches quarterly results, financial ratios, and shareholding patterns.
Rate limited: 1 request per 3 seconds
"""

import sys
import json
import asyncio
import re
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
import httpx
from bs4 import BeautifulSoup

console = Console()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Screener.in URLs
SCREENER_BASE_URL = "https://www.screener.in"
COMPANY_URL = "https://www.screener.in/company/{symbol}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Rate limiting
RATE_LIMIT_SECONDS = 3


async def fetch_company_page(symbol: str) -> str:
    """Fetch the HTML page for a company from Screener.in"""
    console.print(f"\n[bold blue]Fetching Screener.in page for {symbol}...[/bold blue]")

    url = COMPANY_URL.format(symbol=symbol)

    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=30.0, follow_redirects=True
        ) as client:
            response = await client.get(url)

            if response.status_code == 200:
                console.print(f"[green]✓ Fetched page for {symbol}[/green]")
                return response.text
            elif response.status_code == 404:
                console.print(
                    f"[yellow]Company {symbol} not found on Screener.in[/yellow]"
                )
                return ""
            else:
                console.print(
                    f"[yellow]Status {response.status_code} for {symbol}[/yellow]"
                )
                return ""

    except Exception as e:
        console.print(f"[red]Failed to fetch: {e}[/red]")
        return ""


def parse_company_info(html: str) -> dict:
    """Parse basic company information from the page."""
    soup = BeautifulSoup(html, "html.parser")

    info = {
        "name": "",
        "bse_code": "",
        "nse_code": "",
        "sector": "",
        "industry": "",
        "market_cap_cr": None,
        "current_price": None,
        "pe_ratio": None,
        "book_value": None,
        "dividend_yield": None,
        "roce": None,
        "roe": None,
    }

    # Company name
    name_elem = soup.select_one("h1.h2")
    if name_elem:
        info["name"] = name_elem.get_text(strip=True)

    # Get key ratios from the top section
    ratios_section = soup.select("#top-ratios li")
    for li in ratios_section:
        name_elem = li.select_one(".name")
        value_elem = li.select_one(".number")

        if name_elem and value_elem:
            name = name_elem.get_text(strip=True).lower()
            value = value_elem.get_text(strip=True)

            # Clean the value
            value_clean = re.sub(r"[₹,%\s]", "", value)

            try:
                if "market cap" in name:
                    info["market_cap_cr"] = float(value_clean.replace(",", ""))
                elif "current price" in name:
                    info["current_price"] = float(value_clean.replace(",", ""))
                elif "stock p/e" in name or "p/e" in name:
                    info["pe_ratio"] = float(value_clean)
                elif "book value" in name:
                    info["book_value"] = float(value_clean.replace(",", ""))
                elif "dividend yield" in name:
                    info["dividend_yield"] = float(value_clean)
                elif "roce" in name:
                    info["roce"] = float(value_clean)
                elif "roe" in name:
                    info["roe"] = float(value_clean)
            except (ValueError, TypeError):
                pass

    return info


def parse_quarterly_results(html: str) -> list:
    """Parse quarterly results table."""
    soup = BeautifulSoup(html, "html.parser")

    # Find quarterly results section
    quarters_section = soup.select_one("#quarters")
    if not quarters_section:
        return []

    results = []
    table = quarters_section.select_one("table")
    if not table:
        return []

    # Get headers (quarters)
    headers = []
    header_row = table.select_one("thead tr")
    if header_row:
        for th in header_row.select("th"):
            headers.append(th.get_text(strip=True))

    # Get data rows
    rows = table.select("tbody tr")
    data = {}

    for row in rows:
        cells = row.select("td")
        if not cells:
            continue

        metric = cells[0].get_text(strip=True)
        values = []

        for cell in cells[1:]:
            value = cell.get_text(strip=True)
            # Clean value
            value_clean = re.sub(r"[₹,%\s]", "", value).replace(",", "")
            try:
                values.append(float(value_clean) if value_clean else None)
            except ValueError:
                values.append(None)

        data[metric] = values

    # Convert to list of quarters
    for i, quarter in enumerate(headers[1:]):  # Skip first header (metric name)
        if i < len(headers) - 1:
            quarter_data = {"quarter": quarter}
            for metric, values in data.items():
                if i < len(values):
                    quarter_data[metric] = values[i]
            results.append(quarter_data)

    return results


def parse_shareholding_pattern(html: str) -> dict:
    """Parse shareholding pattern."""
    soup = BeautifulSoup(html, "html.parser")

    shareholding = {
        "promoters": None,
        "fiis": None,
        "diis": None,
        "public": None,
        "others": None,
    }

    # Find shareholding section
    sh_section = soup.select_one("#shareholding")
    if not sh_section:
        return shareholding

    table = sh_section.select_one("table")
    if not table:
        return shareholding

    rows = table.select("tbody tr")
    for row in rows:
        cells = row.select("td")
        if len(cells) >= 2:
            category = cells[0].get_text(strip=True).lower()
            # Get latest value (last column)
            value = cells[-1].get_text(strip=True)
            value_clean = re.sub(r"[%\s]", "", value)

            try:
                pct = float(value_clean)
                if "promoter" in category:
                    shareholding["promoters"] = pct
                elif "fii" in category or "foreign" in category:
                    shareholding["fiis"] = pct
                elif "dii" in category:
                    shareholding["diis"] = pct
                elif "public" in category:
                    shareholding["public"] = pct
            except ValueError:
                pass

    return shareholding


def parse_key_ratios(html: str) -> dict:
    """Parse key financial ratios."""
    soup = BeautifulSoup(html, "html.parser")

    ratios = {}

    # Find ratios section (usually in a data table)
    sections = soup.select("section.data-table")

    for section in sections:
        header = section.select_one("h2")
        if header and "ratios" in header.get_text().lower():
            table = section.select_one("table")
            if table:
                rows = table.select("tbody tr")
                for row in rows:
                    cells = row.select("td")
                    if len(cells) >= 2:
                        metric = cells[0].get_text(strip=True)
                        value = cells[-1].get_text(strip=True)
                        value_clean = re.sub(r"[%\s]", "", value).replace(",", "")
                        try:
                            ratios[metric] = float(value_clean) if value_clean else None
                        except ValueError:
                            ratios[metric] = value

    return ratios


def display_company_info(info: dict):
    """Display company information."""
    if not info.get("name"):
        return

    console.print(f"\n[bold]{info['name']}[/bold]")

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    metrics = [
        (
            "Market Cap",
            f"₹{info['market_cap_cr']:,.0f} Cr" if info.get("market_cap_cr") else "N/A",
        ),
        (
            "Current Price",
            f"₹{info['current_price']:,.2f}" if info.get("current_price") else "N/A",
        ),
        ("P/E Ratio", f"{info['pe_ratio']:.2f}" if info.get("pe_ratio") else "N/A"),
        (
            "Book Value",
            f"₹{info['book_value']:,.2f}" if info.get("book_value") else "N/A",
        ),
        (
            "Dividend Yield",
            f"{info['dividend_yield']:.2f}%" if info.get("dividend_yield") else "N/A",
        ),
        ("ROCE", f"{info['roce']:.2f}%" if info.get("roce") else "N/A"),
        ("ROE", f"{info['roe']:.2f}%" if info.get("roe") else "N/A"),
    ]

    for metric, value in metrics:
        table.add_row(metric, value)

    console.print(table)


def display_quarterly_results(results: list):
    """Display quarterly results."""
    if not results:
        console.print("[yellow]No quarterly results found[/yellow]")
        return

    table = Table(title="Quarterly Results")
    table.add_column("Quarter", style="cyan")
    table.add_column("Sales", justify="right")
    table.add_column("Expenses", justify="right")
    table.add_column("Operating Profit", justify="right")
    table.add_column("Net Profit", justify="right")
    table.add_column("EPS", justify="right")

    for q in results[:8]:  # Last 8 quarters
        sales = q.get("Sales", q.get("Revenue", None))
        expenses = q.get("Expenses", None)
        op_profit = q.get("Operating Profit", None)
        net_profit = q.get("Net Profit", q.get("Profit after tax", None))
        eps = q.get("EPS", q.get("EPS in Rs", None))

        table.add_row(
            q.get("quarter", "N/A"),
            f"₹{sales:,.0f}" if sales else "N/A",
            f"₹{expenses:,.0f}" if expenses else "N/A",
            f"₹{op_profit:,.0f}" if op_profit else "N/A",
            f"₹{net_profit:,.0f}" if net_profit else "N/A",
            f"₹{eps:.2f}" if eps else "N/A",
        )

    console.print(table)


def display_shareholding(shareholding: dict):
    """Display shareholding pattern."""
    console.print("\n[bold]Shareholding Pattern[/bold]")

    table = Table(show_header=False, box=None)
    table.add_column("Category", style="dim")
    table.add_column("Holding %", justify="right")

    categories = [
        ("Promoters", shareholding.get("promoters")),
        ("FIIs", shareholding.get("fiis")),
        ("DIIs", shareholding.get("diis")),
        ("Public", shareholding.get("public")),
    ]

    for cat, val in categories:
        if val is not None:
            table.add_row(cat, f"{val:.2f}%")

    console.print(table)


def save_output(data, filename: str):
    """Save data to JSON file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"[dim]Saved to {filepath}[/dim]")


async def main_async():
    """Async main function."""
    console.print("[bold magenta]═══ Screener.in Fetcher Test ═══[/bold magenta]")

    test_symbols = ["RELIANCE", "TATAPOWER", "TITAN"]
    all_data = {}

    for symbol in test_symbols:
        # Fetch page
        html = await fetch_company_page(symbol)

        if html:
            # Parse data
            info = parse_company_info(html)
            quarterly = parse_quarterly_results(html)
            shareholding = parse_shareholding_pattern(html)
            ratios = parse_key_ratios(html)

            # Display
            display_company_info(info)
            display_quarterly_results(quarterly)
            display_shareholding(shareholding)

            # Store
            all_data[symbol] = {
                "info": info,
                "quarterly_results": quarterly,
                "shareholding": shareholding,
                "ratios": ratios,
            }

        # Rate limiting
        console.print(f"[dim]Rate limiting: waiting {RATE_LIMIT_SECONDS}s...[/dim]")
        await asyncio.sleep(RATE_LIMIT_SECONDS)

    # Save outputs
    save_output(
        {"timestamp": datetime.now().isoformat(), "companies": all_data},
        "screener_data.json",
    )

    console.print("\n[bold green]═══ Screener.in Test Complete ═══[/bold green]")

    return True


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
