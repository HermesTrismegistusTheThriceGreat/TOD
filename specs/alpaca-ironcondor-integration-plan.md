# Plan: Alpaca Trading API Integration for IronCondorCard

## Task Description

Integrate Alpaca Trading API data into the IronCondorCard Vue component using a **hybrid approach**:
- **REST API** for initial position structure (ticker, legs, strikes, expiry, entry prices) - one-time fetch on component load
- **WebSocket streams** for live `currentPrice` updates on option legs - continuous real-time updates

This integration connects the existing `IronCondorCard.vue` component to live Alpaca trading data, replacing the placeholder mock data with real iron condor positions and streaming price updates.

## Objective

When complete, the IronCondorCard component will:
1. Fetch real iron condor positions from Alpaca via a new FastAPI REST endpoint
2. Display live option leg prices via WebSocket streaming
3. Calculate real-time P/L based on entry prices and streaming current prices
4. Handle errors, reconnection, and edge cases gracefully

## Problem Statement

The IronCondorCard component currently uses hardcoded placeholder data. To make this component useful for live trading monitoring, it needs to:
1. Connect to Alpaca's Trading API to fetch actual iron condor positions
2. Stream real-time option prices for P/L calculations
3. Parse OCC-format option symbols to extract strike, expiry, and type information
4. Handle the 4-leg iron condor structure (short put, long put, short call, long call)

## Solution Approach

**Architecture: Hybrid REST + WebSocket**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Vue 3)                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                       IronCondorCard.vue                           │ │
│  │  ┌──────────────────┐     ┌──────────────────────────────────────┐ │ │
│  │  │ useAlpacaPositions│     │    useAlpacaPriceStream             │ │ │
│  │  │ (REST - one-time)│     │    (WebSocket - continuous)          │ │ │
│  │  └────────┬─────────┘     └────────────────┬─────────────────────┘ │ │
│  └───────────┼─────────────────────────────────┼──────────────────────┘ │
│              │                                  │                       │
└──────────────┼──────────────────────────────────┼───────────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI @ 9403)                       │
│  ┌────────────────────────┐    ┌────────────────────────────────────┐   │
│  │  REST: /api/positions  │    │  WS: /ws (existing + new events)   │   │
│  │  /api/positions/{id}   │    │  - option_price_update             │   │
│  └───────────┬────────────┘    └───────────────┬────────────────────┘   │
│              │                                  │                        │
│              ▼                                  ▼                        │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      AlpacaService                                  ││
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐││
│  │  │  TradingClient   │  │ OptionDataStream │  │  TradingStream     │││
│  │  │  (positions)     │  │  (price quotes)  │  │  (order fills)     │││
│  │  └──────────────────┘  └──────────────────┘  └────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │         Alpaca API              │
                    │  (Trading + Options Data)       │
                    └─────────────────────────────────┘
```

## Relevant Files

### Existing Files to Modify

- **`apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`**
  - Target component - replace placeholder data with API integration
  - Add composable hooks for positions and price streaming

- **`apps/orchestrator_3_stream/backend/main.py`**
  - Add new REST endpoints for positions
  - Initialize AlpacaService in lifespan

- **`apps/orchestrator_3_stream/backend/modules/config.py`**
  - Add Alpaca API configuration constants

- **`apps/orchestrator_3_stream/backend/modules/websocket_manager.py`**
  - Add broadcast method for option price updates

- **`apps/orchestrator_3_stream/frontend/src/services/chatService.ts`**
  - Add WebSocket callback for option price updates

- **`apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`**
  - Add state management for positions and prices

- **`apps/orchestrator_3_stream/.env`**
  - Add Alpaca API credentials (already present)

### New Files to Create

- **`apps/orchestrator_3_stream/backend/modules/alpaca_service.py`**
  - AlpacaService class with TradingClient, OptionDataStream, TradingStream
  - OCC symbol parser utility
  - Position aggregation logic for iron condors

- **`apps/orchestrator_3_stream/backend/modules/alpaca_models.py`**
  - Pydantic models for positions, option legs, price updates

- **`apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts`**
  - REST API client for position endpoints

- **`apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`**
  - Composable for fetching and managing positions

- **`apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts`**
  - Composable for WebSocket price streaming

- **`apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`**
  - TypeScript interfaces for Alpaca data structures

## Implementation Phases

### Phase 1: Foundation (Backend Infrastructure)

**Goal:** Set up Alpaca SDK integration, configuration, and Pydantic models

1. Add Alpaca credentials to config and .env
2. Create Pydantic models for positions and option legs
3. Create AlpacaService class with TradingClient initialization
4. Implement OCC symbol parser utility
5. Add unit tests for OCC parser

### Phase 2: Core Implementation (REST + WebSocket)

**Goal:** Implement full data flow from Alpaca to frontend

1. Implement position fetching with iron condor detection
2. Create REST endpoints for positions
3. Add OptionDataStream integration for price streaming
4. Extend WebSocket manager for price broadcast
5. Update frontend services and store

### Phase 3: Integration & Polish (Frontend Component)

**Goal:** Connect IronCondorCard to live data with error handling

1. Create Vue composables for positions and streaming
2. Update IronCondorCard to use composables
3. Add error handling, loading states, reconnection logic
4. Add caching for price updates
5. Integration testing

## Step by Step Tasks

### 1. Add Alpaca Configuration

Add Alpaca API credentials and configuration to the backend.

**File:** `apps/orchestrator_3_stream/.env`
```env
# Alpaca Trading API
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
```

**File:** `apps/orchestrator_3_stream/backend/modules/config.py`

Add after line 175 (after IDE configuration):

```python
# ============================================================================
# ALPACA TRADING API CONFIGURATION
# ============================================================================

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() in ["true", "1", "yes"]
ALPACA_DATA_FEED = os.getenv("ALPACA_DATA_FEED", "iex")  # 'iex' or 'sip'

# Validate Alpaca credentials
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    config_logger.warning("Alpaca API credentials not configured - trading features disabled")
```

**Acceptance Criteria:**
- [ ] .env file contains Alpaca credential placeholders
- [ ] config.py exports ALPACA_* constants
- [ ] Warning logged if credentials missing

---

### 2. Create Alpaca Pydantic Models

Create strongly-typed Pydantic models for all Alpaca data structures.

**File:** `apps/orchestrator_3_stream/backend/modules/alpaca_models.py`

```python
#!/usr/bin/env python3
"""
Pydantic models for Alpaca Trading API integration.

These models handle:
- Option leg representation
- Iron condor position grouping
- Real-time price updates
- OCC symbol parsing results
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, computed_field
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
    raw_symbol: str
    underlying: str
    expiry_date: date
    option_type: Literal['Call', 'Put']
    strike_price: Decimal

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
        strike = Decimal(strike_str) / 1000

        return cls(
            raw_symbol=symbol,
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
    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str  # OCC symbol
    direction: Literal['Long', 'Short']
    strike: Decimal
    option_type: Literal['Call', 'Put']
    quantity: int
    entry_price: Decimal  # Average fill price
    current_price: Decimal = Decimal("0")  # Updated via WebSocket
    expiry_date: date
    underlying: str

    @field_validator('strike', 'entry_price', 'current_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert float/string to Decimal"""
        if v is None:
            return Decimal("0")
        return Decimal(str(v))

    @computed_field
    @property
    def pnl_dollars(self) -> Decimal:
        """Calculate P/L in dollars (considering direction)"""
        multiplier = 1 if self.direction == 'Short' else -1
        price_diff = (self.entry_price - self.current_price) * multiplier
        return price_diff * self.quantity * 100

    @computed_field
    @property
    def pnl_percent(self) -> Decimal:
        """Calculate P/L as percentage"""
        if self.entry_price == 0:
            return Decimal("0")
        direction_mult = -1 if self.direction == 'Short' else 1
        return ((self.current_price - self.entry_price) / self.entry_price) * 100 * direction_mult

    class Config:
        json_encoders = {
            Decimal: float,
            date: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# IRON CONDOR POSITION MODEL
# ═══════════════════════════════════════════════════════════

class IronCondorPosition(BaseModel):
    """
    Complete iron condor position with 4 legs.

    Iron Condor Structure:
    - Short Put (lower strike) - Sell to open
    - Long Put (even lower strike) - Buy for protection
    - Short Call (higher strike) - Sell to open
    - Long Call (even higher strike) - Buy for protection
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    ticker: str  # Underlying symbol (e.g., "SPY")
    strategy: str = "Iron Condor"
    expiry_date: date
    legs: List[OptionLeg]
    created_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def total_pnl(self) -> Decimal:
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
        return (
            len(self.legs) == 4 and
            self.short_put is not None and
            self.long_put is not None and
            self.short_call is not None and
            self.long_call is not None and
            self.long_put.strike < self.short_put.strike and
            self.short_call.strike < self.long_call.strike
        )

    class Config:
        json_encoders = {
            Decimal: float,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# PRICE UPDATE MODELS
# ═══════════════════════════════════════════════════════════

class OptionPriceUpdate(BaseModel):
    """
    Real-time price update for an option.
    Broadcast via WebSocket to update currentPrice in frontend.
    """
    symbol: str  # OCC symbol
    bid_price: Decimal
    ask_price: Decimal
    mid_price: Decimal  # (bid + ask) / 2
    last_price: Optional[Decimal] = None
    volume: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('bid_price', 'ask_price', 'mid_price', 'last_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))

    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class PositionPriceUpdates(BaseModel):
    """
    Batch of price updates for all legs in a position.
    Used for efficient WebSocket broadcasting.
    """
    position_id: str
    updates: Dict[str, OptionPriceUpdate]  # symbol -> update
    timestamp: datetime = Field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════
# API REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class GetPositionsResponse(BaseModel):
    """Response for GET /api/positions"""
    status: Literal['success', 'error']
    positions: List[IronCondorPosition] = []
    total_count: int = 0
    message: Optional[str] = None


class GetPositionResponse(BaseModel):
    """Response for GET /api/positions/{id}"""
    status: Literal['success', 'error']
    position: Optional[IronCondorPosition] = None
    message: Optional[str] = None


class SubscribePricesRequest(BaseModel):
    """Request to subscribe to price updates for specific symbols"""
    symbols: List[str]  # List of OCC symbols


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
]
```

**Acceptance Criteria:**
- [ ] OCCSymbol.parse() correctly parses "SPY260117C00688000"
- [ ] OptionLeg calculates P/L correctly for both Long and Short
- [ ] IronCondorPosition validates 4-leg structure
- [ ] All models serialize to JSON without errors

---

### 3. Create AlpacaService Class

Implement the core service for Alpaca API integration.

**File:** `apps/orchestrator_3_stream/backend/modules/alpaca_service.py`

```python
#!/usr/bin/env python3
"""
Alpaca Trading API Service

Provides:
- Position fetching via TradingClient
- Real-time price streaming via OptionDataStream
- Order update notifications via TradingStream
- Iron condor position detection and grouping
"""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass
from alpaca.data.live import OptionDataStream
from alpaca.trading.stream import TradingStream

from .config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_PAPER,
    ALPACA_DATA_FEED,
)
from .alpaca_models import (
    OCCSymbol,
    OptionLeg,
    IronCondorPosition,
    OptionPriceUpdate,
)
from .logger import get_logger
from .websocket_manager import get_websocket_manager

logger = get_logger()


class AlpacaService:
    """
    Service class for Alpaca Trading API integration.

    Handles:
    - REST: Position fetching and iron condor detection
    - WebSocket: Real-time option price streaming
    - Event: Order fill notifications
    """

    def __init__(self):
        self._trading_client: Optional[TradingClient] = None
        self._option_stream: Optional[OptionDataStream] = None
        self._trading_stream: Optional[TradingStream] = None
        self._subscribed_symbols: set = set()
        self._positions_cache: Dict[str, IronCondorPosition] = {}
        self._price_cache: Dict[str, OptionPriceUpdate] = {}
        self._stream_task: Optional[asyncio.Task] = None
        self._is_streaming = False
        self._price_callbacks: List[Callable] = []

    @property
    def is_configured(self) -> bool:
        """Check if Alpaca credentials are configured"""
        return bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    def _get_trading_client(self) -> TradingClient:
        """Get or create TradingClient instance"""
        if self._trading_client is None:
            if not self.is_configured:
                raise RuntimeError("Alpaca API credentials not configured")

            self._trading_client = TradingClient(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY,
                paper=ALPACA_PAPER
            )
            logger.info(f"Alpaca TradingClient initialized (paper={ALPACA_PAPER})")

        return self._trading_client

    def _get_option_stream(self) -> OptionDataStream:
        """Get or create OptionDataStream instance"""
        if self._option_stream is None:
            if not self.is_configured:
                raise RuntimeError("Alpaca API credentials not configured")

            self._option_stream = OptionDataStream(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY,
            )
            logger.info("Alpaca OptionDataStream initialized")

        return self._option_stream

    # ═══════════════════════════════════════════════════════════
    # POSITION FETCHING (REST)
    # ═══════════════════════════════════════════════════════════

    async def get_all_positions(self) -> List[IronCondorPosition]:
        """
        Fetch all option positions and group them into iron condors.

        Returns:
            List of detected iron condor positions
        """
        try:
            client = self._get_trading_client()

            # Get all positions (sync call, run in executor)
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(
                None, client.get_all_positions
            )

            # Filter for options only
            option_positions = [
                p for p in positions
                if hasattr(p, 'asset_class') and str(p.asset_class) == 'us_option'
            ]

            logger.info(f"Fetched {len(option_positions)} option positions from Alpaca")

            # Group into iron condors
            iron_condors = self._group_into_iron_condors(option_positions)

            # Cache positions
            for ic in iron_condors:
                self._positions_cache[ic.id] = ic

            return iron_condors

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    async def get_position_by_id(self, position_id: str) -> Optional[IronCondorPosition]:
        """Get a specific iron condor position by ID"""
        # Check cache first
        if position_id in self._positions_cache:
            return self._positions_cache[position_id]

        # Refresh positions
        await self.get_all_positions()
        return self._positions_cache.get(position_id)

    def _group_into_iron_condors(self, positions: list) -> List[IronCondorPosition]:
        """
        Group option positions into iron condor structures.

        Logic:
        1. Group by underlying + expiry
        2. Look for 4-leg iron condor pattern
        3. Validate structure (2 puts + 2 calls, proper directions)
        """
        # Group by underlying and expiry
        grouped: Dict[tuple, list] = defaultdict(list)

        for pos in positions:
            try:
                occ = OCCSymbol.parse(pos.symbol)
                key = (occ.underlying, occ.expiry_date)
                grouped[key].append((pos, occ))
            except ValueError as e:
                logger.warning(f"Skipping invalid symbol {pos.symbol}: {e}")
                continue

        iron_condors = []

        for (underlying, expiry), legs in grouped.items():
            # Need exactly 4 legs for iron condor
            if len(legs) != 4:
                logger.debug(f"Skipping {underlying} {expiry}: {len(legs)} legs (need 4)")
                continue

            # Separate into calls and puts
            calls = [(p, o) for p, o in legs if o.option_type == 'Call']
            puts = [(p, o) for p, o in legs if o.option_type == 'Put']

            if len(calls) != 2 or len(puts) != 2:
                logger.debug(f"Skipping {underlying} {expiry}: not 2C+2P structure")
                continue

            # Build option legs
            option_legs = []
            for pos, occ in legs:
                qty = int(pos.qty)
                direction = 'Short' if qty < 0 else 'Long'

                leg = OptionLeg(
                    symbol=pos.symbol,
                    direction=direction,
                    strike=occ.strike_price,
                    option_type=occ.option_type,
                    quantity=abs(qty),
                    entry_price=Decimal(str(pos.avg_entry_price)) if pos.avg_entry_price else Decimal("0"),
                    current_price=Decimal(str(pos.current_price)) if pos.current_price else Decimal("0"),
                    expiry_date=occ.expiry_date,
                    underlying=occ.underlying
                )
                option_legs.append(leg)

            ic = IronCondorPosition(
                ticker=underlying,
                expiry_date=expiry,
                legs=option_legs
            )

            if ic.is_valid_iron_condor():
                iron_condors.append(ic)
                logger.info(f"Detected iron condor: {underlying} exp {expiry}")
            else:
                logger.debug(f"Skipping {underlying} {expiry}: invalid IC structure")

        return iron_condors

    # ═══════════════════════════════════════════════════════════
    # PRICE STREAMING (WebSocket)
    # ═══════════════════════════════════════════════════════════

    async def start_price_streaming(self, symbols: List[str]) -> None:
        """
        Start streaming prices for given option symbols.

        Args:
            symbols: List of OCC option symbols to stream
        """
        if not symbols:
            logger.warning("No symbols provided for price streaming")
            return

        # Add to subscribed set
        new_symbols = set(symbols) - self._subscribed_symbols
        if not new_symbols:
            logger.debug("All symbols already subscribed")
            return

        self._subscribed_symbols.update(new_symbols)

        stream = self._get_option_stream()

        # Register quote handler
        async def quote_handler(quote):
            await self._handle_quote_update(quote)

        # Subscribe to quotes for new symbols
        stream.subscribe_quotes(quote_handler, *new_symbols)
        logger.info(f"Subscribed to quotes for {len(new_symbols)} symbols")

        # Start stream if not already running
        if not self._is_streaming:
            self._stream_task = asyncio.create_task(self._run_stream())
            self._is_streaming = True

    async def _run_stream(self):
        """Run the option data stream (blocking)"""
        try:
            stream = self._get_option_stream()
            logger.info("Starting OptionDataStream...")
            await asyncio.get_event_loop().run_in_executor(None, stream.run)
        except Exception as e:
            logger.error(f"OptionDataStream error: {e}")
            self._is_streaming = False

    async def _handle_quote_update(self, quote) -> None:
        """
        Handle incoming quote update from Alpaca.

        Broadcasts update to all connected WebSocket clients.
        """
        try:
            symbol = quote.symbol

            bid = Decimal(str(quote.bid_price)) if quote.bid_price else Decimal("0")
            ask = Decimal(str(quote.ask_price)) if quote.ask_price else Decimal("0")
            mid = (bid + ask) / 2 if bid and ask else bid or ask

            update = OptionPriceUpdate(
                symbol=symbol,
                bid_price=bid,
                ask_price=ask,
                mid_price=mid,
                last_price=None,  # Quotes don't have last price
                volume=0
            )

            # Cache the update
            self._price_cache[symbol] = update

            # Broadcast via WebSocket
            ws_manager = get_websocket_manager()
            await ws_manager.broadcast_option_price_update(update.model_dump())

            logger.debug(f"Price update: {symbol} bid={bid} ask={ask}")

        except Exception as e:
            logger.error(f"Error handling quote update: {e}")

    async def stop_price_streaming(self) -> None:
        """Stop the price streaming"""
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        if self._option_stream:
            self._option_stream.stop()

        self._is_streaming = False
        self._subscribed_symbols.clear()
        logger.info("Price streaming stopped")

    def get_cached_price(self, symbol: str) -> Optional[OptionPriceUpdate]:
        """Get cached price for a symbol"""
        return self._price_cache.get(symbol)

    # ═══════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════

    async def shutdown(self) -> None:
        """Clean shutdown of all connections"""
        await self.stop_price_streaming()

        if self._trading_client:
            # TradingClient doesn't have a close method
            self._trading_client = None

        logger.info("AlpacaService shutdown complete")


# Global service instance
_alpaca_service: Optional[AlpacaService] = None


def get_alpaca_service() -> AlpacaService:
    """Get the global AlpacaService instance"""
    global _alpaca_service
    if _alpaca_service is None:
        _alpaca_service = AlpacaService()
    return _alpaca_service


async def init_alpaca_service() -> AlpacaService:
    """Initialize the Alpaca service (call during app startup)"""
    service = get_alpaca_service()
    if service.is_configured:
        logger.success("AlpacaService initialized and ready")
    else:
        logger.warning("AlpacaService: credentials not configured")
    return service
```

**Acceptance Criteria:**
- [ ] Service initializes TradingClient correctly
- [ ] get_all_positions() fetches and groups iron condors
- [ ] Price streaming subscribes and receives updates
- [ ] Graceful shutdown cleans up all resources

---

### 4. Add WebSocket Broadcast Method

Extend the WebSocket manager to broadcast option price updates.

**File:** `apps/orchestrator_3_stream/backend/modules/websocket_manager.py`

Add after line 274 (after adw_event_summary_update):

```python
    # ========================================================================
    # Alpaca Options Broadcasting
    # ========================================================================

    async def broadcast_option_price_update(self, update_data: dict):
        """
        Broadcast real-time option price update.

        Used by AlpacaService to push price changes to frontend.

        Args:
            update_data: Dict with symbol, bid_price, ask_price, mid_price, timestamp
        """
        await self.broadcast({
            "type": "option_price_update",
            "update": update_data
        })

    async def broadcast_position_update(self, position_data: dict):
        """
        Broadcast position update (e.g., after order fill).

        Args:
            position_data: Full position data including all legs
        """
        await self.broadcast({
            "type": "position_update",
            "position": position_data
        })
```

**Acceptance Criteria:**
- [ ] broadcast_option_price_update sends correct message type
- [ ] broadcast_position_update sends correct message type
- [ ] Both methods add timestamp if not present

---

### 5. Create REST Endpoints

Add FastAPI endpoints for position data.

**File:** `apps/orchestrator_3_stream/backend/main.py`

Add imports at top:
```python
from modules.alpaca_service import get_alpaca_service, init_alpaca_service
from modules.alpaca_models import (
    GetPositionsResponse,
    GetPositionResponse,
    SubscribePricesRequest,
)
```

Add in lifespan startup (after other service initializations):
```python
    # Initialize Alpaca service
    alpaca_service = await init_alpaca_service()
    app.state.alpaca_service = alpaca_service
```

Add in lifespan shutdown:
```python
    # Shutdown Alpaca service
    if hasattr(app.state, 'alpaca_service'):
        await app.state.alpaca_service.shutdown()
```

Add new endpoints (after ADW endpoints, before WebSocket):

```python
# ============================================================================
# ALPACA TRADING ENDPOINTS
# ============================================================================

@app.get("/api/positions", response_model=GetPositionsResponse)
async def get_positions():
    """
    Get all iron condor positions from Alpaca.

    Returns grouped iron condor positions with all leg details.
    """
    try:
        alpaca_service = get_alpaca_service()

        if not alpaca_service.is_configured:
            return GetPositionsResponse(
                status="error",
                message="Alpaca API not configured"
            )

        positions = await alpaca_service.get_all_positions()

        return GetPositionsResponse(
            status="success",
            positions=positions,
            total_count=len(positions)
        )

    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return GetPositionsResponse(
            status="error",
            message=str(e)
        )


@app.get("/api/positions/{position_id}", response_model=GetPositionResponse)
async def get_position(position_id: str):
    """
    Get a specific iron condor position by ID.
    """
    try:
        alpaca_service = get_alpaca_service()

        if not alpaca_service.is_configured:
            return GetPositionResponse(
                status="error",
                message="Alpaca API not configured"
            )

        position = await alpaca_service.get_position_by_id(position_id)

        if position is None:
            return GetPositionResponse(
                status="error",
                message=f"Position not found: {position_id}"
            )

        return GetPositionResponse(
            status="success",
            position=position
        )

    except Exception as e:
        logger.error(f"Failed to get position {position_id}: {e}")
        return GetPositionResponse(
            status="error",
            message=str(e)
        )


@app.post("/api/positions/subscribe-prices")
async def subscribe_prices(request: SubscribePricesRequest):
    """
    Subscribe to real-time price updates for option symbols.

    Call this after loading positions to start receiving
    WebSocket price updates.
    """
    try:
        alpaca_service = get_alpaca_service()

        if not alpaca_service.is_configured:
            return {"status": "error", "message": "Alpaca API not configured"}

        await alpaca_service.start_price_streaming(request.symbols)

        return {
            "status": "success",
            "message": f"Subscribed to {len(request.symbols)} symbols",
            "symbols": request.symbols
        }

    except Exception as e:
        logger.error(f"Failed to subscribe to prices: {e}")
        return {"status": "error", "message": str(e)}
```

**Acceptance Criteria:**
- [ ] GET /api/positions returns list of iron condors
- [ ] GET /api/positions/{id} returns single position
- [ ] POST /api/positions/subscribe-prices starts streaming
- [ ] All endpoints handle errors gracefully

---

### 6. Update Frontend WebSocket Callbacks

Add handlers for new WebSocket events.

**File:** `apps/orchestrator_3_stream/frontend/src/services/chatService.ts`

Add to WebSocketCallbacks interface (after line 75):
```typescript
  // Alpaca price streaming events
  onOptionPriceUpdate?: (data: any) => void
  onPositionUpdate?: (data: any) => void
```

Add cases in switch statement (after adw_event_summary_update case):
```typescript
        // Alpaca price updates
        case 'option_price_update':
          callbacks.onOptionPriceUpdate?.(message)
          break

        case 'position_update':
          callbacks.onPositionUpdate?.(message)
          break
```

**Acceptance Criteria:**
- [ ] WebSocketCallbacks interface includes new event handlers
- [ ] Switch statement routes new event types correctly

---

### 7. Create TypeScript Interfaces

Define TypeScript types for Alpaca data structures.

**File:** `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`

```typescript
/**
 * Alpaca Trading API TypeScript Interfaces
 *
 * These interfaces match the backend Pydantic models
 * and the IronCondorCard component's expected data structure.
 */

/**
 * Single option leg within an iron condor position
 */
export interface OptionLeg {
  id: string
  symbol: string  // OCC symbol
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'
  quantity: number
  entryPrice: number
  currentPrice: number
  expiryDate: string  // ISO date string
  underlying: string
  // Computed fields (calculated on frontend)
  pnlDollars?: number
  pnlPercent?: number
}

/**
 * Iron condor position with 4 legs
 */
export interface IronCondorPosition {
  id: string
  ticker: string
  strategy: string
  expiryDate: string  // ISO date string
  legs: OptionLeg[]
  createdAt: string  // ISO datetime string
  // Computed fields
  totalPnl?: number
  daysToExpiry?: number
}

/**
 * Real-time price update for an option
 */
export interface OptionPriceUpdate {
  symbol: string
  bidPrice: number
  askPrice: number
  midPrice: number
  lastPrice?: number
  volume: number
  timestamp: string
}

/**
 * Position price updates (batch)
 */
export interface PositionPriceUpdates {
  positionId: string
  updates: Record<string, OptionPriceUpdate>
  timestamp: string
}

/**
 * API response for GET /api/positions
 */
export interface GetPositionsResponse {
  status: 'success' | 'error'
  positions: IronCondorPosition[]
  totalCount: number
  message?: string
}

/**
 * API response for GET /api/positions/{id}
 */
export interface GetPositionResponse {
  status: 'success' | 'error'
  position?: IronCondorPosition
  message?: string
}

/**
 * Request for POST /api/positions/subscribe-prices
 */
export interface SubscribePricesRequest {
  symbols: string[]
}

/**
 * WebSocket message for option_price_update
 */
export interface OptionPriceUpdateMessage {
  type: 'option_price_update'
  update: OptionPriceUpdate
  timestamp: string
}

/**
 * WebSocket message for position_update
 */
export interface PositionUpdateMessage {
  type: 'position_update'
  position: IronCondorPosition
  timestamp: string
}

/**
 * Transform backend snake_case to frontend camelCase
 */
export function transformOptionLeg(leg: any): OptionLeg {
  return {
    id: leg.id,
    symbol: leg.symbol,
    direction: leg.direction,
    strike: Number(leg.strike),
    optionType: leg.option_type,
    quantity: leg.quantity,
    entryPrice: Number(leg.entry_price),
    currentPrice: Number(leg.current_price),
    expiryDate: leg.expiry_date,
    underlying: leg.underlying,
    pnlDollars: leg.pnl_dollars ? Number(leg.pnl_dollars) : undefined,
    pnlPercent: leg.pnl_percent ? Number(leg.pnl_percent) : undefined,
  }
}

export function transformPosition(position: any): IronCondorPosition {
  return {
    id: position.id,
    ticker: position.ticker,
    strategy: position.strategy,
    expiryDate: position.expiry_date,
    legs: position.legs.map(transformOptionLeg),
    createdAt: position.created_at,
    totalPnl: position.total_pnl ? Number(position.total_pnl) : undefined,
    daysToExpiry: position.days_to_expiry,
  }
}

export function transformPriceUpdate(update: any): OptionPriceUpdate {
  return {
    symbol: update.symbol,
    bidPrice: Number(update.bid_price),
    askPrice: Number(update.ask_price),
    midPrice: Number(update.mid_price),
    lastPrice: update.last_price ? Number(update.last_price) : undefined,
    volume: update.volume,
    timestamp: update.timestamp,
  }
}
```

**Acceptance Criteria:**
- [ ] All interfaces match backend models
- [ ] Transform functions handle snake_case to camelCase
- [ ] Types are exported and usable

---

### 8. Create Frontend Alpaca Service

Add REST API client for positions.

**File:** `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts`

```typescript
/**
 * Alpaca Service
 *
 * REST API client for Alpaca trading endpoints
 */

import { apiClient } from './api'
import type {
  GetPositionsResponse,
  GetPositionResponse,
  SubscribePricesRequest,
  IronCondorPosition,
  transformPosition,
} from '../types/alpaca'
import { transformPosition as transform } from '../types/alpaca'

/**
 * Fetch all iron condor positions from Alpaca
 */
export async function getPositions(): Promise<IronCondorPosition[]> {
  const response = await apiClient.get<GetPositionsResponse>('/api/positions')

  if (response.data.status === 'error') {
    throw new Error(response.data.message || 'Failed to fetch positions')
  }

  return response.data.positions.map(transform)
}

/**
 * Fetch a specific position by ID
 */
export async function getPositionById(positionId: string): Promise<IronCondorPosition | null> {
  const response = await apiClient.get<GetPositionResponse>(`/api/positions/${positionId}`)

  if (response.data.status === 'error') {
    if (response.data.message?.includes('not found')) {
      return null
    }
    throw new Error(response.data.message || 'Failed to fetch position')
  }

  return response.data.position ? transform(response.data.position) : null
}

/**
 * Subscribe to real-time price updates for option symbols
 */
export async function subscribePrices(symbols: string[]): Promise<void> {
  const response = await apiClient.post('/api/positions/subscribe-prices', {
    symbols
  } as SubscribePricesRequest)

  if (response.data.status === 'error') {
    throw new Error(response.data.message || 'Failed to subscribe to prices')
  }
}

/**
 * Extract all option symbols from positions for price subscription
 */
export function extractSymbolsFromPositions(positions: IronCondorPosition[]): string[] {
  const symbols: string[] = []

  for (const position of positions) {
    for (const leg of position.legs) {
      if (leg.symbol && !symbols.includes(leg.symbol)) {
        symbols.push(leg.symbol)
      }
    }
  }

  return symbols
}
```

**Acceptance Criteria:**
- [ ] getPositions() fetches and transforms positions
- [ ] getPositionById() handles not found case
- [ ] subscribePrices() initiates streaming
- [ ] extractSymbolsFromPositions() collects all symbols

---

### 9. Create useAlpacaPositions Composable

Vue composable for position management.

**File:** `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`

```typescript
/**
 * useAlpacaPositions Composable
 *
 * Manages fetching and caching of iron condor positions from Alpaca.
 * Provides reactive state for loading, errors, and position data.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { IronCondorPosition } from '../types/alpaca'
import { getPositions, getPositionById, subscribePrices, extractSymbolsFromPositions } from '../services/alpacaService'

interface UseAlpacaPositionsOptions {
  /** Auto-fetch positions on mount */
  autoFetch?: boolean
  /** Auto-subscribe to price updates after fetching */
  autoSubscribe?: boolean
  /** Specific position ID to fetch (for single position view) */
  positionId?: string
}

export function useAlpacaPositions(options: UseAlpacaPositionsOptions = {}) {
  const {
    autoFetch = true,
    autoSubscribe = true,
    positionId = undefined
  } = options

  // State
  const positions = ref<IronCondorPosition[]>([])
  const currentPosition = ref<IronCondorPosition | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isSubscribed = ref(false)

  // Computed
  const hasPositions = computed(() => positions.value.length > 0)
  const positionCount = computed(() => positions.value.length)

  /**
   * Fetch all positions from Alpaca
   */
  async function fetchPositions(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      positions.value = await getPositions()

      // Auto-subscribe to price updates
      if (autoSubscribe && positions.value.length > 0) {
        await subscribeToUpdates()
      }

    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch positions'
      error.value = message
      console.error('useAlpacaPositions.fetchPositions error:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch a specific position by ID
   */
  async function fetchPosition(id: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      currentPosition.value = await getPositionById(id)

      if (currentPosition.value && autoSubscribe) {
        const symbols = extractSymbolsFromPositions([currentPosition.value])
        await subscribePrices(symbols)
        isSubscribed.value = true
      }

    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch position'
      error.value = message
      console.error('useAlpacaPositions.fetchPosition error:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Subscribe to price updates for all position symbols
   */
  async function subscribeToUpdates(): Promise<void> {
    if (isSubscribed.value) return

    try {
      const symbols = extractSymbolsFromPositions(positions.value)

      if (symbols.length > 0) {
        await subscribePrices(symbols)
        isSubscribed.value = true
        console.log(`Subscribed to ${symbols.length} option symbols`)
      }

    } catch (e) {
      console.error('Failed to subscribe to price updates:', e)
      // Don't set error - this is non-critical
    }
  }

  /**
   * Refresh positions (re-fetch from API)
   */
  async function refresh(): Promise<void> {
    if (positionId) {
      await fetchPosition(positionId)
    } else {
      await fetchPositions()
    }
  }

  /**
   * Find a position by ID in cached positions
   */
  function findPosition(id: string): IronCondorPosition | undefined {
    return positions.value.find(p => p.id === id)
  }

  /**
   * Update a leg's current price (called from price stream)
   */
  function updateLegPrice(symbol: string, newPrice: number): void {
    for (const position of positions.value) {
      for (const leg of position.legs) {
        if (leg.symbol === symbol) {
          leg.currentPrice = newPrice
          // Recalculate P/L
          const multiplier = leg.direction === 'Short' ? 1 : -1
          const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
          leg.pnlDollars = priceDiff * leg.quantity * 100
          leg.pnlPercent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * (leg.direction === 'Short' ? -1 : 1)
        }
      }
    }

    // Also update current position if applicable
    if (currentPosition.value) {
      for (const leg of currentPosition.value.legs) {
        if (leg.symbol === symbol) {
          leg.currentPrice = newPrice
        }
      }
    }
  }

  // Lifecycle
  onMounted(() => {
    if (autoFetch) {
      if (positionId) {
        fetchPosition(positionId)
      } else {
        fetchPositions()
      }
    }
  })

  return {
    // State
    positions,
    currentPosition,
    loading,
    error,
    isSubscribed,

    // Computed
    hasPositions,
    positionCount,

    // Actions
    fetchPositions,
    fetchPosition,
    subscribeToUpdates,
    refresh,
    findPosition,
    updateLegPrice,
  }
}
```

**Acceptance Criteria:**
- [ ] Auto-fetches positions on mount when enabled
- [ ] Auto-subscribes to price updates when enabled
- [ ] updateLegPrice() correctly updates reactive state
- [ ] Error handling doesn't crash component

---

### 10. Create useAlpacaPriceStream Composable

Vue composable for WebSocket price streaming.

**File:** `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts`

```typescript
/**
 * useAlpacaPriceStream Composable
 *
 * Handles WebSocket price updates for option legs.
 * Integrates with the existing orchestrator WebSocket connection.
 */

import { ref, watch, onUnmounted } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OptionPriceUpdate } from '../types/alpaca'
import { transformPriceUpdate } from '../types/alpaca'

interface PriceStreamCallbacks {
  onPriceUpdate?: (update: OptionPriceUpdate) => void
}

export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
  const store = useOrchestratorStore()

  // State
  const priceCache = ref<Map<string, OptionPriceUpdate>>(new Map())
  const lastUpdate = ref<Date | null>(null)
  const updateCount = ref(0)

  /**
   * Get the latest cached price for a symbol
   */
  function getPrice(symbol: string): OptionPriceUpdate | undefined {
    return priceCache.value.get(symbol)
  }

  /**
   * Get the mid price for a symbol (for display)
   */
  function getMidPrice(symbol: string): number | undefined {
    return priceCache.value.get(symbol)?.midPrice
  }

  /**
   * Handle incoming price update from WebSocket
   */
  function handlePriceUpdate(message: any): void {
    try {
      const update = transformPriceUpdate(message.update)

      // Cache the update
      priceCache.value.set(update.symbol, update)
      lastUpdate.value = new Date()
      updateCount.value++

      // Call user callback
      callbacks.onPriceUpdate?.(update)

    } catch (e) {
      console.error('Failed to process price update:', e)
    }
  }

  /**
   * Clear the price cache
   */
  function clearCache(): void {
    priceCache.value.clear()
    updateCount.value = 0
  }

  return {
    // State
    priceCache,
    lastUpdate,
    updateCount,

    // Methods
    getPrice,
    getMidPrice,
    handlePriceUpdate,
    clearCache,
  }
}
```

**Acceptance Criteria:**
- [ ] Caches price updates by symbol
- [ ] handlePriceUpdate transforms and stores updates
- [ ] getMidPrice returns number for display

---

### 11. Update Orchestrator Store

Add state management for positions and prices.

**File:** `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`

Add to state (find appropriate location in state definitions):
```typescript
  // Alpaca position state
  alpacaPositions: [] as IronCondorPosition[],
  alpacaPriceCache: new Map<string, OptionPriceUpdate>(),
  alpacaPositionsLoading: false,
  alpacaPositionsError: null as string | null,
```

Add import at top:
```typescript
import type { IronCondorPosition, OptionPriceUpdate } from '../types/alpaca'
import { transformPosition, transformPriceUpdate } from '../types/alpaca'
```

Add actions:
```typescript
  // Alpaca position actions
  setAlpacaPositions(positions: IronCondorPosition[]) {
    this.alpacaPositions = positions
  },

  updateOptionPrice(symbol: string, update: OptionPriceUpdate) {
    this.alpacaPriceCache.set(symbol, update)

    // Update currentPrice in all matching legs
    for (const position of this.alpacaPositions) {
      for (const leg of position.legs) {
        if (leg.symbol === symbol) {
          leg.currentPrice = update.midPrice
        }
      }
    }
  },

  setAlpacaLoading(loading: boolean) {
    this.alpacaPositionsLoading = loading
  },

  setAlpacaError(error: string | null) {
    this.alpacaPositionsError = error
  },
```

Update WebSocket connection to handle new events:
```typescript
  // In connectWebSocket method, add handlers:
  onOptionPriceUpdate: (message: any) => {
    const update = transformPriceUpdate(message.update)
    this.updateOptionPrice(update.symbol, update)
  },

  onPositionUpdate: (message: any) => {
    const position = transformPosition(message.position)
    const index = this.alpacaPositions.findIndex(p => p.id === position.id)
    if (index >= 0) {
      this.alpacaPositions[index] = position
    } else {
      this.alpacaPositions.push(position)
    }
  },
```

**Acceptance Criteria:**
- [ ] Store holds alpacaPositions array
- [ ] updateOptionPrice updates both cache and leg prices
- [ ] WebSocket handlers update store on message

---

### 12. Update IronCondorCard Component

Connect the component to live Alpaca data.

**File:** `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`

Replace the `<script setup>` section:

```typescript
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Timer } from '@element-plus/icons-vue'
import { useAlpacaPositions } from '../composables/useAlpacaPositions'
import { useAlpacaPriceStream } from '../composables/useAlpacaPriceStream'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OptionLeg, IronCondorPosition } from '../types/alpaca'

// Props - pass position ID to fetch from API OR initialData for direct injection
const props = defineProps<{
  positionId?: string
  initialData?: IronCondorPosition
  /** Use mock data (for development/demo) */
  useMockData?: boolean
}>()

// Store for WebSocket integration
const store = useOrchestratorStore()

// Composables
const {
  positions,
  currentPosition,
  loading,
  error,
  fetchPosition,
  fetchPositions,
  updateLegPrice,
} = useAlpacaPositions({
  autoFetch: !props.useMockData && !props.initialData,
  autoSubscribe: !props.useMockData,
  positionId: props.positionId,
})

const { handlePriceUpdate, getMidPrice } = useAlpacaPriceStream({
  onPriceUpdate: (update) => {
    // Update leg prices when we receive updates
    updateLegPrice(update.symbol, update.midPrice)
  }
})

// Local state
const position = ref<IronCondorPosition | null>(null)

// Placeholder data - used when useMockData is true
const placeholderData: IronCondorPosition = {
  id: 'mock-1',
  ticker: 'SPY',
  strategy: 'Iron Condor',
  expiryDate: '2026-01-10',
  createdAt: new Date().toISOString(),
  legs: [
    { id: '1', symbol: 'SPY260110C00688000', direction: 'Short', strike: 688, optionType: 'Call', quantity: 10, entryPrice: 4.04, currentPrice: 3.25, expiryDate: '2026-01-10', underlying: 'SPY' },
    { id: '2', symbol: 'SPY260110C00697000', direction: 'Long', strike: 697, optionType: 'Call', quantity: 10, entryPrice: 0.53, currentPrice: 0.09, expiryDate: '2026-01-10', underlying: 'SPY' },
    { id: '3', symbol: 'SPY260110P00683000', direction: 'Long', strike: 683, optionType: 'Put', quantity: 10, entryPrice: 1.47, currentPrice: 0.53, expiryDate: '2026-01-10', underlying: 'SPY' },
    { id: '4', symbol: 'SPY260110P00688000', direction: 'Short', strike: 688, optionType: 'Put', quantity: 10, entryPrice: 2.90, currentPrice: 1.57, expiryDate: '2026-01-10', underlying: 'SPY' },
  ]
}

// Watch for position data changes
watch([currentPosition, positions], () => {
  if (props.positionId && currentPosition.value) {
    position.value = currentPosition.value
  } else if (positions.value.length > 0) {
    // Use first position if no specific ID
    position.value = positions.value[0]
  }
}, { immediate: true })

// Watch for WebSocket price updates via store
watch(
  () => store.alpacaPriceCache,
  (cache) => {
    if (!position.value) return

    // Update prices for all legs from cache
    for (const leg of position.value.legs) {
      const update = cache.get(leg.symbol)
      if (update) {
        leg.currentPrice = update.midPrice
      }
    }
  },
  { deep: true }
)

// Computed values
const daysToExpiry = computed(() => {
  if (!position.value) return 0
  const expiry = new Date(position.value.expiryDate)
  const today = new Date()
  return Math.max(0, Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)))
})

const totalPnL = computed(() => {
  if (!position.value) return 0
  return position.value.legs.reduce((sum, leg) => {
    return sum + calculateLegPnL(leg).dollars
  }, 0)
})

const sortedLegs = computed(() => {
  if (!position.value) return []
  const legs = [...position.value.legs]

  const calls = legs.filter(l => l.optionType === 'Call')
  const puts = legs.filter(l => l.optionType === 'Put')

  // Sort Calls: Long then Short
  calls.sort((a, b) => {
    if (a.direction === 'Long' && b.direction === 'Short') return -1
    if (a.direction === 'Short' && b.direction === 'Long') return 1
    return b.strike - a.strike
  })

  // Sort Puts: Short then Long
  puts.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike
  })

  return [...calls, ...puts]
})

// Helpers
const calculateLegPnL = (leg: OptionLeg) => {
  const multiplier = leg.direction === 'Short' ? 1 : -1
  const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
  const dollars = priceDiff * leg.quantity * 100
  const percent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * (leg.direction === 'Short' ? -1 : 1)
  return { dollars, percent }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const formatCurrency = (value: number) => `${value >= 0 ? '+' : ''}$${Math.abs(value).toLocaleString()}`
const formatPercent = (value: number) => `(${value >= 0 ? '+' : ''}${value.toFixed(2)}%)`

// Lifecycle
onMounted(() => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.useMockData) {
    position.value = placeholderData
  }
  // Otherwise, useAlpacaPositions will fetch automatically
})
</script>
```

**Acceptance Criteria:**
- [ ] Component fetches real positions when positionId provided
- [ ] Component updates prices via WebSocket
- [ ] useMockData prop allows demo mode
- [ ] initialData prop allows direct data injection
- [ ] Error states display appropriately

---

### 13. Add Unit Tests for OCC Parser

**File:** `apps/orchestrator_3_stream/backend/tests/test_occ_parser.py`

```python
#!/usr/bin/env python3
"""
Unit tests for OCC symbol parser
"""

import pytest
from datetime import date
from decimal import Decimal

from modules.alpaca_models import OCCSymbol


class TestOCCSymbolParser:
    """Tests for OCCSymbol.parse()"""

    def test_parse_spy_call(self):
        """Parse SPY call option"""
        result = OCCSymbol.parse("SPY260117C00688000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Call"
        assert result.strike_price == Decimal("688")

    def test_parse_spy_put(self):
        """Parse SPY put option"""
        result = OCCSymbol.parse("SPY260117P00683000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Put"
        assert result.strike_price == Decimal("683")

    def test_parse_fractional_strike(self):
        """Parse option with fractional strike"""
        result = OCCSymbol.parse("AAPL250321C00142500")

        assert result.underlying == "AAPL"
        assert result.strike_price == Decimal("142.5")

    def test_parse_single_char_underlying(self):
        """Parse option with single character underlying"""
        result = OCCSymbol.parse("F251219C00015000")

        assert result.underlying == "F"
        assert result.strike_price == Decimal("15")

    def test_parse_six_char_underlying(self):
        """Parse option with 6 character underlying"""
        result = OCCSymbol.parse("GOOGLL251219C01500000")

        assert result.underlying == "GOOGLL"
        assert result.strike_price == Decimal("1500")

    def test_invalid_format_raises(self):
        """Invalid format raises ValueError"""
        with pytest.raises(ValueError):
            OCCSymbol.parse("INVALID")

    def test_lowercase_normalized(self):
        """Lowercase input is normalized to uppercase"""
        result = OCCSymbol.parse("spy260117c00688000")

        assert result.underlying == "SPY"
        assert result.option_type == "Call"

    def test_raw_symbol_preserved(self):
        """Raw symbol is preserved"""
        result = OCCSymbol.parse("SPY260117C00688000")

        assert result.raw_symbol == "SPY260117C00688000"


class TestOptionLegPnL:
    """Tests for OptionLeg P/L calculations"""

    def test_short_call_profit(self):
        """Short call with price decrease = profit"""
        from modules.alpaca_models import OptionLeg

        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=Decimal("688"),
            option_type="Call",
            quantity=10,
            entry_price=Decimal("4.00"),
            current_price=Decimal("3.00"),
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Short: entry > current = profit
        # P/L = (entry - current) * qty * 100
        # = (4.00 - 3.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == Decimal("1000")

    def test_long_put_profit(self):
        """Long put with price increase = profit"""
        from modules.alpaca_models import OptionLeg

        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=Decimal("683"),
            option_type="Put",
            quantity=10,
            entry_price=Decimal("1.00"),
            current_price=Decimal("2.00"),
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Long: current > entry = profit
        # P/L = (current - entry) * qty * 100
        # But formula is (entry - current) * -1 = (current - entry)
        # = (2.00 - 1.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == Decimal("1000")
```

Run tests with:
```bash
cd apps/orchestrator_3_stream/backend
uv run pytest tests/test_occ_parser.py -v
```

**Acceptance Criteria:**
- [ ] All OCC parser tests pass
- [ ] P/L calculation tests pass for both directions

---

### 14. Add Dependencies

**File:** `apps/orchestrator_3_stream/backend/pyproject.toml`

Add to dependencies:
```toml
alpaca-py = "^0.43.0"
```

Run:
```bash
cd apps/orchestrator_3_stream/backend
uv add alpaca-py
```

**Acceptance Criteria:**
- [ ] alpaca-py installed successfully
- [ ] Import works without errors

---

### 15. Integration Testing

Create integration test to verify end-to-end flow.

**Steps:**
1. Set up paper trading account with test iron condor position
2. Start backend with Alpaca credentials
3. Open frontend and verify positions load
4. Verify WebSocket price updates flow through
5. Verify P/L calculations update in real-time

**Manual Test Checklist:**
- [ ] Backend starts without errors
- [ ] GET /api/positions returns iron condor data
- [ ] WebSocket connects and receives price updates
- [ ] IronCondorCard displays live data
- [ ] P/L updates when prices change
- [ ] Graceful handling when API credentials missing

## Testing Strategy

### Unit Tests
- OCC symbol parser (all format variations)
- P/L calculations (both directions, edge cases)
- Position grouping logic (4-leg detection)
- Pydantic model validation

### Integration Tests
- REST endpoint responses
- WebSocket event broadcasting
- Frontend composable state management
- Store updates from WebSocket

### Manual Testing
- Full flow with paper trading account
- Error scenarios (no positions, API down)
- Reconnection after WebSocket disconnect

## Acceptance Criteria

1. **Backend**
   - [ ] AlpacaService initializes with credentials from .env
   - [ ] GET /api/positions returns iron condor positions
   - [ ] WebSocket broadcasts price updates
   - [ ] OCC parser handles all valid symbol formats
   - [ ] Error handling for missing credentials

2. **Frontend**
   - [ ] IronCondorCard displays real position data
   - [ ] Prices update in real-time via WebSocket
   - [ ] P/L calculations are correct
   - [ ] Loading and error states work
   - [ ] Mock data mode works for development

3. **Integration**
   - [ ] End-to-end flow from Alpaca to UI works
   - [ ] Reconnection logic handles disconnects
   - [ ] Multiple positions display correctly

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# Backend - ensure code compiles
cd apps/orchestrator_3_stream/backend
uv run python -c "from modules.alpaca_service import AlpacaService; print('Import OK')"
uv run python -c "from modules.alpaca_models import OCCSymbol; print(OCCSymbol.parse('SPY260117C00688000'))"

# Run unit tests
uv run pytest tests/test_occ_parser.py -v

# Start backend (requires .env with credentials)
uv run uvicorn main:app --host 127.0.0.1 --port 9403 --reload

# Test endpoints (in another terminal)
curl http://127.0.0.1:9403/api/positions | jq .
curl http://127.0.0.1:9403/health | jq .

# Frontend - type check
cd ../frontend
npm run build
```

## Notes

### Dependencies
- Add `alpaca-py` via `uv add alpaca-py` in backend
- No new frontend dependencies needed

### Environment Variables Required
```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true
```

### OCC Symbol Format Reference
```
Format: {underlying}{YYMMDD}{C|P}{strike * 1000, 8 digits}

Examples:
- SPY260117C00688000 = SPY Call $688 exp 2026-01-17
- AAPL250321P00142500 = AAPL Put $142.50 exp 2025-03-21
```

### Iron Condor Structure
```
         Long Call (protection)
              ↓
         Short Call (sell premium)
    ─────────────────────────────── Stock Price
         Short Put (sell premium)
              ↓
         Long Put (protection)
```

### WebSocket Message Format
```json
{
  "type": "option_price_update",
  "update": {
    "symbol": "SPY260117C00688000",
    "bid_price": 3.20,
    "ask_price": 3.30,
    "mid_price": 3.25,
    "timestamp": "2026-01-09T12:00:00Z"
  }
}
```
