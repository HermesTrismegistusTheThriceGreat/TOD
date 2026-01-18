# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
"""
Pydantic models for options greek data and strategy selection.
"""

from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field, computed_field


class GreekProfile(BaseModel):
    """
    Greek profile for a single option contract.

    This is the core data structure for strategy selection.
    """

    symbol: str = Field(..., description="Underlying ticker symbol")
    strike: float = Field(..., gt=0, description="Option strike price")
    expiry: date = Field(..., description="Expiration date")
    option_type: Literal["call", "put"] = Field(..., description="Option type")
    dte: int = Field(..., ge=0, description="Days to expiration")

    # Core Greeks
    delta: float = Field(..., ge=-1, le=1, description="Delta (-1 to 1)")
    gamma: float = Field(..., ge=0, description="Gamma (rate of delta change)")
    theta: float = Field(..., description="Theta (time decay, negative for longs)")
    vega: float = Field(..., ge=0, description="Vega (IV sensitivity)")

    # Volatility Metrics
    implied_vol: float = Field(
        ..., ge=0, le=5, description="Implied volatility as decimal (e.g., 0.25 = 25%)"
    )
    hist_vol_20d: float = Field(
        ..., ge=0, le=5, description="20-day historical volatility as decimal"
    )
    iv_rank: Optional[float] = Field(
        None, ge=0, le=100, description="IV rank/percentile (0-100)"
    )

    # Optional pricing data
    bid: Optional[float] = Field(None, ge=0, description="Bid price")
    ask: Optional[float] = Field(None, ge=0, description="Ask price")
    last_price: Optional[float] = Field(None, ge=0, description="Last trade price")
    volume: Optional[int] = Field(None, ge=0, description="Contract volume")
    open_interest: Optional[int] = Field(None, ge=0, description="Open interest")

    # Skew analysis (optional)
    put_iv: Optional[float] = Field(
        None, ge=0, description="Put IV at this strike (for skew)"
    )
    call_iv: Optional[float] = Field(
        None, ge=0, description="Call IV at this strike (for skew)"
    )

    @computed_field
    @property
    def vol_edge(self) -> float:
        """Volatility edge: IV - HV. Negative means IV is cheap."""
        return self.implied_vol - self.hist_vol_20d

    @computed_field
    @property
    def skew(self) -> Optional[float]:
        """Put-Call IV skew. Positive means puts are more expensive."""
        if self.put_iv is not None and self.call_iv is not None:
            return self.put_iv - self.call_iv
        return None

    @computed_field
    @property
    def mid_price(self) -> Optional[float]:
        """Mid price between bid and ask."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last_price


class MarketRegime(BaseModel):
    """
    Detected market regime/theme for strategy selection.
    """

    symbol: str = Field(..., description="Underlying symbol")
    theme: Literal[
        "volatility_mean_reversion",
        "range_bound_stability",
        "term_structure_arb",
        "volatility_skew",
        "regime_shift",
    ] = Field(..., description="Detected market theme")
    confidence: float = Field(
        ..., ge=0, le=1, description="Confidence in regime detection (0-1)"
    )
    indicators: dict = Field(
        default_factory=dict, description="Supporting metrics for the detection"
    )


class StrategyRecommendation(BaseModel):
    """
    Strategy recommendation output.
    """

    code: str = Field(..., description="Strategy code (STRAT_A1 through STRAT_A6)")
    name: str = Field(..., description="Strategy name")
    greeks: str = Field(..., description="Greek profile description")
    sentiment: str = Field(..., description="Strategy sentiment/description")


class StrategyParameters(BaseModel):
    """
    Specific parameters for executing a strategy.
    """

    # Iron Condor / Butterfly parameters
    short_put: Optional[float] = Field(None, description="Short put strike")
    long_put: Optional[float] = Field(None, description="Long put strike (wing)")
    short_call: Optional[float] = Field(None, description="Short call strike")
    long_call: Optional[float] = Field(None, description="Long call strike (wing)")

    # Straddle/Strangle parameters
    atm_strike: Optional[float] = Field(None, description="ATM strike for straddle")

    # Calendar spread parameters
    near_expiry: Optional[date] = Field(None, description="Near-term expiration")
    far_expiry: Optional[date] = Field(None, description="Far-term expiration")

    # Ratio spread parameters
    long_strike: Optional[float] = Field(None, description="Long option strike")
    short_strike: Optional[float] = Field(None, description="Short option strike")
    ratio: Optional[str] = Field(None, description="Ratio (e.g., '1x2')")

    # Common
    expiry: Optional[date] = Field(None, description="Primary expiration")
    net_credit: Optional[float] = Field(None, description="Net credit received")
    net_debit: Optional[float] = Field(None, description="Net debit paid")


class RiskMetrics(BaseModel):
    """
    Risk metrics for a strategy.
    """

    max_profit: float = Field(..., description="Maximum profit potential")
    max_loss: float = Field(..., description="Maximum loss potential")
    breakeven_low: Optional[float] = Field(None, description="Lower breakeven price")
    breakeven_high: Optional[float] = Field(None, description="Upper breakeven price")
    probability_of_profit: Optional[float] = Field(
        None, ge=0, le=1, description="Estimated probability of profit"
    )
    risk_reward_ratio: Optional[float] = Field(
        None, description="Risk to reward ratio"
    )


class FullRecommendation(BaseModel):
    """
    Complete strategy recommendation with all details.
    """

    symbol: str
    theme: str
    regime: MarketRegime
    strategy: StrategyRecommendation
    parameters: StrategyParameters
    risk_metrics: RiskMetrics
    greeks_used: list[GreekProfile] = Field(
        default_factory=list, description="Greek profiles used in analysis"
    )
    notes: list[str] = Field(
        default_factory=list, description="Additional notes or warnings"
    )


# Strategy definitions
STRATEGIES = {
    "volatility_mean_reversion": StrategyRecommendation(
        code="STRAT_A1",
        name="Long Straddle",
        greeks="+Vega, +Gamma, -Theta",
        sentiment="Buying the dip in vol - high risk, high reward",
    ),
    "range_bound_stability": StrategyRecommendation(
        code="STRAT_A2",
        name="Iron Condor",
        greeks="-Vega, -Gamma, +Theta",
        sentiment="Bread and butter theta harvesting",
    ),
    "volatility_skew": StrategyRecommendation(
        code="STRAT_A3",
        name="Ratio Spread",
        greeks="Variable Delta, -Vega",
        sentiment="Complex skew exploitation",
    ),
    "term_structure_arb": StrategyRecommendation(
        code="STRAT_A4",
        name="Calendar Spread",
        greeks="Neutral Delta, +Vega",
        sentiment="Low-risk time decay play",
    ),
    "precision_pinning": StrategyRecommendation(
        code="STRAT_A5",
        name="Butterfly Spread",
        greeks="Neutral Vega, -Gamma",
        sentiment="Precision price targeting",
    ),
    "arbitrage": StrategyRecommendation(
        code="STRAT_A6",
        name="Synthetic/Parity",
        greeks="Pure Delta",
        sentiment="Institutional edge only",
    ),
}


if __name__ == "__main__":
    # Example usage
    example_greek = GreekProfile(
        symbol="SLV",
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
        iv_rank=75.0,
    )

    print("Example Greek Profile:")
    print(example_greek.model_dump_json(indent=2))
    print(f"\nVol Edge: {example_greek.vol_edge:.2%}")
