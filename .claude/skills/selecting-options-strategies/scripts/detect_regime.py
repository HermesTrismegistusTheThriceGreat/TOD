# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich"]
# ///
"""
Market Regime Detector

Analyzes options data to detect the current market regime/theme.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import models from same directory
sys.path.insert(0, str(Path(__file__).parent))
from models import GreekProfile, MarketRegime

console = Console()


# Theme detection thresholds
THRESHOLDS = {
    "vol_mean_reversion": {
        "vol_edge_max": -0.05,  # IV at least 5% below HV
        "min_dte": 45,  # Need time for vol expansion
    },
    "range_bound": {
        "iv_rank_min": 70,  # High IV rank
        "delta_range": (0.10, 0.30),  # OTM strikes available
    },
    "term_structure": {
        "iv_diff_min": 0.02,  # Near IV at least 2% below far
        "delta_range": (0.45, 0.55),  # ATM options
    },
    "skew": {
        "skew_min": 0.05,  # At least 5% put-call skew
    },
}


def analyze_vol_metrics(greeks: list[GreekProfile]) -> dict:
    """Calculate volatility metrics from greek data."""
    if not greeks:
        return {}

    ivs = [g.implied_vol for g in greeks]
    hvs = [g.hist_vol_20d for g in greeks]
    iv_ranks = [g.iv_rank for g in greeks if g.iv_rank is not None]

    return {
        "avg_iv": sum(ivs) / len(ivs),
        "avg_hv": sum(hvs) / len(hvs),
        "vol_edge": (sum(ivs) / len(ivs)) - (sum(hvs) / len(hvs)),
        "iv_rank": sum(iv_ranks) / len(iv_ranks) if iv_ranks else None,
        "iv_range": (min(ivs), max(ivs)),
    }


def analyze_term_structure(greeks: list[GreekProfile]) -> dict:
    """Analyze term structure from multi-expiry data."""
    expiries = {}
    for g in greeks:
        key = g.expiry
        if key not in expiries:
            expiries[key] = []
        expiries[key].append(g)

    if len(expiries) < 2:
        return {"multi_expiry": False}

    # Sort by DTE and compare
    sorted_expiries = sorted(expiries.items(), key=lambda x: x[1][0].dte)

    near_expiry, near_greeks = sorted_expiries[0]
    far_expiry, far_greeks = sorted_expiries[-1]

    near_iv = sum(g.implied_vol for g in near_greeks) / len(near_greeks)
    far_iv = sum(g.implied_vol for g in far_greeks) / len(far_greeks)

    return {
        "multi_expiry": True,
        "near_expiry": str(near_expiry),
        "far_expiry": str(far_expiry),
        "near_iv": near_iv,
        "far_iv": far_iv,
        "term_spread": far_iv - near_iv,
        "contango": near_iv < far_iv,
    }


def analyze_skew(greeks: list[GreekProfile]) -> dict:
    """Analyze put-call volatility skew."""
    skews = []
    for g in greeks:
        if g.skew is not None:
            skews.append(g.skew)

    if not skews:
        # Try to calculate from separate put/call IVs at same strike
        strikes = {}
        for g in greeks:
            if g.strike not in strikes:
                strikes[g.strike] = {}
            strikes[g.strike][g.option_type] = g.implied_vol

        for strike, ivs in strikes.items():
            if "put" in ivs and "call" in ivs:
                skews.append(ivs["put"] - ivs["call"])

    if not skews:
        return {"skew_data": False}

    avg_skew = sum(skews) / len(skews)
    return {
        "skew_data": True,
        "avg_skew": avg_skew,
        "skew_direction": "puts_rich" if avg_skew > 0 else "calls_rich",
        "significant_skew": abs(avg_skew) > THRESHOLDS["skew"]["skew_min"],
    }


def detect_regime(
    greeks: list[GreekProfile],
    iv_rank_override: float | None = None,
) -> MarketRegime:
    """
    Detect market regime from greek data.

    Returns MarketRegime with theme, confidence, and supporting indicators.
    """
    if not greeks:
        return MarketRegime(
            symbol="UNKNOWN",
            theme="range_bound_stability",
            confidence=0.5,
            indicators={"error": "No data provided"},
        )

    symbol = greeks[0].symbol

    # Gather all metrics
    vol_metrics = analyze_vol_metrics(greeks)
    term_metrics = analyze_term_structure(greeks)
    skew_metrics = analyze_skew(greeks)

    # Override IV rank if provided
    if iv_rank_override is not None:
        vol_metrics["iv_rank"] = iv_rank_override

    indicators = {
        "vol": vol_metrics,
        "term_structure": term_metrics,
        "skew": skew_metrics,
    }

    # Decision logic with priority
    detected_themes = []

    # 1. Check volatility mean reversion
    vol_edge = vol_metrics.get("vol_edge", 0)
    if vol_edge < THRESHOLDS["vol_mean_reversion"]["vol_edge_max"]:
        confidence = min(0.9, abs(vol_edge) * 5)
        detected_themes.append(("volatility_mean_reversion", confidence))

    # 2. Check skew opportunity
    if skew_metrics.get("significant_skew"):
        skew_val = abs(skew_metrics.get("avg_skew", 0))
        confidence = min(0.85, skew_val * 5)
        detected_themes.append(("volatility_skew", confidence))

    # 3. Check term structure
    if term_metrics.get("contango") and term_metrics.get("term_spread", 0) > 0.02:
        confidence = min(0.8, term_metrics["term_spread"] * 10)
        detected_themes.append(("term_structure_arb", confidence))

    # 4. Check range-bound (high IV rank)
    iv_rank = vol_metrics.get("iv_rank")
    if iv_rank and iv_rank > THRESHOLDS["range_bound"]["iv_rank_min"]:
        confidence = min(0.9, iv_rank / 100)
        detected_themes.append(("range_bound_stability", confidence))

    # Select highest confidence theme
    if detected_themes:
        detected_themes.sort(key=lambda x: x[1], reverse=True)
        theme, confidence = detected_themes[0]
    else:
        theme = "range_bound_stability"
        confidence = 0.5

    return MarketRegime(
        symbol=symbol,
        theme=theme,
        confidence=confidence,
        indicators=indicators,
    )


def display_regime(regime: MarketRegime) -> None:
    """Display regime analysis using rich formatting."""
    theme_colors = {
        "volatility_mean_reversion": "red",
        "range_bound_stability": "green",
        "term_structure_arb": "blue",
        "volatility_skew": "yellow",
        "regime_shift": "magenta",
    }

    color = theme_colors.get(regime.theme, "white")
    theme_display = regime.theme.replace("_", " ").title()

    console.print(
        Panel(
            f"[bold {color}]{theme_display}[/]\n\nConfidence: {regime.confidence:.1%}",
            title=f"[bold]Market Regime: {regime.symbol}[/]",
            width=80,
        )
    )

    # Volatility metrics table
    vol = regime.indicators.get("vol", {})
    if vol:
        vol_table = Table(title="Volatility Metrics", width=80)
        vol_table.add_column("Metric", style="cyan")
        vol_table.add_column("Value", style="green")

        if "avg_iv" in vol:
            vol_table.add_row("Average IV", f"{vol['avg_iv']:.2%}")
        if "avg_hv" in vol:
            vol_table.add_row("Average HV", f"{vol['avg_hv']:.2%}")
        if "vol_edge" in vol:
            edge = vol["vol_edge"]
            edge_color = "red" if edge < 0 else "green"
            vol_table.add_row("Vol Edge (IV - HV)", f"[{edge_color}]{edge:.2%}[/]")
        if "iv_rank" in vol and vol["iv_rank"] is not None:
            vol_table.add_row("IV Rank", f"{vol['iv_rank']:.1f}")

        console.print(vol_table)

    # Term structure table
    term = regime.indicators.get("term_structure", {})
    if term.get("multi_expiry"):
        term_table = Table(title="Term Structure", width=80)
        term_table.add_column("Metric", style="cyan")
        term_table.add_column("Value", style="blue")

        term_table.add_row("Near Expiry", term.get("near_expiry", "N/A"))
        term_table.add_row("Far Expiry", term.get("far_expiry", "N/A"))
        if "near_iv" in term:
            term_table.add_row("Near IV", f"{term['near_iv']:.2%}")
        if "far_iv" in term:
            term_table.add_row("Far IV", f"{term['far_iv']:.2%}")
        if "term_spread" in term:
            term_table.add_row("Term Spread", f"{term['term_spread']:.2%}")
        term_table.add_row("Structure", "Contango" if term.get("contango") else "Backwardation")

        console.print(term_table)

    # Skew table
    skew = regime.indicators.get("skew", {})
    if skew.get("skew_data"):
        skew_table = Table(title="Volatility Skew", width=80)
        skew_table.add_column("Metric", style="cyan")
        skew_table.add_column("Value", style="yellow")

        if "avg_skew" in skew:
            skew_table.add_row("Average Skew", f"{skew['avg_skew']:.2%}")
        if "skew_direction" in skew:
            skew_table.add_row("Direction", skew["skew_direction"].replace("_", " ").title())
        skew_table.add_row(
            "Significant",
            "[green]Yes[/]" if skew.get("significant_skew") else "[red]No[/]",
        )

        console.print(skew_table)

    # Strategy suggestion
    strategy_map = {
        "volatility_mean_reversion": ("STRAT_A1", "Long Straddle"),
        "range_bound_stability": ("STRAT_A2", "Iron Condor"),
        "volatility_skew": ("STRAT_A3", "Ratio Spread"),
        "term_structure_arb": ("STRAT_A4", "Calendar Spread"),
    }

    if regime.theme in strategy_map:
        code, name = strategy_map[regime.theme]
        console.print(f"\n[bold green]Suggested Strategy:[/] {code} - {name}")


def main():
    parser = argparse.ArgumentParser(description="Detect market regime from options data")
    parser.add_argument("--symbol", required=True, help="Underlying symbol")
    parser.add_argument("--data", help="Path to JSON file with greek data")
    parser.add_argument("--iv-rank", type=float, help="Override IV rank (0-100)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Load data
    greeks = []
    if args.data:
        data_path = Path(args.data)
        if data_path.exists():
            with open(data_path) as f:
                raw_data = json.load(f)
                if isinstance(raw_data, list):
                    greeks = [GreekProfile(**g) for g in raw_data]
                else:
                    greeks = [GreekProfile(**raw_data)]
        else:
            console.print(f"[red]File not found: {args.data}[/]")
            sys.exit(1)

    # If no data file, create minimal example
    if not greeks:
        console.print("[yellow]No data file provided. Using example data.[/]")
        from datetime import date

        greeks = [
            GreekProfile(
                symbol=args.symbol,
                strike=25.0,
                expiry=date(2025, 2, 21),
                option_type="call",
                dte=45,
                delta=0.50,
                gamma=0.08,
                theta=-0.02,
                vega=0.15,
                implied_vol=0.28,
                hist_vol_20d=0.22,
                iv_rank=args.iv_rank or 75.0,
            )
        ]

    # Detect regime
    regime = detect_regime(greeks, args.iv_rank)

    # Output
    if args.json:
        print(regime.model_dump_json(indent=2))
    else:
        display_regime(regime)


if __name__ == "__main__":
    main()
