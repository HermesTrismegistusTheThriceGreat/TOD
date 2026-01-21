#!/usr/bin/env python3
"""
Spot Price Stream Service

Provides real-time stock quote streaming via Alpaca's StockDataStream WebSocket API.
Follows the same pattern as AlpacaService for consistency.

IMPORTANT: Use app.state pattern, not global singleton.
Initialize via init_spot_price_service(app) in lifespan.
"""

import asyncio
from typing import Optional, Any, TYPE_CHECKING, List, Set
from datetime import datetime

from alpaca.data.live import StockDataStream

from .config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_PRICE_THROTTLE_MS,
)
from .alpaca_models import SpotPriceUpdate
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from .rate_limiter import RateLimiter
from .logger import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()


# ═══════════════════════════════════════════════════════════
# SPOT PRICE STREAM SERVICE
# ═══════════════════════════════════════════════════════════

class SpotPriceStreamService:
    """
    Service for real-time stock quote streaming via Alpaca StockDataStream.

    Handles:
    - WebSocket: Real-time stock quote streaming
    - Rate limiting: Throttles broadcasts to prevent overwhelming clients
    - Circuit breaker: API resilience

    IMPORTANT: Do not instantiate directly. Use init_spot_price_service(app).
    """

    def __init__(self):
        self._stock_stream: Optional[StockDataStream] = None
        self._subscribed_symbols: Set[str] = set()
        self._stream_task: Optional[asyncio.Task] = None
        self._is_streaming = False

        # Circuit breaker for API calls
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="spot_price_stream"
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

    def _get_stock_stream(self) -> StockDataStream:
        """Get or create StockDataStream instance"""
        if self._stock_stream is None:
            if not self.is_configured:
                raise RuntimeError("Alpaca API credentials not configured")

            self._stock_stream = StockDataStream(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY,
            )
            logger.info("Alpaca StockDataStream initialized")

        return self._stock_stream

    # ═══════════════════════════════════════════════════════════
    # SPOT PRICE STREAMING (WebSocket)
    # ═══════════════════════════════════════════════════════════

    async def start_spot_streaming(self, symbols: List[str]) -> None:
        """
        Start streaming spot prices for given stock symbols.

        Args:
            symbols: List of stock symbols to stream (e.g., ["SPY", "QQQ"])
        """
        if not symbols:
            logger.warning("No symbols provided for spot price streaming")
            return

        # Add to subscribed set
        new_symbols = set(symbols) - self._subscribed_symbols
        if not new_symbols:
            logger.debug("All symbols already subscribed for spot prices")
            return

        self._subscribed_symbols.update(new_symbols)

        stream = self._get_stock_stream()

        # Register quote handler
        async def quote_handler(quote: Any) -> None:
            await self._handle_quote_update(quote)

        # Subscribe to quotes for new symbols
        stream.subscribe_quotes(quote_handler, *new_symbols)
        logger.info(f"Subscribed to spot price quotes for {len(new_symbols)} symbols: {list(new_symbols)}")

        # Start stream if not already running
        if not self._is_streaming:
            self._stream_task = asyncio.create_task(self._run_stream())
            self._is_streaming = True

        # Broadcast status update
        if self._ws_manager:
            await self._ws_manager.broadcast_alpaca_status(
                "spot_streaming_started",
                {"symbols": list(self._subscribed_symbols)}
            )

    async def _run_stream(self) -> None:
        """Run the stock data stream (blocking)"""
        try:
            stream = self._get_stock_stream()
            logger.info("Starting StockDataStream...")
            # Use get_running_loop() for executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, stream.run)
        except Exception as e:
            logger.error(f"StockDataStream error: {e}")
            self._is_streaming = False
            raise

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

            update = SpotPriceUpdate(
                symbol=symbol,
                bid_price=bid,
                ask_price=ask,
                mid_price=mid,
                last_price=None,
            )

            # Broadcast via WebSocket with rate limiting
            if self._ws_manager:
                async def send_update(data):
                    await self._ws_manager.broadcast_spot_price_update(data)

                # Rate limit by symbol
                was_sent = await self._rate_limiter.throttle(
                    key=symbol,
                    data=update.model_dump(mode='json'),
                    send_callback=send_update
                )

                if was_sent:
                    logger.debug(f"Spot price update sent: {symbol} mid={mid}")
                else:
                    logger.debug(f"Spot price update throttled: {symbol}")

        except Exception as e:
            logger.error(f"Error handling spot quote update: {e}")

    async def stop_spot_streaming(self) -> None:
        """Stop the spot price streaming"""
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        if self._stock_stream:
            self._stock_stream.stop()

        self._is_streaming = False
        self._subscribed_symbols.clear()
        logger.info("Spot price streaming stopped")

        # Broadcast status update
        if self._ws_manager:
            await self._ws_manager.broadcast_alpaca_status("spot_streaming_stopped", {})

    # ═══════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════

    async def shutdown(self) -> None:
        """Clean shutdown of all connections"""
        await self.stop_spot_streaming()

        # Clear rate limiter
        self._rate_limiter.clear()

        if self._stock_stream:
            self._stock_stream = None

        logger.info("SpotPriceStreamService shutdown complete")


# ═══════════════════════════════════════════════════════════
# APP.STATE INITIALIZATION (NOT GLOBAL SINGLETON)
# ═══════════════════════════════════════════════════════════

async def init_spot_price_service(app: "FastAPI") -> SpotPriceStreamService:
    """
    Initialize SpotPriceStreamService and store in app.state.

    IMPORTANT: Call this in FastAPI lifespan startup.

    Usage:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            spot_price_service = await init_spot_price_service(app)
            spot_price_service.set_websocket_manager(ws_manager)
            yield
            await spot_price_service.shutdown()

    Args:
        app: FastAPI application instance

    Returns:
        Initialized SpotPriceStreamService
    """
    service = SpotPriceStreamService()
    app.state.spot_price_service = service

    if service.is_configured:
        logger.success("SpotPriceStreamService initialized and ready")
    else:
        logger.warning("SpotPriceStreamService: credentials not configured")

    return service


def get_spot_price_service(app: "FastAPI") -> SpotPriceStreamService:
    """
    Get SpotPriceStreamService from app.state.

    Usage in endpoints:
        @app.post("/api/positions/subscribe-spot-prices")
        async def subscribe_spot_prices(request: Request):
            service = get_spot_price_service(request.app)
            ...

    Args:
        app: FastAPI application instance

    Returns:
        SpotPriceStreamService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if not hasattr(app.state, 'spot_price_service'):
        raise RuntimeError("SpotPriceStreamService not initialized. Call init_spot_price_service() in lifespan.")
    return app.state.spot_price_service
