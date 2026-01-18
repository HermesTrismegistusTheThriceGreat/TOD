# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "numpy", "rich"]
# ///
"""
Options Strategy Selector

Analyzes greek data and market conditions to recommend optimal options strategies.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import models from same directory
sys.path.insert(0, str(Path(__file__).parent))
from models import (
    GreekProfile,
    MarketRegime,
    StrategyRecommendation,
    StrategyParameters,
    RiskMetrics,
    FullRecommendation,
    STRATEGIES,
)

console = Console()


def detect_regime(
    greeks: list[GreekProfile],
    spot: float,
    iv_rank: Optional[float] = None,
) -> MarketRegime:
    """
    Detect market regime from greek data.

    Priority order:
    1. Volatility Mean Reversion (IV significantly below HV)
    2. Range-Bound Stability (High IV rank)
    3. Term Structure Arb (if multi-expiry data)
    4. Volatility Skew (if put/call IV available)
    5. Default to Range-Bound
    """
    if not greeks:
        return MarketRegime(
            symbol="UNKNOWN",
            theme="range_bound_stability",
            confidence=0.5,
            indicators={"reason": "No greek data provided"},
        )

    symbol = greeks[0].symbol

    # Calculate aggregate metrics
    avg_iv = sum(g.implied_vol for g in greeks) / len(greeks)
    avg_hv = sum(g.hist_vol_20d for g in greeks) / len(greeks)
    vol_edge = avg_iv - avg_hv

    # Use provided IV rank or estimate from data
    effective_iv_rank = iv_rank
    if effective_iv_rank is None:
        ranks = [g.iv_rank for g in greeks if g.iv_rank is not None]
        effective_iv_rank = sum(ranks) / len(ranks) if ranks else 50.0

    indicators = {
        "avg_iv": round(avg_iv, 4),
        "avg_hv": round(avg_hv, 4),
        "vol_edge": round(vol_edge, 4),
        "iv_rank": round(effective_iv_rank, 1),
    }

    # Check for volatility mean reversion (IV cheap)
    if vol_edge < -0.05:  # IV more than 5% below HV
        return MarketRegime(
            symbol=symbol,
            theme="volatility_mean_reversion",
            confidence=min(0.9, abs(vol_edge) * 5),
            indicators={**indicators, "trigger": "IV significantly below HV"},
        )

    # Check for skew opportunities
    skews = [g.skew for g in greeks if g.skew is not None]
    if skews:
        avg_skew = sum(skews) / len(skews)
        if abs(avg_skew) > 0.05:  # More than 5% skew
            return MarketRegime(
                symbol=symbol,
                theme="volatility_skew",
                confidence=min(0.85, abs(avg_skew) * 5),
                indicators={**indicators, "avg_skew": round(avg_skew, 4)},
            )

    # Check for high IV rank (range-bound opportunity)
    if effective_iv_rank > 70:
        return MarketRegime(
            symbol=symbol,
            theme="range_bound_stability",
            confidence=min(0.9, effective_iv_rank / 100),
            indicators={**indicators, "trigger": "High IV rank"},
        )

    # Check for term structure opportunities (would need multi-expiry data)
    expiries = set(g.expiry for g in greeks)
    if len(expiries) > 1:
        # Group by expiry and compare IVs
        near_greeks = [g for g in greeks if g.dte <= 30]
        far_greeks = [g for g in greeks if g.dte > 30]

        if near_greeks and far_greeks:
            near_iv = sum(g.implied_vol for g in near_greeks) / len(near_greeks)
            far_iv = sum(g.implied_vol for g in far_greeks) / len(far_greeks)

            if near_iv < far_iv - 0.02:  # Near-term IV cheaper
                return MarketRegime(
                    symbol=symbol,
                    theme="term_structure_arb",
                    confidence=0.75,
                    indicators={
                        **indicators,
                        "near_iv": round(near_iv, 4),
                        "far_iv": round(far_iv, 4),
                    },
                )

    # Default to range-bound
    return MarketRegime(
        symbol=symbol,
        theme="range_bound_stability",
        confidence=0.6,
        indicators={**indicators, "trigger": "Default regime"},
    )


def calculate_iron_condor_params(
    greeks: list[GreekProfile], spot: float
) -> tuple[StrategyParameters, RiskMetrics]:
    """Calculate Iron Condor parameters from available strikes."""
    calls = [g for g in greeks if g.option_type == "call"]
    puts = [g for g in greeks if g.option_type == "put"]

    if not calls or not puts:
        raise ValueError("Need both calls and puts for Iron Condor")

    # Find short strikes (delta ~0.15-0.20)
    short_call = min(calls, key=lambda g: abs(abs(g.delta) - 0.16))
    short_put = min(puts, key=lambda g: abs(abs(g.delta) - 0.16))

    # Calculate minimum wing width based on spot price
    # Use at least $5 or 1.5% of spot, whichever is larger
    min_wing_width = max(5.0, spot * 0.015)

    # Find wing strikes (further OTM with minimum width)
    long_calls = [c for c in calls if c.strike >= short_call.strike + min_wing_width]
    long_puts = [p for p in puts if p.strike <= short_put.strike - min_wing_width]

    if not long_calls or not long_puts:
        # Fallback: use furthest available strikes
        long_call = max(calls, key=lambda g: g.strike)
        long_put = min(puts, key=lambda g: g.strike)
    else:
        # Select closest strike that meets minimum width
        long_call = min(long_calls, key=lambda g: g.strike)
        long_put = max(long_puts, key=lambda g: g.strike)

    # Estimate prices (use mid if available, otherwise estimate)
    def get_price(g: GreekProfile) -> float:
        if g.mid_price:
            return g.mid_price
        # Rough estimate based on delta
        return max(0.05, abs(g.delta) * spot * 0.1)

    # Net credit = short premiums - long premiums
    short_credit = get_price(short_call) + get_price(short_put)
    long_debit = get_price(long_call) + get_price(long_put)
    net_credit = short_credit - long_debit

    # Wing width (use call side)
    wing_width = long_call.strike - short_call.strike

    params = StrategyParameters(
        short_put=short_put.strike,
        long_put=long_put.strike,
        short_call=short_call.strike,
        long_call=long_call.strike,
        expiry=short_call.expiry,
        net_credit=round(net_credit, 2),
    )

    risk = RiskMetrics(
        max_profit=round(net_credit * 100, 2),
        max_loss=round((wing_width - net_credit) * 100, 2),
        breakeven_low=round(short_put.strike - net_credit, 2),
        breakeven_high=round(short_call.strike + net_credit, 2),
    )

    return params, risk


def calculate_straddle_params(
    greeks: list[GreekProfile], spot: float
) -> tuple[StrategyParameters, RiskMetrics]:
    """Calculate Long Straddle parameters."""
    # Find ATM options
    atm_call = min(
        [g for g in greeks if g.option_type == "call"],
        key=lambda g: abs(g.strike - spot),
    )
    atm_put = min(
        [g for g in greeks if g.option_type == "put"],
        key=lambda g: abs(g.strike - spot),
    )

    def get_price(g: GreekProfile) -> float:
        if g.mid_price:
            return g.mid_price
        return max(0.10, abs(g.delta) * spot * 0.15)

    premium = get_price(atm_call) + get_price(atm_put)

    params = StrategyParameters(
        atm_strike=atm_call.strike,
        expiry=atm_call.expiry,
        net_debit=round(premium, 2),
    )

    risk = RiskMetrics(
        max_profit=float("inf"),  # Unlimited
        max_loss=round(premium * 100, 2),
        breakeven_low=round(atm_call.strike - premium, 2),
        breakeven_high=round(atm_call.strike + premium, 2),
    )

    return params, risk


def select_strategy(
    greeks: list[GreekProfile],
    spot: float,
    iv_rank: Optional[float] = None,
) -> FullRecommendation:
    """
    Main entry point: select optimal strategy based on greek data.
    """
    # Detect regime
    regime = detect_regime(greeks, spot, iv_rank)

    # Get strategy recommendation
    strategy = STRATEGIES.get(regime.theme, STRATEGIES["range_bound_stability"])

    # Calculate parameters based on strategy
    notes = []

    try:
        if regime.theme == "volatility_mean_reversion":
            params, risk = calculate_straddle_params(greeks, spot)
            notes.append("Consider DTE > 45 for vol expansion time")
        elif regime.theme == "range_bound_stability":
            params, risk = calculate_iron_condor_params(greeks, spot)
            notes.append("Manage at 50% of max profit or 21 DTE")
        else:
            # Default to iron condor params for other strategies
            params, risk = calculate_iron_condor_params(greeks, spot)
            notes.append(f"Parameters estimated for {strategy.name}")
    except (ValueError, IndexError) as e:
        params = StrategyParameters()
        risk = RiskMetrics(max_profit=0, max_loss=0)
        notes.append(f"Could not calculate parameters: {e}")

    return FullRecommendation(
        symbol=regime.symbol,
        theme=regime.theme,
        regime=regime,
        strategy=strategy,
        parameters=params,
        risk_metrics=risk,
        greeks_used=greeks[:5],  # Include first 5 for reference
        notes=notes,
    )


def display_recommendation(rec: FullRecommendation) -> None:
    """Display recommendation using rich formatting."""
    # Strategy panel
    strategy_text = f"""
[bold cyan]Code:[/] {rec.strategy.code}
[bold cyan]Name:[/] {rec.strategy.name}
[bold cyan]Greeks:[/] {rec.strategy.greeks}
[bold cyan]Sentiment:[/] {rec.strategy.sentiment}
"""
    console.print(
        Panel(
            strategy_text,
            title=f"[bold green]Strategy Recommendation: {rec.symbol}[/]",
            width=80,
        )
    )

    # Regime info
    regime_table = Table(title="Market Regime Analysis", width=80)
    regime_table.add_column("Metric", style="cyan")
    regime_table.add_column("Value", style="green")

    regime_table.add_row("Theme", rec.regime.theme.replace("_", " ").title())
    regime_table.add_row("Confidence", f"{rec.regime.confidence:.1%}")
    for key, value in rec.regime.indicators.items():
        if isinstance(value, float):
            regime_table.add_row(key, f"{value:.4f}")
        else:
            regime_table.add_row(key, str(value))

    console.print(regime_table)

    # Parameters
    if rec.parameters.model_dump(exclude_none=True):
        params_table = Table(title="Strategy Parameters", width=80)
        params_table.add_column("Parameter", style="cyan")
        params_table.add_column("Value", style="yellow")

        for key, value in rec.parameters.model_dump(exclude_none=True).items():
            params_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(params_table)

    # Risk metrics
    risk_table = Table(title="Risk Metrics", width=80)
    risk_table.add_column("Metric", style="cyan")
    risk_table.add_column("Value", style="red")

    risk_table.add_row("Max Profit", f"${rec.risk_metrics.max_profit:,.2f}")
    risk_table.add_row("Max Loss", f"${rec.risk_metrics.max_loss:,.2f}")
    if rec.risk_metrics.breakeven_low:
        risk_table.add_row("Breakeven Low", f"${rec.risk_metrics.breakeven_low:.2f}")
    if rec.risk_metrics.breakeven_high:
        risk_table.add_row("Breakeven High", f"${rec.risk_metrics.breakeven_high:.2f}")

    console.print(risk_table)

    # Notes
    if rec.notes:
        console.print("\n[bold yellow]Notes:[/]")
        for note in rec.notes:
            console.print(f"  - {note}")


def main():
    parser = argparse.ArgumentParser(
        description="Select optimal options strategy based on greek data"
    )
    parser.add_argument("--symbol", required=True, help="Underlying symbol")
    parser.add_argument("--data", help="Path to JSON file with greek data")
    parser.add_argument("--spot", type=float, help="Current spot price")
    parser.add_argument("--iv-rank", type=float, help="IV rank (0-100)")
    parser.add_argument("--output", help="Output file path for JSON recommendation")

    args = parser.parse_args()

    # Load greek data
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

    # Use spot price from args or estimate from greeks
    spot = args.spot
    if spot is None and greeks:
        # Estimate from ATM options
        atm_options = [g for g in greeks if abs(g.delta) > 0.4 and abs(g.delta) < 0.6]
        if atm_options:
            spot = sum(g.strike for g in atm_options) / len(atm_options)
        else:
            spot = greeks[0].strike

    if spot is None:
        console.print("[red]Error: Must provide --spot or greek data[/]")
        sys.exit(1)

    # Generate recommendation
    recommendation = select_strategy(greeks, spot, args.iv_rank)

    # Display
    display_recommendation(recommendation)

    # Save if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            f.write(recommendation.model_dump_json(indent=2))
        console.print(f"\n[green]Saved to {output_path}[/]")


if __name__ == "__main__":
    main()
