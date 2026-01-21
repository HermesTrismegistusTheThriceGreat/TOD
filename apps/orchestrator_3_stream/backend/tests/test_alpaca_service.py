#!/usr/bin/env python3
"""
Unit tests for AlpacaService.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_service.py -v
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.alpaca_service import AlpacaService, TTLCache, CachedPrice
from modules.alpaca_models import OptionPriceUpdate, OptionsPosition, OptionLeg
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


class TestCachedPrice:
    """Tests for CachedPrice dataclass"""

    def test_is_expired_false_within_ttl(self):
        """CachedPrice is not expired within TTL"""
        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )
        cached = CachedPrice(update=update)

        assert cached.is_expired(ttl_seconds=300) is False

    def test_is_expired_true_after_ttl(self):
        """CachedPrice is expired after TTL"""
        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )
        # Create with timestamp in the past
        cached = CachedPrice(
            update=update,
            cached_at=datetime.now() - timedelta(seconds=400)
        )

        assert cached.is_expired(ttl_seconds=300) is True


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

    def test_size_property(self):
        """Size property returns correct count"""
        cache = TTLCache(ttl_seconds=300)

        assert cache.size == 0

        for i in range(3):
            update = OptionPriceUpdate(
                symbol=f"SYM{i}",
                bid_price=1.0,
                ask_price=1.0,
                mid_price=1.0
            )
            cache.set(f"SYM{i}", update)

        assert cache.size == 3


class TestAlpacaService:
    """Tests for AlpacaService"""

    def test_is_configured_false_without_credentials(self):
        """is_configured returns False without credentials"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', ''), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', ''):
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

    def test_get_cached_price_missing(self):
        """get_cached_price returns None for missing symbol"""
        service = AlpacaService()
        assert service.get_cached_price("NONEXISTENT") is None

    def test_set_websocket_manager(self):
        """set_websocket_manager sets the ws_manager"""
        service = AlpacaService()
        mock_ws_manager = Mock()

        service.set_websocket_manager(mock_ws_manager)
        assert service._ws_manager is mock_ws_manager

    def test_evict_expired_cache(self):
        """evict_expired_cache delegates to TTLCache"""
        service = AlpacaService()

        # Create cache with 0 TTL
        service._price_cache = TTLCache(ttl_seconds=0)

        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25
        )
        service._price_cache.set("SPY260117C00688000", update)

        time.sleep(0.01)

        service.evict_expired_cache()
        assert service._price_cache.size == 0

    def test_add_and_remove_price_callback(self):
        """add_price_callback and remove_price_callback work correctly"""
        service = AlpacaService()

        callback = Mock()

        service.add_price_callback(callback)
        assert callback in service._price_callbacks

        service.remove_price_callback(callback)
        assert callback not in service._price_callbacks

    def test_remove_nonexistent_callback_no_error(self):
        """Removing non-existent callback doesn't raise error"""
        service = AlpacaService()
        callback = Mock()

        # Should not raise
        service.remove_price_callback(callback)

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

    @pytest.mark.asyncio
    async def test_shutdown_clears_trading_client(self):
        """Shutdown clears trading client reference"""
        service = AlpacaService()
        service._trading_client = Mock()

        await service.shutdown()

        assert service._trading_client is None

    @pytest.mark.asyncio
    async def test_stop_price_streaming_cancels_task(self):
        """stop_price_streaming cancels streaming task"""
        service = AlpacaService()
        service._is_streaming = True
        service._subscribed_symbols = {"SYM1", "SYM2"}

        # Create a real task that we can cancel
        async def dummy_coro():
            await asyncio.sleep(100)

        task = asyncio.create_task(dummy_coro())
        service._stream_task = task

        await service.stop_price_streaming()

        assert service._is_streaming is False
        assert len(service._subscribed_symbols) == 0
        assert task.cancelled()


class TestAlpacaServiceGetTradingClient:
    """Tests for _get_trading_client method"""

    def test_raises_without_credentials(self):
        """_get_trading_client raises if not configured"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', ''), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', ''):
            service = AlpacaService()

            with pytest.raises(RuntimeError, match="credentials not configured"):
                service._get_trading_client()

    def test_creates_client_with_credentials(self):
        """_get_trading_client creates TradingClient when configured"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', 'test_key'), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', 'test_secret'), \
             patch('modules.alpaca_service.TradingClient') as mock_client:

            service = AlpacaService()
            client = service._get_trading_client()

            mock_client.assert_called_once_with(
                api_key='test_key',
                secret_key='test_secret',
                paper=True  # Default from config
            )

    def test_reuses_existing_client(self):
        """_get_trading_client reuses existing client"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', 'test_key'), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', 'test_secret'), \
             patch('modules.alpaca_service.TradingClient') as mock_client:

            mock_instance = Mock()
            mock_client.return_value = mock_instance

            service = AlpacaService()
            client1 = service._get_trading_client()
            client2 = service._get_trading_client()

            assert client1 is client2
            mock_client.assert_called_once()  # Only created once


class TestAlpacaServiceGetOptionStream:
    """Tests for _get_option_stream method"""

    def test_raises_without_credentials(self):
        """_get_option_stream raises if not configured"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', ''), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', ''):
            service = AlpacaService()

            with pytest.raises(RuntimeError, match="credentials not configured"):
                service._get_option_stream()

    def test_creates_stream_with_credentials(self):
        """_get_option_stream creates OptionDataStream when configured"""
        with patch('modules.alpaca_service.ALPACA_API_KEY', 'test_key'), \
             patch('modules.alpaca_service.ALPACA_SECRET_KEY', 'test_secret'), \
             patch('modules.alpaca_service.OptionDataStream') as mock_stream:

            service = AlpacaService()
            stream = service._get_option_stream()

            mock_stream.assert_called_once_with(
                api_key='test_key',
                secret_key='test_secret',
            )


class TestAlpacaServiceHelpers:
    """Tests for init_alpaca_service and get_alpaca_service helpers"""

    @pytest.mark.asyncio
    async def test_init_alpaca_service(self):
        """init_alpaca_service stores service in app.state"""
        from modules.alpaca_service import init_alpaca_service

        mock_app = Mock()
        mock_app.state = Mock()

        service = await init_alpaca_service(mock_app)

        assert isinstance(service, AlpacaService)
        assert mock_app.state.alpaca_service is service

    def test_get_alpaca_service_returns_service(self):
        """get_alpaca_service returns service from app.state"""
        from modules.alpaca_service import get_alpaca_service

        mock_app = Mock()
        mock_service = AlpacaService()
        mock_app.state.alpaca_service = mock_service

        result = get_alpaca_service(mock_app)
        assert result is mock_service

    def test_get_alpaca_service_raises_if_not_initialized(self):
        """get_alpaca_service raises if service not initialized"""
        from modules.alpaca_service import get_alpaca_service

        mock_app = Mock()
        mock_app.state = Mock(spec=[])  # No alpaca_service attribute

        with pytest.raises(RuntimeError, match="not initialized"):
            get_alpaca_service(mock_app)


class TestGroupByTicker:
    """Tests for _group_by_ticker method"""

    def create_mock_position(self, symbol: str, qty: int, avg_entry_price: float = 1.0,
                             current_price: float = 1.0) -> Mock:
        """Helper to create a mock Alpaca position"""
        pos = Mock()
        pos.symbol = symbol
        pos.qty = qty
        pos.avg_entry_price = avg_entry_price
        pos.current_price = current_price
        pos.asset_class = 'us_option'
        return pos

    def test_group_by_ticker_single_leg(self):
        """Single option leg creates ticker position"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117C00695000", 10)
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].ticker == "SPY"
        assert len(result[0].legs) == 1
        assert result[0].strategy == "Options"

    def test_group_by_ticker_two_legs_vertical_spread(self):
        """Two-leg spread creates ticker position with Options strategy"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117C00695000", -10),  # Short
            self.create_mock_position("SPY260117C00700000", 10),   # Long
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].ticker == "SPY"
        assert len(result[0].legs) == 2
        assert result[0].strategy == "Options"

    def test_group_by_ticker_four_legs(self):
        """Four-leg position creates ticker position with Options strategy"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117P00680000", 10),   # Long Put
            self.create_mock_position("SPY260117P00685000", -10),  # Short Put
            self.create_mock_position("SPY260117C00695000", -10),  # Short Call
            self.create_mock_position("SPY260117C00700000", 10),   # Long Call
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].ticker == "SPY"
        assert len(result[0].legs) == 4
        assert result[0].strategy == "Options"

    def test_group_by_ticker_three_legs_options(self):
        """Three-leg position creates ticker position with Options strategy"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117P00680000", 10),   # Long Put
            self.create_mock_position("SPY260117P00685000", -10),  # Short Put
            self.create_mock_position("SPY260117C00695000", -10),  # Short Call
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].ticker == "SPY"
        assert len(result[0].legs) == 3
        assert result[0].strategy == "Options"

    def test_group_by_ticker_multiple_tickers(self):
        """Multiple tickers create separate positions"""
        service = AlpacaService()

        positions = [
            # SPY positions
            self.create_mock_position("SPY260117C00695000", -10),
            self.create_mock_position("SPY260117C00700000", 10),
            # AAPL positions
            self.create_mock_position("AAPL260117C00200000", 5),
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 2
        tickers = {r.ticker for r in result}
        assert "SPY" in tickers
        assert "AAPL" in tickers

    def test_group_by_ticker_invalid_symbol_skipped(self):
        """Invalid symbols are skipped without crashing"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("INVALID_SYMBOL", 10),
            self.create_mock_position("SPY260117C00695000", 10),
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].ticker == "SPY"

    def test_group_by_ticker_empty_list(self):
        """Empty position list returns empty result"""
        service = AlpacaService()

        result = service._group_by_ticker([])

        assert len(result) == 0

    def test_group_by_ticker_strangle(self):
        """Strangle (2 legs, different types, different strikes) detected"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117C00700000", -10),  # Short Call
            self.create_mock_position("SPY260117P00680000", -10),  # Short Put
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].strategy == "Options"

    def test_group_by_ticker_straddle(self):
        """Straddle (2 legs, different types, same strike) detected"""
        service = AlpacaService()

        positions = [
            self.create_mock_position("SPY260117C00690000", -10),  # Short Call at 690
            self.create_mock_position("SPY260117P00690000", -10),  # Short Put at 690
        ]

        result = service._group_by_ticker(positions)

        assert len(result) == 1
        assert result[0].strategy == "Options"

    def test_group_by_ticker_different_expiries(self):
        """Different expiry dates create separate positions"""
        service = AlpacaService()

        positions = [
            # Jan 17 expiry
            self.create_mock_position("SPY260117C00695000", 10),
            # Feb 20 expiry
            self.create_mock_position("SPY260220C00695000", 10),
        ]

        result = service._group_by_ticker(positions)

        # Should create 2 separate positions (grouped by ticker + expiry)
        assert len(result) == 2
