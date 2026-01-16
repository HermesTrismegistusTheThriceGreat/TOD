#!/usr/bin/env python3
"""
Pydantic models for Alpaca Trading API integration.

These models follow the same patterns as apps/orchestrator_db/models.py:
- Use float (not Decimal) for currency values
- Use model_config = ConfigDict() (Pydantic V2)
- Use field_validator for type conversion
- UUID/datetime serialization to strings

Models:
- OCCSymbol: Parsed OCC option symbol
- OptionLeg: Single option leg in a position
- IronCondorPosition: 4-leg iron condor grouping
- OptionPriceUpdate: Real-time price update
- API request/response models
"""

from datetime import date, datetime
from typing import Dict, Any, Optional, List, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict
import re


# ═══════════════════════════════════════════════════════════
# OCC SYMBOL PARSING
# ═══════════════════════════════════════════════════════════

class OCCSymbol(BaseModel):
    """
    Parsed OCC option symbol.

    OCC Format: {underlying}{YYMMDD}{C|P}{strike * 1000, 8 digits}
    Example: SPY260117C00688000 -> SPY Call $688 expiring 2026-01-17
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            date: lambda v: v.isoformat()
        }
    )

    raw_symbol: str
    underlying: str
    expiry_date: date
    option_type: Literal['Call', 'Put']
    strike_price: float

    @classmethod
    def parse(cls, symbol: str) -> 'OCCSymbol':
        """
        Parse OCC-format option symbol.

        Args:
            symbol: OCC symbol like 'SPY260117C00688000'

        Returns:
            Parsed OCCSymbol object

        Raises:
            ValueError: If symbol format is invalid
        """
        # OCC format: underlying (1-6 chars) + date (6) + type (1) + strike (8)
        pattern = r'^([A-Z]{1,6})(\d{6})([CP])(\d{8})$'
        match = re.match(pattern, symbol.upper())

        if not match:
            raise ValueError(f"Invalid OCC symbol format: {symbol}")

        underlying, date_str, opt_type, strike_str = match.groups()

        # Parse date (YYMMDD)
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        expiry = date(year, month, day)

        # Parse strike (divide by 1000)
        strike = float(strike_str) / 1000

        return cls(
            raw_symbol=symbol.upper(),
            underlying=underlying,
            expiry_date=expiry,
            option_type='Call' if opt_type == 'C' else 'Put',
            strike_price=strike
        )


# ═══════════════════════════════════════════════════════════
# OPTION LEG MODEL
# ═══════════════════════════════════════════════════════════

class OptionLeg(BaseModel):
    """
    Single option leg within an iron condor position.

    Maps to IronCondorCard's OptionLeg interface.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID: str,
            date: lambda v: v.isoformat()
        }
    )

    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str  # OCC symbol
    direction: Literal['Long', 'Short']
    strike: float
    option_type: Literal['Call', 'Put']
    quantity: int
    entry_price: float  # Average fill price
    current_price: float = 0.0  # Updated via WebSocket
    expiry_date: date
    underlying: str

    @field_validator('strike', 'entry_price', 'current_price', mode='before')
    @classmethod
    def convert_to_float(cls, v):
        """Convert any numeric type to float"""
        if v is None:
            return 0.0
        return float(v)

    @computed_field
    @property
    def pnl_dollars(self) -> float:
        """
        Calculate P/L in dollars (considering direction).

        Short positions profit when price decreases.
        Long positions profit when price increases.
        """
        multiplier = 1 if self.direction == 'Short' else -1
        price_diff = (self.entry_price - self.current_price) * multiplier
        return price_diff * self.quantity * 100

    @computed_field
    @property
    def pnl_percent(self) -> float:
        """Calculate P/L as percentage"""
        if self.entry_price == 0:
            return 0.0
        direction_mult = -1 if self.direction == 'Short' else 1
        return ((self.current_price - self.entry_price) / self.entry_price) * 100 * direction_mult


# ═══════════════════════════════════════════════════════════
# IRON CONDOR POSITION MODEL
# ═══════════════════════════════════════════════════════════

class IronCondorPosition(BaseModel):
    """
    Complete iron condor position with 4 legs.

    Iron Condor Structure:
    - Long Call (highest strike) - Buy for protection
    - Short Call (high strike) - Sell to open
    - Short Put (low strike) - Sell to open
    - Long Put (lowest strike) - Buy for protection

    Note: Also available as TickerPosition alias for backwards compatibility.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID: str,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
    )

    id: str = Field(default_factory=lambda: str(uuid4()))
    ticker: str  # Underlying symbol (e.g., "SPY")
    strategy: str = "Options"  # Default to generic "Options", detect_strategy() sets specific type
    expiry_date: date
    legs: List[OptionLeg]
    created_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def total_pnl(self) -> float:
        """Sum P/L across all legs"""
        return sum(leg.pnl_dollars for leg in self.legs)

    @computed_field
    @property
    def days_to_expiry(self) -> int:
        """Calculate days until expiration"""
        today = date.today()
        delta = self.expiry_date - today
        return max(0, delta.days)

    def get_leg_by_type(self, option_type: str, direction: str) -> Optional[OptionLeg]:
        """Find a specific leg by type and direction"""
        for leg in self.legs:
            if leg.option_type == option_type and leg.direction == direction:
                return leg
        return None

    @property
    def short_put(self) -> Optional[OptionLeg]:
        return self.get_leg_by_type('Put', 'Short')

    @property
    def long_put(self) -> Optional[OptionLeg]:
        return self.get_leg_by_type('Put', 'Long')

    @property
    def short_call(self) -> Optional[OptionLeg]:
        return self.get_leg_by_type('Call', 'Short')

    @property
    def long_call(self) -> Optional[OptionLeg]:
        return self.get_leg_by_type('Call', 'Long')

    def is_valid_iron_condor(self) -> bool:
        """Verify this is a valid iron condor structure (informational only)"""
        if len(self.legs) != 4:
            return False

        sp = self.short_put
        lp = self.long_put
        sc = self.short_call
        lc = self.long_call

        if not all([sp, lp, sc, lc]):
            return False

        # Validate strike ordering:
        # Long Put < Short Put < Short Call < Long Call
        return (
            lp.strike < sp.strike and
            sp.strike < sc.strike and
            sc.strike < lc.strike
        )

    def is_valid_iron_butterfly(self) -> bool:
        """Verify this is a valid iron butterfly structure.

        Iron Butterfly: 4 legs with short put strike == short call strike (ATM)
        """
        if len(self.legs) != 4:
            return False

        sp = self.short_put
        lp = self.long_put
        sc = self.short_call
        lc = self.long_call

        if not all([sp, lp, sc, lc]):
            return False

        # Iron Butterfly: short put and short call at SAME strike (ATM)
        # Long put below, long call above
        return (
            lp.strike < sp.strike and
            sp.strike == sc.strike and  # KEY DIFFERENCE: same strike
            sc.strike < lc.strike
        )

    def detect_strategy(self) -> str:
        """
        Detect the strategy type based on leg structure.

        Returns strategy type based on leg configuration:
        - "Iron Butterfly": 4 legs with short strikes equal (ATM)
        - "Iron Condor": 4 legs with 2C+2P and valid strike ordering
        - "Vertical Spread": 2 legs of same type, different strikes
        - "Straddle": 2 legs, same strike, different types
        - "Strangle": 2 legs, different strikes, different types
        - "Options": Default for unrecognized patterns
        """
        if len(self.legs) == 0:
            return "Options"

        # Check for 4-leg strategies (check Iron Butterfly FIRST - more specific)
        if len(self.legs) == 4:
            if self.is_valid_iron_butterfly():
                return "Iron Butterfly"
            if self.is_valid_iron_condor():
                return "Iron Condor"

        # Check for 2-leg strategies
        if len(self.legs) == 2:
            leg1, leg2 = self.legs[0], self.legs[1]

            # Same option type = Vertical Spread
            if leg1.option_type == leg2.option_type:
                return "Vertical Spread"

            # Different option types
            # Same strike = Straddle
            if leg1.strike == leg2.strike:
                return "Straddle"

            # Different strikes = Strangle
            return "Strangle"

        # Default for unrecognized patterns (1, 3, 5+ legs, or invalid 4-leg)
        return "Options"


# ═══════════════════════════════════════════════════════════
# PRICE UPDATE MODELS
# ═══════════════════════════════════════════════════════════

class OptionPriceUpdate(BaseModel):
    """
    Real-time price update for an option.
    Broadcast via WebSocket to update currentPrice in frontend.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    symbol: str  # OCC symbol
    bid_price: float
    ask_price: float
    mid_price: float  # (bid + ask) / 2
    last_price: Optional[float] = None
    volume: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('bid_price', 'ask_price', 'mid_price', 'last_price', mode='before')
    @classmethod
    def convert_to_float(cls, v):
        if v is None:
            return None
        return float(v)


class PositionPriceUpdates(BaseModel):
    """
    Batch of price updates for all legs in a position.
    Used for efficient WebSocket broadcasting.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    position_id: str
    updates: Dict[str, OptionPriceUpdate]  # symbol -> update
    timestamp: datetime = Field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════
# API REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class GetPositionsResponse(BaseModel):
    """Response for GET /api/positions"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    positions: List[IronCondorPosition] = []
    total_count: int = 0
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# CLOSE POSITION MODELS
# ═══════════════════════════════════════════════════════════

class CloseOrderResult(BaseModel):
    """Result of a single close order"""
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    order_id: str
    status: Literal['submitted', 'filled', 'failed']
    filled_qty: int = 0
    filled_avg_price: Optional[float] = None
    error_message: Optional[str] = None


class CloseStrategyRequest(BaseModel):
    """Request to close an entire strategy (all legs)"""
    model_config = ConfigDict(from_attributes=True)

    position_id: str
    order_type: Literal['market', 'limit'] = 'market'
    limit_price_offset: Optional[float] = None  # For limit orders: offset from mid price


class CloseStrategyResponse(BaseModel):
    """Response for close strategy operation"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'partial', 'error']
    position_id: str
    orders: List[CloseOrderResult] = []
    message: Optional[str] = None
    total_legs: int = 0
    closed_legs: int = 0


class CloseLegRequest(BaseModel):
    """Request to close a single leg"""
    model_config = ConfigDict(from_attributes=True)

    leg_id: str
    order_type: Literal['market', 'limit'] = 'market'
    limit_price: Optional[float] = None


class CloseLegResponse(BaseModel):
    """Response for close leg operation"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    order: Optional[CloseOrderResult] = None
    message: Optional[str] = None


class GetPositionResponse(BaseModel):
    """Response for GET /api/positions/{id}"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    position: Optional[IronCondorPosition] = None
    message: Optional[str] = None


class SubscribePricesRequest(BaseModel):
    """Request to subscribe to price updates for specific symbols"""
    model_config = ConfigDict(from_attributes=True)

    symbols: List[str]  # List of OCC symbols


class SubscribePricesResponse(BaseModel):
    """Response for POST /api/positions/subscribe-prices"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    message: Optional[str] = None
    symbols: List[str] = []


# ═══════════════════════════════════════════════════════════
# TRADE HISTORY MODELS
# ═══════════════════════════════════════════════════════════

class TradeResponse(BaseModel):
    """Single trade (aggregated from orders with same trade_id)"""
    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    ticker: str  # underlying symbol
    strategy: str  # iron_condor, vertical_spread, etc.
    direction: Literal['Long', 'Short']  # dominant direction
    entry_date: str  # ISO format date
    exit_date: Optional[str] = None
    entry_price: float  # total premium received/paid
    exit_price: Optional[float] = None
    quantity: int  # number of contracts (max across legs)
    pnl: float  # total P&L in dollars
    pnl_percent: float  # P&L as percentage
    status: Literal['open', 'closed', 'expired']
    leg_count: int  # number of legs in this trade
    orders: List[dict] = []  # individual order details


class LegDetail(BaseModel):
    """Individual leg within a trade with open/close matching."""
    model_config = ConfigDict(from_attributes=True)

    leg_number: int
    description: str  # e.g., "423 Call"
    symbol: str  # OCC symbol
    strike: float
    option_type: Literal['call', 'put']

    # Open (entry) details
    open_action: Literal['BUY', 'SELL']
    open_fill: float  # filled_avg_price for opening order
    open_date: Optional[str] = None

    # Close (exit) details - None if position still open
    close_action: Optional[Literal['BUY', 'SELL']] = None
    close_fill: Optional[float] = None
    close_date: Optional[str] = None

    # Computed P&L
    quantity: int
    pnl_per_contract: float  # P&L per single contract
    pnl_total: float  # P&L for all contracts (quantity * 100 * pnl_per_contract)
    is_closed: bool = False


class TradeSummary(BaseModel):
    """Aggregated summary for all legs in a trade."""
    model_config = ConfigDict(from_attributes=True)

    opening_credit: float  # Net credit received at open (sell side - buy side)
    closing_debit: float   # Net debit paid at close (buy side - sell side)
    net_pnl_per_contract: float
    net_pnl_total: float
    leg_count: int
    closed_legs: int
    open_legs: int


class DetailedTrade(BaseModel):
    """Complete trade with leg-level detail."""
    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    ticker: str
    strategy: str  # iron_butterfly, vertical_spread, etc.
    direction: Literal['Long', 'Short']  # Net direction based on premium
    status: Literal['open', 'closed', 'partial']  # partial = some legs closed
    entry_date: str
    exit_date: Optional[str] = None
    expiry_date: Optional[str] = None

    legs: List['LegDetail']
    summary: 'TradeSummary'


class DetailedTradeListResponse(BaseModel):
    """Response for detailed trades endpoint."""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    trades: List['DetailedTrade'] = []
    total_count: int = 0
    message: Optional[str] = None


class TradeListResponse(BaseModel):
    """Response for GET /api/trades"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    trades: List[TradeResponse] = []
    total_count: int = 0
    message: Optional[str] = None


class TradeStatsResponse(BaseModel):
    """Response for GET /api/trade-stats"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    total_pnl: float = 0.0
    win_rate: float = 0.0  # percentage
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════

# Alias for new code using the generic name
TickerPosition = IronCondorPosition

__all__ = [
    "OCCSymbol",
    "OptionLeg",
    "IronCondorPosition",
    "TickerPosition",
    "OptionPriceUpdate",
    "PositionPriceUpdates",
    "GetPositionsResponse",
    "GetPositionResponse",
    "SubscribePricesRequest",
    "SubscribePricesResponse",
    "CloseOrderResult",
    "CloseStrategyRequest",
    "CloseStrategyResponse",
    "CloseLegRequest",
    "CloseLegResponse",
    "TradeResponse",
    "TradeListResponse",
    "TradeStatsResponse",
    "LegDetail",
    "TradeSummary",
    "DetailedTrade",
    "DetailedTradeListResponse",
]
