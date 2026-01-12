# Part 1: Alpaca Pydantic Models

## Overview

**Scope:** Create Pydantic V2 models for Alpaca Trading API data structures
**Dependencies:** None (Foundation layer)
**Estimated Time:** 1-2 hours

## Objectives

1. Create Pydantic models matching codebase patterns (see `apps/orchestrator_db/models.py`)
2. Implement OCC symbol parser utility for option symbols
3. Use `float` with validators (not `Decimal`) to match existing codebase patterns
4. Use Pydantic V2 `model_config = ConfigDict(...)` syntax (NOT deprecated `class Config`)

## Review Feedback Addressed

| Issue | Severity | Fix |
|-------|----------|-----|
| `class Config` deprecated in Pydantic V2 | HIGH | Use `model_config = ConfigDict(...)` |
| `Decimal` inconsistent with codebase | HIGH | Use `float` with validators |

## Files to Create

### New Files

| File | Purpose |
|------|---------|
| `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` | Pydantic models for Alpaca data |

## Implementation Steps

### Step 1: Create alpaca_models.py

**File:** `apps/orchestrator_3_stream/backend/modules/alpaca_models.py`

```python
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
    strategy: str = "Iron Condor"
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
        """Verify this is a valid iron condor structure"""
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
# EXPORTS
# ═══════════════════════════════════════════════════════════

__all__ = [
    "OCCSymbol",
    "OptionLeg",
    "IronCondorPosition",
    "OptionPriceUpdate",
    "PositionPriceUpdates",
    "GetPositionsResponse",
    "GetPositionResponse",
    "SubscribePricesRequest",
    "SubscribePricesResponse",
]
```

## Testing Requirements

### Unit Tests

**File:** `apps/orchestrator_3_stream/backend/tests/test_alpaca_models.py`

```python
#!/usr/bin/env python3
"""
Unit tests for Alpaca Pydantic models.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_models.py -v
"""

import pytest
from datetime import date, datetime
from uuid import UUID

# Import models
import sys
sys.path.insert(0, '..')
from modules.alpaca_models import (
    OCCSymbol,
    OptionLeg,
    IronCondorPosition,
    OptionPriceUpdate,
    GetPositionsResponse,
)


class TestOCCSymbolParser:
    """Tests for OCCSymbol.parse()"""

    def test_parse_spy_call(self):
        """Parse SPY call option"""
        result = OCCSymbol.parse("SPY260117C00688000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Call"
        assert result.strike_price == 688.0

    def test_parse_spy_put(self):
        """Parse SPY put option"""
        result = OCCSymbol.parse("SPY260117P00683000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Put"
        assert result.strike_price == 683.0

    def test_parse_fractional_strike(self):
        """Parse option with fractional strike"""
        result = OCCSymbol.parse("AAPL250321C00142500")

        assert result.underlying == "AAPL"
        assert result.strike_price == 142.5

    def test_parse_single_char_underlying(self):
        """Parse option with single character underlying"""
        result = OCCSymbol.parse("F251219C00015000")

        assert result.underlying == "F"
        assert result.strike_price == 15.0

    def test_parse_six_char_underlying(self):
        """Parse option with 6 character underlying"""
        result = OCCSymbol.parse("GOOGLL251219C01500000")

        assert result.underlying == "GOOGLL"
        assert result.strike_price == 1500.0

    def test_invalid_format_raises(self):
        """Invalid format raises ValueError"""
        with pytest.raises(ValueError):
            OCCSymbol.parse("INVALID")

    def test_lowercase_normalized(self):
        """Lowercase input is normalized to uppercase"""
        result = OCCSymbol.parse("spy260117c00688000")

        assert result.underlying == "SPY"
        assert result.option_type == "Call"
        assert result.raw_symbol == "SPY260117C00688000"

    def test_empty_string_raises(self):
        """Empty string raises ValueError"""
        with pytest.raises(ValueError):
            OCCSymbol.parse("")


class TestOptionLegPnL:
    """Tests for OptionLeg P/L calculations"""

    def test_short_call_profit(self):
        """Short call with price decrease = profit"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=4.00,
            current_price=3.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Short: entry > current = profit
        # P/L = (entry - current) * qty * 100
        # = (4.00 - 3.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == 1000.0

    def test_short_call_loss(self):
        """Short call with price increase = loss"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=3.00,
            current_price=4.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Short: entry < current = loss
        # P/L = (3.00 - 4.00) * 10 * 100 = -$1000
        assert leg.pnl_dollars == -1000.0

    def test_long_put_profit(self):
        """Long put with price increase = profit"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=1.00,
            current_price=2.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Long: current > entry = profit
        # P/L = (current - entry) * qty * 100
        # = (2.00 - 1.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == 1000.0

    def test_long_put_loss(self):
        """Long put with price decrease = loss"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=2.00,
            current_price=1.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Long: current < entry = loss
        # P/L = (1.00 - 2.00) * 10 * 100 = -$1000
        assert leg.pnl_dollars == -1000.0

    def test_zero_entry_price_pnl_percent(self):
        """Zero entry price returns 0% P/L"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=0.0,
            current_price=1.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        assert leg.pnl_percent == 0.0


class TestIronCondorPosition:
    """Tests for IronCondorPosition validation"""

    def create_valid_iron_condor(self) -> IronCondorPosition:
        """Helper to create a valid iron condor"""
        return IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                OptionLeg(symbol="SPY260117P00680000", direction="Long", strike=680.0, option_type="Put", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117P00685000", direction="Short", strike=685.0, option_type="Put", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117C00695000", direction="Short", strike=695.0, option_type="Call", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117C00700000", direction="Long", strike=700.0, option_type="Call", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
            ]
        )

    def test_valid_iron_condor(self):
        """Valid iron condor passes validation"""
        ic = self.create_valid_iron_condor()
        assert ic.is_valid_iron_condor() is True

    def test_invalid_fewer_than_4_legs(self):
        """Iron condor with fewer than 4 legs fails validation"""
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                OptionLeg(symbol="SPY260117P00680000", direction="Long", strike=680.0, option_type="Put", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117P00685000", direction="Short", strike=685.0, option_type="Put", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
            ]
        )
        assert ic.is_valid_iron_condor() is False

    def test_total_pnl_calculation(self):
        """Total P/L sums all leg P/Ls"""
        ic = self.create_valid_iron_condor()

        # Set current prices to trigger P/L
        ic.legs[0].current_price = 0.50  # Long put: loss of $500
        ic.legs[1].current_price = 1.50  # Short put: profit of $500
        ic.legs[2].current_price = 1.50  # Short call: profit of $500
        ic.legs[3].current_price = 0.50  # Long call: loss of $500

        # Total should be $0 (balanced)
        assert ic.total_pnl == 0.0

    def test_get_leg_by_type(self):
        """get_leg_by_type returns correct leg"""
        ic = self.create_valid_iron_condor()

        short_put = ic.get_leg_by_type('Put', 'Short')
        assert short_put is not None
        assert short_put.strike == 685.0

        long_call = ic.get_leg_by_type('Call', 'Long')
        assert long_call is not None
        assert long_call.strike == 700.0

    def test_days_to_expiry(self):
        """days_to_expiry calculates correctly"""
        from datetime import timedelta

        # Create IC expiring in 10 days
        future_date = date.today() + timedelta(days=10)
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=future_date,
            legs=[]
        )

        assert ic.days_to_expiry == 10


class TestModelSerialization:
    """Tests for JSON serialization"""

    def test_option_leg_to_json(self):
        """OptionLeg serializes to JSON correctly"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=4.00,
            current_price=3.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        json_data = leg.model_dump()

        assert json_data['symbol'] == 'SPY260117C00688000'
        assert json_data['strike'] == 688.0
        assert json_data['pnl_dollars'] == 1000.0
        assert 'expiry_date' in json_data

    def test_price_update_to_json(self):
        """OptionPriceUpdate serializes correctly"""
        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25,
        )

        json_data = update.model_dump()

        assert json_data['symbol'] == 'SPY260117C00688000'
        assert json_data['mid_price'] == 3.25
        assert 'timestamp' in json_data

    def test_response_model_serialization(self):
        """API response models serialize correctly"""
        response = GetPositionsResponse(
            status='success',
            positions=[],
            total_count=0
        )

        json_data = response.model_dump()

        assert json_data['status'] == 'success'
        assert json_data['positions'] == []
```

## Validation Commands

```bash
# Navigate to backend directory
cd apps/orchestrator_3_stream/backend

# Verify module imports correctly
uv run python -c "from modules.alpaca_models import OCCSymbol, OptionLeg, IronCondorPosition; print('Import OK')"

# Test OCC parser
uv run python -c "
from modules.alpaca_models import OCCSymbol
result = OCCSymbol.parse('SPY260117C00688000')
print(f'Underlying: {result.underlying}')
print(f'Expiry: {result.expiry_date}')
print(f'Type: {result.option_type}')
print(f'Strike: {result.strike_price}')
"

# Run unit tests
uv run pytest tests/test_alpaca_models.py -v

# Verify Pydantic V2 model_config pattern
uv run python -c "
from modules.alpaca_models import OptionLeg
print(f'Model config: {OptionLeg.model_config}')
assert 'from_attributes' in OptionLeg.model_config
print('Pydantic V2 pattern confirmed')
"
```

## Acceptance Criteria

- [ ] All models use `model_config = ConfigDict(...)` (Pydantic V2)
- [ ] All currency fields use `float` (not `Decimal`)
- [ ] OCCSymbol.parse() correctly parses all valid OCC formats
- [ ] OptionLeg P/L calculations are correct for Long and Short directions
- [ ] IronCondorPosition.is_valid_iron_condor() validates 4-leg structure
- [ ] All models serialize to JSON without errors
- [ ] All unit tests pass
- [ ] No linting errors in the module

## Notes

### OCC Symbol Format Reference

```
Format: {underlying}{YYMMDD}{C|P}{strike * 1000, 8 digits}

Examples:
- SPY260117C00688000 = SPY Call $688 exp 2026-01-17
- AAPL250321P00142500 = AAPL Put $142.50 exp 2025-03-21
- F251219C00015000 = F Call $15 exp 2025-12-19
```

### Iron Condor Structure

```
         Long Call (protection)  $700
              ↓
         Short Call (premium)    $695
    ─────────────────────────────── Stock Price
         Short Put (premium)     $685
              ↓
         Long Put (protection)   $680
```
