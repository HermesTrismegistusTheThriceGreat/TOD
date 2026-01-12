# Part 2: Alpaca Service

## Overview

**Scope:** Create the core AlpacaService class for Alpaca API integration
**Dependencies:** Part 1 (Pydantic Models)
**Estimated Time:** 2-3 hours

## Objectives

1. Implement AlpacaService with TradingClient for position fetching
2. Implement OptionDataStream for real-time price streaming
3. Add circuit breaker pattern for Alpaca API resilience
4. Add TTL-based cache eviction for price data
5. Use `app.state` pattern (NOT global singleton) for service instance
6. Use `asyncio.get_running_loop()` (NOT deprecated `get_event_loop()`)

## Review Feedback Addressed

| Issue | Severity | Fix |
|-------|----------|-----|
| No circuit breaker for Alpaca API | HIGH | Implement circuit breaker pattern |
| Use `app.state` pattern | MEDIUM | Store service in FastAPI app.state |
| Use `asyncio.get_running_loop()` | MEDIUM | Replace deprecated `get_event_loop()` |
| Add TTL-based cache eviction | MEDIUM | Implement cache with TTL expiration |

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` | Core Alpaca service |
| `apps/orchestrator_3_stream/backend/modules/circuit_breaker.py` | Circuit breaker utility |

### Files to Modify

| File | Change |
|------|--------|
| `apps/orchestrator_3_stream/backend/modules/config.py` | Add Alpaca configuration |
| `apps/orchestrator_3_stream/.env` | Add Alpaca credentials |

## Implementation Steps

### Step 1: Add Configuration

**File:** `apps/orchestrator_3_stream/.env`

Add these environment variables:

```env
# Alpaca Trading API
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
ALPACA_DATA_FEED=iex
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

# Circuit breaker settings
ALPACA_CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("ALPACA_CB_FAILURE_THRESHOLD", "5"))
ALPACA_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv("ALPACA_CB_RECOVERY_TIMEOUT", "60"))

# Cache settings
ALPACA_PRICE_CACHE_TTL_SECONDS = int(os.getenv("ALPACA_PRICE_CACHE_TTL", "300"))  # 5 minutes

# Validate Alpaca credentials
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    config_logger.warning("Alpaca API credentials not configured - trading features disabled")
```

### Step 2: Create Circuit Breaker

**File:** `apps/orchestrator_3_stream/backend/modules/circuit_breaker.py`

```python
#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation

Provides resilience for external API calls by:
- Tracking failures and opening circuit after threshold
- Allowing recovery attempts after timeout
- Preventing cascading failures

Usage:
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async with breaker:
        result = await external_api_call()
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for external API resilience.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        name: Optional name for logging
    """
    failure_threshold: int = 5
    recovery_timeout: int = 60
    name: str = "default"

    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _success_count: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery"""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed for recovery attempt"""
        if self._last_failure_time is None:
            return True
        recovery_time = self._last_failure_time + timedelta(seconds=self.recovery_timeout)
        return datetime.now() >= recovery_time

    def record_success(self):
        """Record a successful call"""
        self._failure_count = 0
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED

    def record_failure(self):
        """Record a failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        self._success_count = 0

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self):
        """Reset circuit to closed state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0

    async def __aenter__(self):
        """Context manager entry - check if circuit allows call"""
        if self.is_open:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is open. "
                f"Recovery in {self._time_until_recovery()} seconds."
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success or failure"""
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure()
        return False  # Don't suppress exceptions

    def _time_until_recovery(self) -> int:
        """Calculate seconds until recovery attempt"""
        if self._last_failure_time is None:
            return 0
        recovery_time = self._last_failure_time + timedelta(seconds=self.recovery_timeout)
        remaining = (recovery_time - datetime.now()).total_seconds()
        return max(0, int(remaining))


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking calls"""
    pass


def with_circuit_breaker(breaker: CircuitBreaker):
    """
    Decorator for functions protected by circuit breaker.

    Usage:
        @with_circuit_breaker(my_breaker)
        async def call_external_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> Any:
            async with breaker:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Step 3: Create Alpaca Service

**File:** `apps/orchestrator_3_stream/backend/modules/alpaca_service.py`

```python
#!/usr/bin/env python3
"""
Alpaca Trading API Service

Provides:
- Position fetching via TradingClient (REST)
- Real-time price streaming via OptionDataStream (WebSocket)
- Iron condor position detection and grouping
- Circuit breaker for API resilience
- TTL-based cache eviction

IMPORTANT: Use app.state pattern, not global singleton.
Initialize via init_alpaca_service(app) in lifespan.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING
from collections import defaultdict
from dataclasses import dataclass, field

from alpaca.trading.client import TradingClient
from alpaca.data.live import OptionDataStream

from .config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_PAPER,
    ALPACA_DATA_FEED,
    ALPACA_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    ALPACA_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    ALPACA_PRICE_CACHE_TTL_SECONDS,
)
from .alpaca_models import (
    OCCSymbol,
    OptionLeg,
    IronCondorPosition,
    OptionPriceUpdate,
)
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from .logger import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()


# ═══════════════════════════════════════════════════════════
# TTL CACHE FOR PRICE UPDATES
# ═══════════════════════════════════════════════════════════

@dataclass
class CachedPrice:
    """Price update with TTL tracking"""
    update: OptionPriceUpdate
    cached_at: datetime = field(default_factory=datetime.now)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired"""
        expiry = self.cached_at + timedelta(seconds=ttl_seconds)
        return datetime.now() >= expiry


class TTLCache:
    """Simple TTL-based cache for price updates"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, CachedPrice] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[OptionPriceUpdate]:
        """Get cached item if not expired"""
        if key not in self._cache:
            return None

        cached = self._cache[key]
        if cached.is_expired(self._ttl):
            del self._cache[key]
            return None

        return cached.update

    def set(self, key: str, value: OptionPriceUpdate):
        """Cache an item with current timestamp"""
        self._cache[key] = CachedPrice(update=value)

    def clear(self):
        """Clear all cached items"""
        self._cache.clear()

    def evict_expired(self):
        """Remove all expired entries"""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired(self._ttl)
        ]
        for key in expired_keys:
            del self._cache[key]

    @property
    def size(self) -> int:
        return len(self._cache)


# ═══════════════════════════════════════════════════════════
# ALPACA SERVICE
# ═══════════════════════════════════════════════════════════

class AlpacaService:
    """
    Service class for Alpaca Trading API integration.

    Handles:
    - REST: Position fetching and iron condor detection
    - WebSocket: Real-time option price streaming
    - Circuit breaker: API resilience
    - Caching: TTL-based price cache

    IMPORTANT: Do not instantiate directly. Use init_alpaca_service(app).
    """

    def __init__(self):
        self._trading_client: Optional[TradingClient] = None
        self._option_stream: Optional[OptionDataStream] = None
        self._subscribed_symbols: set = set()
        self._positions_cache: Dict[str, IronCondorPosition] = {}
        self._price_cache = TTLCache(ttl_seconds=ALPACA_PRICE_CACHE_TTL_SECONDS)
        self._stream_task: Optional[asyncio.Task] = None
        self._is_streaming = False
        self._price_callbacks: List[Callable] = []

        # Circuit breaker for API calls
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=ALPACA_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=ALPACA_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
            name="alpaca_api"
        )

        # WebSocket manager reference (set during init)
        self._ws_manager = None

    @property
    def is_configured(self) -> bool:
        """Check if Alpaca credentials are configured"""
        return bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    @property
    def circuit_state(self) -> str:
        """Get current circuit breaker state"""
        return self._circuit_breaker.state.value

    def set_websocket_manager(self, ws_manager):
        """Set WebSocket manager for broadcasting"""
        self._ws_manager = ws_manager

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

        Uses circuit breaker to handle API failures gracefully.

        Returns:
            List of detected iron condor positions

        Raises:
            CircuitBreakerOpenError: If circuit is open
            RuntimeError: If API call fails
        """
        try:
            async with self._circuit_breaker:
                client = self._get_trading_client()

                # Get all positions (sync call, run in executor)
                # IMPORTANT: Use get_running_loop(), not get_event_loop()
                loop = asyncio.get_running_loop()
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

        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open - returning cached positions")
            return list(self._positions_cache.values())

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
                    strike=float(occ.strike_price),
                    option_type=occ.option_type,
                    quantity=abs(qty),
                    entry_price=float(pos.avg_entry_price) if pos.avg_entry_price else 0.0,
                    current_price=float(pos.current_price) if pos.current_price else 0.0,
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
            # Use get_running_loop() for executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, stream.run)
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

            bid = float(quote.bid_price) if quote.bid_price else 0.0
            ask = float(quote.ask_price) if quote.ask_price else 0.0
            mid = (bid + ask) / 2 if bid and ask else bid or ask

            update = OptionPriceUpdate(
                symbol=symbol,
                bid_price=bid,
                ask_price=ask,
                mid_price=mid,
                last_price=None,  # Quotes don't have last price
                volume=0
            )

            # Cache the update (with TTL)
            self._price_cache.set(symbol, update)

            # Broadcast via WebSocket if manager is set
            if self._ws_manager:
                await self._ws_manager.broadcast_option_price_update(update.model_dump())

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
        """Get cached price for a symbol (if not expired)"""
        return self._price_cache.get(symbol)

    def evict_expired_cache(self):
        """Manually evict expired cache entries"""
        self._price_cache.evict_expired()

    # ═══════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════

    def add_price_callback(self, callback: Callable[[OptionPriceUpdate], None]):
        """Add callback for price updates"""
        self._price_callbacks.append(callback)

    def remove_price_callback(self, callback: Callable):
        """Remove price callback"""
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)

    # ═══════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════

    async def shutdown(self) -> None:
        """Clean shutdown of all connections"""
        await self.stop_price_streaming()

        if self._trading_client:
            # TradingClient doesn't have a close method
            self._trading_client = None

        self._price_cache.clear()
        self._positions_cache.clear()

        logger.info("AlpacaService shutdown complete")


# ═══════════════════════════════════════════════════════════
# APP.STATE INITIALIZATION (NOT GLOBAL SINGLETON)
# ═══════════════════════════════════════════════════════════

async def init_alpaca_service(app: "FastAPI") -> AlpacaService:
    """
    Initialize AlpacaService and store in app.state.

    IMPORTANT: Call this in FastAPI lifespan startup.

    Usage:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            alpaca_service = await init_alpaca_service(app)
            yield
            await alpaca_service.shutdown()

    Args:
        app: FastAPI application instance

    Returns:
        Initialized AlpacaService
    """
    service = AlpacaService()
    app.state.alpaca_service = service

    if service.is_configured:
        logger.success("AlpacaService initialized and ready")
    else:
        logger.warning("AlpacaService: credentials not configured")

    return service


def get_alpaca_service(app: "FastAPI") -> AlpacaService:
    """
    Get AlpacaService from app.state.

    Usage in endpoints:
        @app.get("/api/positions")
        async def get_positions(request: Request):
            service = get_alpaca_service(request.app)
            ...

    Args:
        app: FastAPI application instance

    Returns:
        AlpacaService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if not hasattr(app.state, 'alpaca_service'):
        raise RuntimeError("AlpacaService not initialized. Call init_alpaca_service() in lifespan.")
    return app.state.alpaca_service
```

## Testing Requirements

### Unit Tests

**File:** `apps/orchestrator_3_stream/backend/tests/test_alpaca_service.py`

```python
#!/usr/bin/env python3
"""
Unit tests for AlpacaService.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_service.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, '..')
from modules.alpaca_service import AlpacaService, TTLCache
from modules.alpaca_models import OptionPriceUpdate, IronCondorPosition, OptionLeg
from modules.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


class TestCircuitBreaker:
    """Tests for circuit breaker pattern"""

    def test_initial_state_closed(self):
        """Circuit breaker starts in closed state"""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.is_closed
        assert not breaker.is_open

    def test_opens_after_threshold(self):
        """Circuit opens after failure threshold"""
        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.is_open
        assert not breaker.is_closed

    def test_success_resets_failures(self):
        """Success resets failure count"""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()

        assert breaker._failure_count == 0
        assert breaker.is_closed

    def test_half_open_after_recovery_timeout(self):
        """Circuit becomes half-open after recovery timeout"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)

        breaker.record_failure()
        assert breaker._state == CircuitState.OPEN

        # After timeout, should be half-open
        assert breaker.state == CircuitState.HALF_OPEN

    def test_closes_on_success_in_half_open(self):
        """Success in half-open state closes circuit"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)

        breaker.record_failure()
        _ = breaker.state  # Trigger half-open check

        breaker.record_success()
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Context manager records success"""
        breaker = CircuitBreaker()

        async with breaker:
            pass

        assert breaker._success_count == 1

    @pytest.mark.asyncio
    async def test_context_manager_failure(self):
        """Context manager records failure on exception"""
        breaker = CircuitBreaker()

        with pytest.raises(ValueError):
            async with breaker:
                raise ValueError("test")

        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_context_manager_blocks_when_open(self):
        """Context manager raises when circuit is open"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        breaker.record_failure()

        with pytest.raises(CircuitBreakerOpenError):
            async with breaker:
                pass


class TestTTLCache:
    """Tests for TTL cache"""

    def test_set_and_get(self):
        """Basic set and get operations"""
        cache = TTLCache(ttl_seconds=300)

        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )

        cache.set("SPY260117C00688000", update)
        result = cache.get("SPY260117C00688000")

        assert result is not None
        assert result.symbol == "SPY260117C00688000"

    def test_get_missing_key(self):
        """Get returns None for missing key"""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        """Expired entries return None and are removed"""
        cache = TTLCache(ttl_seconds=0)  # Immediate expiry

        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )

        cache.set("SPY260117C00688000", update)

        # Wait briefly to ensure expiry
        import time
        time.sleep(0.01)

        assert cache.get("SPY260117C00688000") is None

    def test_evict_expired(self):
        """evict_expired removes all expired entries"""
        cache = TTLCache(ttl_seconds=0)

        for i in range(5):
            update = OptionPriceUpdate(
                symbol=f"SYM{i}",
                bid_price=1.0,
                ask_price=1.0,
                mid_price=1.0
            )
            cache.set(f"SYM{i}", update)

        import time
        time.sleep(0.01)

        cache.evict_expired()
        assert cache.size == 0

    def test_clear(self):
        """Clear removes all entries"""
        cache = TTLCache()

        for i in range(5):
            update = OptionPriceUpdate(
                symbol=f"SYM{i}",
                bid_price=1.0,
                ask_price=1.0,
                mid_price=1.0
            )
            cache.set(f"SYM{i}", update)

        cache.clear()
        assert cache.size == 0


class TestAlpacaService:
    """Tests for AlpacaService"""

    def test_is_configured_false_without_credentials(self):
        """is_configured returns False without credentials"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', ''):
            service = AlpacaService()
            assert service.is_configured is False

    def test_is_configured_true_with_credentials(self):
        """is_configured returns True with credentials"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', 'test_key'), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', 'test_secret'):
            service = AlpacaService()
            assert service.is_configured is True

    def test_circuit_state_property(self):
        """circuit_state returns current state"""
        service = AlpacaService()
        assert service.circuit_state == 'closed'

    def test_get_cached_price(self):
        """get_cached_price returns cached update"""
        service = AlpacaService()

        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )

        service._price_cache.set("SPY260117C00688000", update)

        result = service.get_cached_price("SPY260117C00688000")
        assert result is not None
        assert result.mid_price == 3.25

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Shutdown clears all state"""
        service = AlpacaService()

        # Add some cached data
        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )
        service._price_cache.set("SPY260117C00688000", update)

        await service.shutdown()

        assert service._price_cache.size == 0
        assert len(service._positions_cache) == 0
```

## Validation Commands

```bash
# Navigate to backend directory
cd apps/orchestrator_3_stream/backend

# Add alpaca-py dependency
uv add alpaca-py

# Verify imports
uv run python -c "
from modules.alpaca_service import AlpacaService, init_alpaca_service, get_alpaca_service
from modules.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
print('Imports OK')
"

# Verify circuit breaker
uv run python -c "
from modules.circuit_breaker import CircuitBreaker, CircuitState
breaker = CircuitBreaker(failure_threshold=3)
print(f'Initial state: {breaker.state}')
breaker.record_failure()
breaker.record_failure()
breaker.record_failure()
print(f'After 3 failures: {breaker.state}')
"

# Run tests
uv run pytest tests/test_alpaca_service.py -v
```

## Acceptance Criteria

- [ ] AlpacaService uses `app.state` pattern (not global singleton)
- [ ] Circuit breaker opens after failure threshold
- [ ] Circuit breaker recovers after timeout
- [ ] TTL cache evicts expired entries
- [ ] All `asyncio.get_event_loop()` replaced with `asyncio.get_running_loop()`
- [ ] Service initializes correctly with credentials
- [ ] Service handles missing credentials gracefully
- [ ] All unit tests pass

## Notes

### Circuit Breaker States

```
CLOSED → (failures >= threshold) → OPEN
   ↑                                  ↓
   └── (success in half-open) ←── HALF_OPEN ← (recovery timeout)
```

### App.state Pattern

```python
# In lifespan:
alpaca_service = await init_alpaca_service(app)

# In endpoints:
from fastapi import Request

@app.get("/api/positions")
async def get_positions(request: Request):
    service = get_alpaca_service(request.app)
    # ...
```
