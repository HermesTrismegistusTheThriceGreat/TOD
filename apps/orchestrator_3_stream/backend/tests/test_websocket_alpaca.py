#!/usr/bin/env python3
"""
WebSocket integration tests for Alpaca price streaming.

Tests:
- WebSocket broadcast methods
- Rate limiting behavior
- Backpressure handling
- Message format validation

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_websocket_alpaca.py -v
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import WebSocket

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.websocket_manager import WebSocketManager
from modules.rate_limiter import RateLimiter, BackpressureQueue
from modules.alpaca_models import OptionPriceUpdate


# ═══════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ═══════════════════════════════════════════════════════════

class TestRateLimiter:
    """Tests for rate limiting"""

    def test_first_message_sends_immediately(self):
        """First message for a key should send immediately"""
        limiter = RateLimiter(throttle_ms=1000)
        assert limiter.can_send("key1") is True

    @pytest.mark.asyncio
    async def test_throttle_sends_first_message(self):
        """First throttled message should send immediately"""
        limiter = RateLimiter(throttle_ms=1000)
        sent_data = []

        async def callback(data):
            sent_data.append(data)

        result = await limiter.throttle("key1", {"value": 1}, callback)

        assert result is True
        assert len(sent_data) == 1
        assert sent_data[0]["value"] == 1

    @pytest.mark.asyncio
    async def test_throttle_delays_second_message(self):
        """Second message within window should be delayed"""
        limiter = RateLimiter(throttle_ms=100)
        sent_data = []

        async def callback(data):
            sent_data.append(data)

        # First message
        await limiter.throttle("key1", {"value": 1}, callback)

        # Second message (should be throttled)
        result = await limiter.throttle("key1", {"value": 2}, callback)

        assert result is False
        assert len(sent_data) == 1  # Only first message sent

    @pytest.mark.asyncio
    async def test_throttle_sends_after_interval(self):
        """Pending message should send after throttle interval"""
        limiter = RateLimiter(throttle_ms=50)  # 50ms throttle
        sent_data = []

        async def callback(data):
            sent_data.append(data)

        # Send two messages rapidly
        await limiter.throttle("key1", {"value": 1}, callback)
        await limiter.throttle("key1", {"value": 2}, callback)

        # Wait for throttle interval
        await asyncio.sleep(0.1)

        assert len(sent_data) == 2
        assert sent_data[1]["value"] == 2

    @pytest.mark.asyncio
    async def test_latest_value_semantics(self):
        """Only latest value should be sent after throttle"""
        limiter = RateLimiter(throttle_ms=100)
        sent_data = []

        async def callback(data):
            sent_data.append(data)

        # Send multiple messages rapidly
        await limiter.throttle("key1", {"value": 1}, callback)
        await limiter.throttle("key1", {"value": 2}, callback)
        await limiter.throttle("key1", {"value": 3}, callback)

        # Wait for throttle interval
        await asyncio.sleep(0.15)

        assert len(sent_data) == 2
        assert sent_data[0]["value"] == 1  # First (immediate)
        assert sent_data[1]["value"] == 3  # Last (after throttle)

    @pytest.mark.asyncio
    async def test_different_keys_independent(self):
        """Different keys should be rate limited independently"""
        limiter = RateLimiter(throttle_ms=1000)
        sent_data = []

        async def callback(data):
            sent_data.append(data)

        await limiter.throttle("key1", {"key": "1"}, callback)
        await limiter.throttle("key2", {"key": "2"}, callback)
        await limiter.throttle("key3", {"key": "3"}, callback)

        assert len(sent_data) == 3

    def test_clear_single_key(self):
        """Clear should remove pending for single key"""
        limiter = RateLimiter(throttle_ms=1000)
        limiter._pending["key1"] = MagicMock()
        limiter._pending["key2"] = MagicMock()

        limiter.clear("key1")

        assert "key1" not in limiter._pending
        assert "key2" in limiter._pending

    def test_clear_all(self):
        """Clear without key should remove all pending"""
        limiter = RateLimiter(throttle_ms=1000)
        limiter._pending["key1"] = MagicMock()
        limiter._pending["key2"] = MagicMock()

        limiter.clear()

        assert len(limiter._pending) == 0


# ═══════════════════════════════════════════════════════════
# BACKPRESSURE QUEUE TESTS
# ═══════════════════════════════════════════════════════════

class TestBackpressureQueue:
    """Tests for backpressure handling"""

    def test_push_to_empty_queue(self):
        """Push to empty queue succeeds"""
        queue = BackpressureQueue(max_size=10)

        result = queue.push({"data": 1})

        assert result is True
        assert queue.size == 1

    def test_push_drops_oldest_when_full(self):
        """Push when full should drop oldest"""
        queue = BackpressureQueue(max_size=3)

        queue.push({"data": 1})
        queue.push({"data": 2})
        queue.push({"data": 3})

        # Queue is now full
        result = queue.push({"data": 4})

        assert result is False
        assert queue.size == 3
        assert queue.dropped_count == 1

        # Oldest should be dropped, newest kept
        assert queue.pop()["data"] == 2
        assert queue.pop()["data"] == 3
        assert queue.pop()["data"] == 4

    def test_pop_from_empty_queue(self):
        """Pop from empty queue returns None"""
        queue = BackpressureQueue()

        assert queue.pop() is None

    def test_is_full(self):
        """is_full property works correctly"""
        queue = BackpressureQueue(max_size=2)

        assert queue.is_full is False

        queue.push(1)
        queue.push(2)

        assert queue.is_full is True

    def test_clear(self):
        """Clear empties the queue"""
        queue = BackpressureQueue()

        queue.push(1)
        queue.push(2)
        queue.clear()

        assert queue.size == 0


# ═══════════════════════════════════════════════════════════
# WEBSOCKET MANAGER ALPACA TESTS
# ═══════════════════════════════════════════════════════════

class TestWebSocketManagerAlpaca:
    """Tests for Alpaca-specific WebSocket broadcasts"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocketManager for testing"""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = MagicMock(spec=WebSocket)
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_broadcast_option_price_update(self, ws_manager, mock_websocket):
        """broadcast_option_price_update sends correct message format"""
        # Connect mock WebSocket
        ws_manager.active_connections.append(mock_websocket)

        update_data = {
            "symbol": "SPY260117C00688000",
            "bid_price": 3.20,
            "ask_price": 3.30,
            "mid_price": 3.25,
            "timestamp": datetime.now().isoformat()
        }

        await ws_manager.broadcast_option_price_update(update_data)

        # Verify message format
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "option_price_update"
        assert call_args["update"]["symbol"] == "SPY260117C00688000"
        assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def test_broadcast_option_price_batch(self, ws_manager, mock_websocket):
        """broadcast_option_price_batch sends correct message format"""
        ws_manager.active_connections.append(mock_websocket)

        updates = [
            {"symbol": "SPY260117C00688000", "mid_price": 3.25},
            {"symbol": "SPY260117P00683000", "mid_price": 1.50},
        ]

        await ws_manager.broadcast_option_price_batch(updates)

        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "option_price_batch"
        assert call_args["count"] == 2
        assert len(call_args["updates"]) == 2

    @pytest.mark.asyncio
    async def test_broadcast_position_update(self, ws_manager, mock_websocket):
        """broadcast_position_update sends correct message format"""
        ws_manager.active_connections.append(mock_websocket)

        position_data = {
            "id": "test-123",
            "ticker": "SPY",
            "legs": []
        }

        await ws_manager.broadcast_position_update(position_data)

        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "position_update"
        assert call_args["position"]["id"] == "test-123"

    @pytest.mark.asyncio
    async def test_broadcast_alpaca_status(self, ws_manager, mock_websocket):
        """broadcast_alpaca_status sends correct message format"""
        ws_manager.active_connections.append(mock_websocket)

        await ws_manager.broadcast_alpaca_status(
            "connected",
            {"circuit_state": "closed"}
        )

        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "alpaca_status"
        assert call_args["status"] == "connected"
        assert call_args["details"]["circuit_state"] == "closed"

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_clients(self, ws_manager):
        """Broadcast handles disconnected clients gracefully"""
        # Create mock that raises on send
        bad_ws = MagicMock(spec=WebSocket)
        bad_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        good_ws = MagicMock(spec=WebSocket)
        good_ws.send_json = AsyncMock()

        ws_manager.active_connections = [bad_ws, good_ws]

        await ws_manager.broadcast_option_price_update({"symbol": "TEST"})

        # Bad connection should be removed
        assert bad_ws not in ws_manager.active_connections
        assert good_ws in ws_manager.active_connections


# ═══════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

class TestAlpacaWebSocketIntegration:
    """Integration tests for Alpaca WebSocket flow"""

    @pytest.mark.asyncio
    async def test_price_update_flow_with_rate_limiting(self):
        """Test full price update flow with rate limiting"""
        from modules.alpaca_service import AlpacaService

        # Create service with mock WebSocket manager
        service = AlpacaService()
        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_option_price_update = AsyncMock()
        service.set_websocket_manager(mock_ws_manager)

        # Simulate rapid price updates
        class MockQuote:
            def __init__(self, symbol, bid, ask):
                self.symbol = symbol
                self.bid_price = bid
                self.ask_price = ask

        # Send multiple updates rapidly
        for i in range(5):
            quote = MockQuote("SPY260117C00688000", 3.20 + i * 0.01, 3.30 + i * 0.01)
            await service._handle_quote_update(quote)

        # Wait for any pending throttled messages
        await asyncio.sleep(0.3)

        # Due to rate limiting, not all messages should be sent
        call_count = mock_ws_manager.broadcast_option_price_update.call_count
        assert call_count < 5  # Some should be throttled
        assert call_count >= 1  # At least first should send

    @pytest.mark.asyncio
    async def test_price_cache_updated_on_update(self):
        """Price cache should be updated on every quote"""
        from modules.alpaca_service import AlpacaService

        service = AlpacaService()
        service.set_websocket_manager(MagicMock())

        class MockQuote:
            symbol = "SPY260117C00688000"
            bid_price = 3.20
            ask_price = 3.30

        await service._handle_quote_update(MockQuote())

        cached = service.get_cached_price("SPY260117C00688000")
        assert cached is not None
        assert cached.mid_price == 3.25
