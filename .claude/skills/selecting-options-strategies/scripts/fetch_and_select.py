#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "requests", "numpy", "python-dotenv", "rich"]
# ///
"""
Complete Alpaca Data Integration Pipeline

Fetches historical volatility and options chain from Alpaca,
builds GreekProfile objects, detects market regime, and recommends strategy.
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import modules from same directory
sys.path.insert(0, str(Path(__file__).parent))
from alpaca_fetcher import AlpacaFetcher, AlpacaFetcherError
from models import GreekProfile
from strategy_selector import select_strategy, display_recommendation

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Alpaca data and recommend options strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch GLD data with auto spot price and get strategy recommendation
  uv run scripts/fetch_and_select.py --symbol GLD

  # Fetch SLV data with explicit spot price
  uv run scripts/fetch_and_select.py --symbol SLV --spot 28.50

  # Fetch with DTE filtering (30-60 days)
  uv run scripts/fetch_and_select.py --symbol GLD --min-dte 30 --max-dte 60

  # Save fetched data for later analysis
  uv run scripts/fetch_and_select.py --symbol SLV --save-data slv_data.json

Environment:
  ALPACA_API_KEY      Your Alpaca API key
  ALPACA_SECRET_KEY   Your Alpaca secret key
        """,
    )
    parser.add_argument(
        "--symbol", required=True, help="Underlying ticker symbol (e.g., SLV, GLD)"
    )
    parser.add_argument(
        "--spot", type=float, help="Current spot price of underlying (auto-fetched if not provided)"
    )
    parser.add_argument(
        "--min-dte",
        type=int,
        default=0,
        help="Minimum days to expiration (default: 0)",
    )
    parser.add_argument(
        "--max-dte",
        type=int,
        default=90,
        help="Maximum days to expiration (default: 90)",
    )
    parser.add_argument(
        "--iv-rank", type=float, help="Override IV rank (0-100) for regime detection"
    )
    parser.add_argument(
        "--save-data", metavar="FILE", help="Save fetched greek data to JSON file"
    )
    parser.add_argument(
        "--output", metavar="FILE", help="Save strategy recommendation to JSON file"
    )

    args = parser.parse_args()

    # Display header
    spot_display = f"${args.spot:.2f}" if args.spot else "(auto-fetch)"
    console.print(
        Panel(
            f"[bold cyan]Fetching Options Data from Alpaca[/]\n\n"
            f"Symbol: {args.symbol}\n"
            f"Spot: {spot_display}\n"
            f"DTE Range: {args.min_dte}-{args.max_dte} days",
            title="[bold green]Options Strategy Pipeline[/]",
            width=80,
        )
    )

    try:
        # Initialize Alpaca fetcher
        console.print("\n[yellow]Initializing Alpaca connection...[/]")
        fetcher = AlpacaFetcher()

        # Auto-fetch spot price if not provided
        spot_price = args.spot
        if spot_price is None:
            console.print(f"\n[yellow]Fetching spot price for {args.symbol}...[/]")
            spot_price = fetcher.fetch_spot_price(args.symbol)
            console.print(f"[green]✓ Spot price: ${spot_price:.2f}[/]")

        # Calculate date filters
        today = date.today()
        expiry_after = today + timedelta(days=args.min_dte)
        expiry_before = today + timedelta(days=args.max_dte)

        # Fetch data
        console.print(f"\n[yellow]Fetching {args.symbol} options chain...[/]")
        console.print(
            f"[dim]Expiry range: {expiry_after.isoformat()} to {expiry_before.isoformat()}[/]"
        )

        profiles = fetcher.fetch_all(
            symbol=args.symbol,
            expiry_after=expiry_after,
            expiry_before=expiry_before,
            hv_window=20,
        )

        if not profiles:
            console.print(
                f"[red]No options data found for {args.symbol} in specified DTE range[/]"
            )
            sys.exit(1)

        console.print(f"[green]✓ Fetched {len(profiles)} option contracts[/]")

        # Display sample data
        if profiles:
            sample_table = Table(
                title=f"Sample Greek Profiles (showing {min(5, len(profiles))} of {len(profiles)})",
                width=80,
            )
            sample_table.add_column("Strike", style="cyan")
            sample_table.add_column("Type", style="yellow")
            sample_table.add_column("DTE", style="blue")
            sample_table.add_column("Delta", style="green")
            sample_table.add_column("IV", style="magenta")
            sample_table.add_column("Vol Edge", style="red")

            for profile in profiles[:5]:
                sample_table.add_row(
                    f"${profile.strike:.2f}",
                    profile.option_type.upper(),
                    str(profile.dte),
                    f"{profile.delta:.3f}",
                    f"{profile.implied_vol:.2%}",
                    f"{profile.vol_edge:+.2%}",
                )

            console.print("\n")
            console.print(sample_table)

        # Save data if requested
        if args.save_data:
            data_path = Path(args.save_data)
            with open(data_path, "w") as f:
                json.dump(
                    [p.model_dump(mode="json") for p in profiles], f, indent=2
                )
            console.print(f"\n[green]✓ Saved greek data to {data_path}[/]")

        # Run strategy selector
        console.print(
            "\n[yellow]Analyzing market regime and selecting strategy...[/]\n"
        )

        recommendation = select_strategy(profiles, spot_price, args.iv_rank)

        # Display recommendation
        display_recommendation(recommendation)

        # Save recommendation if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                f.write(recommendation.model_dump_json(indent=2))
            console.print(f"\n[green]✓ Saved recommendation to {output_path}[/]")

    except AlpacaFetcherError as e:
        console.print(f"\n[red]Alpaca API Error:[/] {e}")
        console.print(
            "\n[yellow]Troubleshooting:[/]\n"
            "  1. Check your ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables\n"
            "  2. Ensure you have Alpaca Elite subscription for options data\n"
            "  3. Verify the symbol is valid and has options listed\n"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
