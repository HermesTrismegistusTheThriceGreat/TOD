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
- OptionsPosition: Options position grouped by underlying and expiry
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
    Single option leg within an options position.

    Maps to OpenPositionCard's OptionLeg interface.
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
# OPTIONS POSITION MODEL
# ═══════════════════════════════════════════════════════════

class OptionsPosition(BaseModel):
    """
    Options position grouped by underlying and expiry.

    Groups all option legs for a given ticker and expiration date.
    Can represent any multi-leg options strategy (spreads, condors, butterflies, etc.)

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
    strategy: str = "Options"  # Default to generic "Options"
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


class SpotPriceUpdate(BaseModel):
    """
    Real-time spot (underlying stock) price update.
    Broadcast via WebSocket to update spot price in frontend.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    symbol: str  # Underlying symbol (e.g., "SPY")
    bid_price: float
    ask_price: float
    mid_price: float  # (bid + ask) / 2
    last_price: Optional[float] = None
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
    positions: List[OptionsPosition] = []
    total_count: int = 0
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# ORDER MODELS
# ═══════════════════════════════════════════════════════════

class Order(BaseModel):
    """Single order from Alpaca."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    qty: Optional[str] = None
    filled_qty: Optional[str] = None
    side: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    filled_at: Optional[str] = None
    filled_avg_price: Optional[str] = None


class GetOrdersResponse(BaseModel):
    """Response for GET /api/orders"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    orders: List[Order] = []
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
    position: Optional[OptionsPosition] = None
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


class SubscribeSpotPricesRequest(BaseModel):
    """Request to subscribe to spot price updates for stock symbols"""
    model_config = ConfigDict(from_attributes=True)

    symbols: List[str]  # List of stock symbols (e.g., ["SPY", "QQQ"])


class SubscribeSpotPricesResponse(BaseModel):
    """Response for POST /api/positions/subscribe-spot-prices"""
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

# Aliases for backwards compatibility
IronCondorPosition = OptionsPosition
TickerPosition = OptionsPosition

__all__ = [
    "OCCSymbol",
    "OptionLeg",
    "OptionsPosition",
    "IronCondorPosition",
    "TickerPosition",
    "OptionPriceUpdate",
    "SpotPriceUpdate",
    "PositionPriceUpdates",
    "GetPositionsResponse",
    "GetPositionResponse",
    "Order",
    "GetOrdersResponse",
    "SubscribePricesRequest",
    "SubscribePricesResponse",
    "SubscribeSpotPricesRequest",
    "SubscribeSpotPricesResponse",
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
