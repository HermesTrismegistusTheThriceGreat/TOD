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
from alpaca.trading.enums import AssetClass, OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.data.live import OptionDataStream

from .config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_PAPER,
    ALPACA_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    ALPACA_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    ALPACA_PRICE_CACHE_TTL_SECONDS,
    ALPACA_PRICE_THROTTLE_MS,
)
from .alpaca_models import (
    OCCSymbol,
    OptionLeg,
    IronCondorPosition,
    OptionPriceUpdate,
    CloseOrderResult,
    CloseStrategyResponse,
    CloseLegResponse,
)
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from .rate_limiter import RateLimiter
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

    def set(self, key: str, value: OptionPriceUpdate) -> None:
        """Cache an item with current timestamp"""
        self._cache[key] = CachedPrice(update=value)

    def clear(self) -> None:
        """Clear all cached items"""
        self._cache.clear()

    def evict_expired(self) -> None:
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

        # Rate limiter for price updates (200ms default throttle)
        self._rate_limiter = RateLimiter(
            throttle_ms=ALPACA_PRICE_THROTTLE_MS,
            max_queue_size=100
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

    def set_websocket_manager(self, ws_manager: Any) -> None:
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
                    if hasattr(p, 'asset_class') and p.asset_class == AssetClass.US_OPTION
                ]

                logger.info(f"Fetched {len(option_positions)} option positions from Alpaca")

                # Group by ticker
                ticker_positions = self._group_by_ticker(option_positions)

                # Cache positions
                for pos in ticker_positions:
                    self._positions_cache[pos.id] = pos

                return ticker_positions

        except CircuitBreakerOpenError:
            logger.warning("Circuit breaker open - returning cached positions")
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

    def _group_by_ticker(self, positions: list) -> List[IronCondorPosition]:
        """
        Group option positions by ticker symbol.

        Logic:
        1. Group by underlying + expiry
        2. Create position for each group (no filtering)
        3. Detect strategy type based on leg structure
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

        ticker_positions = []

        for (underlying, expiry), legs in grouped.items():
            # Skip empty groups
            if len(legs) == 0:
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

            # Create position (using IronCondorPosition for backwards compatibility)
            position = IronCondorPosition(
                ticker=underlying,
                expiry_date=expiry,
                legs=option_legs
            )

            # Detect and set strategy type
            position.strategy = position.detect_strategy()

            ticker_positions.append(position)
            logger.info(f"Created {position.strategy} position: {underlying} exp {expiry} ({len(option_legs)} legs)")

        return ticker_positions

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
        async def quote_handler(quote: Any) -> None:
            await self._handle_quote_update(quote)

        # Subscribe to quotes for new symbols
        stream.subscribe_quotes(quote_handler, *new_symbols)
        logger.info(f"Subscribed to quotes for {len(new_symbols)} symbols")

        # Start stream if not already running
        if not self._is_streaming:
            self._stream_task = asyncio.create_task(self._run_stream())
            self._is_streaming = True

        # Broadcast status update
        if self._ws_manager:
            await self._ws_manager.broadcast_alpaca_status(
                "streaming_started",
                {"symbols": list(self._subscribed_symbols)}
            )

    async def _run_stream(self) -> None:
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

    async def _handle_quote_update(self, quote: Any) -> None:
        """
        Handle incoming quote update from Alpaca.

        Applies rate limiting and broadcasts update to connected clients.
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
                last_price=None,
                volume=0
            )

            # Cache the update (with TTL)
            self._price_cache.set(symbol, update)

            # Broadcast via WebSocket with rate limiting
            if self._ws_manager:
                async def send_update(data):
                    await self._ws_manager.broadcast_option_price_update(data)

                # Rate limit by symbol
                was_sent = await self._rate_limiter.throttle(
                    key=symbol,
                    data=update.model_dump(mode='json'),
                    send_callback=send_update
                )

                if was_sent:
                    logger.debug(f"Price update sent: {symbol} mid={mid}")
                else:
                    logger.debug(f"Price update throttled: {symbol}")

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

        # Broadcast status update
        if self._ws_manager:
            await self._ws_manager.broadcast_alpaca_status("streaming_stopped", {})

    def get_cached_price(self, symbol: str) -> Optional[OptionPriceUpdate]:
        """Get cached price for a symbol (if not expired)"""
        return self._price_cache.get(symbol)

    def evict_expired_cache(self) -> None:
        """Manually evict expired cache entries"""
        self._price_cache.evict_expired()

    # ═══════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════

    def add_price_callback(self, callback: Callable[[OptionPriceUpdate], None]) -> None:
        """Add callback for price updates"""
        self._price_callbacks.append(callback)

    def remove_price_callback(self, callback: Callable) -> None:
        """Remove price callback"""
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)

    # ═══════════════════════════════════════════════════════════
    # POSITION CLOSING (REST)
    # ═══════════════════════════════════════════════════════════

    def _determine_close_side(self, direction: str) -> OrderSide:
        """
        Determine the order side needed to close a position.

        Short positions: buy to close
        Long positions: sell to close
        """
        return OrderSide.BUY if direction == 'Short' else OrderSide.SELL

    async def close_leg(
        self,
        symbol: str,
        quantity: int,
        direction: str,
        order_type: str = 'market',
        limit_price: Optional[float] = None
    ) -> CloseOrderResult:
        """
        Close a single option leg.

        Args:
            symbol: OCC option symbol
            quantity: Number of contracts to close
            direction: 'Long' or 'Short' (current position direction)
            order_type: 'market' or 'limit'
            limit_price: Price for limit orders (required if order_type is 'limit')

        Returns:
            CloseOrderResult with order details
        """
        try:
            async with self._circuit_breaker:
                client = self._get_trading_client()
                side = self._determine_close_side(direction)

                logger.info(f"Closing leg: {symbol} qty={quantity} direction={direction} side={side.value}")

                # Create order request
                if order_type == 'limit' and limit_price is not None:
                    order_request = LimitOrderRequest(
                        symbol=symbol,
                        qty=quantity,
                        side=side,
                        time_in_force=TimeInForce.DAY,
                        limit_price=limit_price
                    )
                else:
                    order_request = MarketOrderRequest(
                        symbol=symbol,
                        qty=quantity,
                        side=side,
                        time_in_force=TimeInForce.DAY
                    )

                # Submit order via TradingClient (sync call, run in executor)
                loop = asyncio.get_running_loop()
                order = await loop.run_in_executor(
                    None, client.submit_order, order_request
                )

                logger.info(f"Order submitted: {order.id} status={order.status}")

                return CloseOrderResult(
                    symbol=symbol,
                    order_id=str(order.id),
                    status='submitted' if order.status.value in ['new', 'pending_new', 'accepted'] else 'filled',
                    filled_qty=int(order.filled_qty) if order.filled_qty else 0,
                    filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None
                )

        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open - cannot close leg {symbol}")
            return CloseOrderResult(
                symbol=symbol,
                order_id='',
                status='failed',
                error_message='Circuit breaker open - API unavailable'
            )

        except Exception as e:
            logger.error(f"Failed to close leg {symbol}: {e}")
            return CloseOrderResult(
                symbol=symbol,
                order_id='',
                status='failed',
                error_message=str(e)
            )

    async def close_strategy(
        self,
        position_id: str,
        order_type: str = 'market'
    ) -> CloseStrategyResponse:
        """
        Close an entire strategy (all legs).

        Args:
            position_id: UUID of the position to close
            order_type: 'market' or 'limit'

        Returns:
            CloseStrategyResponse with all order results
        """
        # Get position from cache or fetch
        position = self._positions_cache.get(position_id)
        if not position:
            position = await self.get_position_by_id(position_id)

        if not position:
            logger.error(f"Position not found: {position_id}")
            return CloseStrategyResponse(
                status='error',
                position_id=position_id,
                message=f'Position not found: {position_id}'
            )

        logger.info(f"Closing strategy: {position_id} ({position.ticker} {position.strategy}) with {len(position.legs)} legs")

        orders: List[CloseOrderResult] = []
        closed_count = 0

        # Close each leg
        for leg in position.legs:
            result = await self.close_leg(
                symbol=leg.symbol,
                quantity=leg.quantity,
                direction=leg.direction,
                order_type=order_type
            )
            orders.append(result)

            if result.status != 'failed':
                closed_count += 1

        # Determine overall status
        total_legs = len(position.legs)
        if closed_count == total_legs:
            status = 'success'
            message = f'Successfully closed all {total_legs} legs'
            # Clear position from cache on full success
            if position_id in self._positions_cache:
                del self._positions_cache[position_id]
        elif closed_count > 0:
            status = 'partial'
            message = f'Closed {closed_count}/{total_legs} legs'
        else:
            status = 'error'
            message = 'Failed to close any legs'

        logger.info(f"Close strategy result: {status} - {message}")

        # Broadcast status update via WebSocket
        if self._ws_manager:
            await self._ws_manager.broadcast_alpaca_status(
                "strategy_closed",
                {
                    "position_id": position_id,
                    "status": status,
                    "closed_legs": closed_count,
                    "total_legs": total_legs
                }
            )

        return CloseStrategyResponse(
            status=status,
            position_id=position_id,
            orders=orders,
            message=message,
            total_legs=total_legs,
            closed_legs=closed_count
        )

    # ═══════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════

    async def shutdown(self) -> None:
        """Clean shutdown of all connections"""
        await self.stop_price_streaming()

        # Clear rate limiter
        self._rate_limiter.clear()

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
