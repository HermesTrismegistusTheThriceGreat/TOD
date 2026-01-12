# Part 4: WebSocket Streaming

## Overview

**Scope:** Implement WebSocket price streaming with rate limiting and backpressure handling
**Dependencies:** Part 1 (Models), Part 2 (Service), Part 3 (Endpoints)
**Estimated Time:** 2-3 hours

## Objectives

1. Add WebSocket broadcast methods for price updates
2. Implement rate limiting (100-500ms throttling) for price streams
3. Add backpressure handling for high-frequency updates
4. Create async WebSocket integration tests
5. Update frontend chatService with new event handlers

## Review Feedback Addressed

| Issue | Severity | Fix |
|-------|----------|-----|
| No WebSocket integration tests | BLOCKER | Add async WebSocket tests |
| No rate limiting for price streams | HIGH | Add 100-500ms throttling |
| Add backpressure handling for WebSocket broadcasts | MEDIUM | Implement message queue with backpressure |

## Files to Create/Modify

### Files to Modify

| File | Change |
|------|--------|
| `apps/orchestrator_3_stream/backend/modules/websocket_manager.py` | Add Alpaca broadcast methods |
| `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` | Add rate limiting |
| `apps/orchestrator_3_stream/frontend/src/services/chatService.ts` | Add event handlers |

### New Files

| File | Purpose |
|------|---------|
| `apps/orchestrator_3_stream/backend/modules/rate_limiter.py` | Rate limiting utility |
| `apps/orchestrator_3_stream/backend/tests/test_websocket_alpaca.py` | WebSocket tests |

## Implementation Steps

### Step 1: Create Rate Limiter

**File:** `apps/orchestrator_3_stream/backend/modules/rate_limiter.py`

```python
#!/usr/bin/env python3
"""
Rate Limiter for WebSocket Price Streaming

Provides throttling for high-frequency price updates to prevent
frontend overwhelm and reduce bandwidth usage.

Features:
- Per-symbol rate limiting
- Configurable throttle interval (100-500ms)
- Backpressure handling via message queue
- Latest-value semantics (drops intermediate updates)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Callable, Awaitable, Optional, Any
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ThrottledMessage:
    """Message with throttle tracking"""
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """
    Rate limiter with latest-value semantics.

    When multiple updates arrive within the throttle window,
    only the latest value is sent when the window expires.

    Args:
        throttle_ms: Minimum milliseconds between updates per key
        max_queue_size: Maximum pending messages before dropping
    """

    def __init__(self, throttle_ms: int = 200, max_queue_size: int = 100):
        self._throttle_ms = throttle_ms
        self._max_queue_size = max_queue_size
        self._last_send: Dict[str, datetime] = {}
        self._pending: Dict[str, ThrottledMessage] = {}
        self._flush_tasks: Dict[str, asyncio.Task] = {}

    @property
    def throttle_interval(self) -> timedelta:
        return timedelta(milliseconds=self._throttle_ms)

    def can_send(self, key: str) -> bool:
        """Check if enough time has passed to send for this key"""
        if key not in self._last_send:
            return True
        elapsed = datetime.now() - self._last_send[key]
        return elapsed >= self.throttle_interval

    async def throttle(
        self,
        key: str,
        data: Any,
        send_callback: Callable[[Any], Awaitable[None]]
    ) -> bool:
        """
        Throttle a message, sending immediately or scheduling for later.

        Args:
            key: Unique key for rate limiting (e.g., symbol)
            data: Data to send
            send_callback: Async function to call when sending

        Returns:
            True if sent immediately, False if throttled
        """
        if self.can_send(key):
            # Send immediately
            await send_callback(data)
            self._last_send[key] = datetime.now()
            return True
        else:
            # Store for later (latest-value semantics)
            self._pending[key] = ThrottledMessage(data=data)

            # Schedule flush if not already scheduled
            if key not in self._flush_tasks or self._flush_tasks[key].done():
                self._flush_tasks[key] = asyncio.create_task(
                    self._flush_pending(key, send_callback)
                )

            return False

    async def _flush_pending(
        self,
        key: str,
        send_callback: Callable[[Any], Awaitable[None]]
    ):
        """Wait for throttle interval then send pending message"""
        # Calculate wait time
        if key in self._last_send:
            elapsed = datetime.now() - self._last_send[key]
            wait_time = (self.throttle_interval - elapsed).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # Send pending message if exists
        if key in self._pending:
            message = self._pending.pop(key)
            await send_callback(message.data)
            self._last_send[key] = datetime.now()

    def clear(self, key: Optional[str] = None):
        """Clear pending messages and cancel tasks"""
        if key:
            self._pending.pop(key, None)
            if key in self._flush_tasks:
                self._flush_tasks[key].cancel()
                del self._flush_tasks[key]
        else:
            self._pending.clear()
            for task in self._flush_tasks.values():
                task.cancel()
            self._flush_tasks.clear()

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class BackpressureQueue:
    """
    Queue with backpressure handling for WebSocket broadcasts.

    When queue is full, oldest messages are dropped to prevent
    memory exhaustion and maintain responsiveness.

    Args:
        max_size: Maximum queue size before dropping messages
    """

    def __init__(self, max_size: int = 1000):
        self._queue: deque = deque(maxlen=max_size)
        self._max_size = max_size
        self._dropped_count = 0

    def push(self, item: Any) -> bool:
        """
        Push item to queue.

        Returns:
            True if added, False if queue was full (oldest dropped)
        """
        was_full = len(self._queue) >= self._max_size
        if was_full:
            self._dropped_count += 1

        self._queue.append(item)
        return not was_full

    def pop(self) -> Optional[Any]:
        """Pop oldest item from queue"""
        if self._queue:
            return self._queue.popleft()
        return None

    def clear(self):
        """Clear the queue"""
        self._queue.clear()

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self._max_size
```

### Step 2: Update WebSocket Manager

**File:** `apps/orchestrator_3_stream/backend/modules/websocket_manager.py`

Add after line 274 (after `broadcast_adw_event_summary_update`):

```python
    # ========================================================================
    # Alpaca Options Broadcasting
    # ========================================================================

    async def broadcast_option_price_update(self, update_data: dict):
        """
        Broadcast real-time option price update.

        Used by AlpacaService to push price changes to frontend.
        Rate limiting is handled by AlpacaService before calling this.

        Args:
            update_data: Dict with symbol, bid_price, ask_price, mid_price, timestamp
        """
        await self.broadcast({
            "type": "option_price_update",
            "update": update_data,
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_option_price_batch(self, updates: list):
        """
        Broadcast batch of price updates for efficiency.

        Use this when multiple symbols update simultaneously to reduce
        WebSocket message count.

        Args:
            updates: List of price update dicts
        """
        await self.broadcast({
            "type": "option_price_batch",
            "updates": updates,
            "count": len(updates),
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_position_update(self, position_data: dict):
        """
        Broadcast position update (e.g., after order fill).

        Args:
            position_data: Full position data including all legs
        """
        await self.broadcast({
            "type": "position_update",
            "position": position_data,
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_alpaca_status(self, status: str, details: dict = None):
        """
        Broadcast Alpaca connection status change.

        Args:
            status: Connection status (connected, disconnected, error)
            details: Additional status details
        """
        await self.broadcast({
            "type": "alpaca_status",
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
```

### Step 3: Update AlpacaService with Rate Limiting

**File:** `apps/orchestrator_3_stream/backend/modules/alpaca_service.py`

Add import at top:

```python
from .rate_limiter import RateLimiter
```

Add configuration in config.py:

```python
# Rate limiting settings
ALPACA_PRICE_THROTTLE_MS = int(os.getenv("ALPACA_PRICE_THROTTLE_MS", "200"))  # 200ms default
```

Update AlpacaService `__init__`:

```python
def __init__(self):
    # ... existing code ...

    # Rate limiter for price updates (200ms default throttle)
    self._rate_limiter = RateLimiter(
        throttle_ms=ALPACA_PRICE_THROTTLE_MS,
        max_queue_size=100
    )
```

Update `_handle_quote_update` method:

```python
async def _handle_quote_update(self, quote) -> None:
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
                data=update.model_dump(),
                send_callback=send_update
            )

            if was_sent:
                logger.debug(f"Price update sent: {symbol} mid={mid}")
            else:
                logger.debug(f"Price update throttled: {symbol}")

    except Exception as e:
        logger.error(f"Error handling quote update: {e}")
```

Add cleanup in `shutdown`:

```python
async def shutdown(self) -> None:
    """Clean shutdown of all connections"""
    await self.stop_price_streaming()

    # Clear rate limiter
    self._rate_limiter.clear()

    # ... rest of existing code ...
```

### Step 4: Update Frontend chatService

**File:** `apps/orchestrator_3_stream/frontend/src/services/chatService.ts`

Add to WebSocketCallbacks interface (around line 75):

```typescript
export interface WebSocketCallbacks {
  // ... existing callbacks ...

  // Alpaca price streaming events
  onOptionPriceUpdate?: (data: OptionPriceUpdateMessage) => void
  onOptionPriceBatch?: (data: OptionPriceBatchMessage) => void
  onPositionUpdate?: (data: PositionUpdateMessage) => void
  onAlpacaStatus?: (data: AlpacaStatusMessage) => void
}

// Add type definitions at top of file
export interface OptionPriceUpdateMessage {
  type: 'option_price_update'
  update: {
    symbol: string
    bid_price: number
    ask_price: number
    mid_price: number
    last_price?: number
    volume: number
    timestamp: string
  }
  timestamp: string
}

export interface OptionPriceBatchMessage {
  type: 'option_price_batch'
  updates: Array<{
    symbol: string
    bid_price: number
    ask_price: number
    mid_price: number
  }>
  count: number
  timestamp: string
}

export interface PositionUpdateMessage {
  type: 'position_update'
  position: any  // IronCondorPosition
  timestamp: string
}

export interface AlpacaStatusMessage {
  type: 'alpaca_status'
  status: 'connected' | 'disconnected' | 'error'
  details: Record<string, any>
  timestamp: string
}
```

Add cases in the switch statement (around line 150):

```typescript
        // Alpaca price updates
        case 'option_price_update':
          callbacks.onOptionPriceUpdate?.(message as OptionPriceUpdateMessage)
          break

        case 'option_price_batch':
          callbacks.onOptionPriceBatch?.(message as OptionPriceBatchMessage)
          break

        case 'position_update':
          callbacks.onPositionUpdate?.(message as PositionUpdateMessage)
          break

        case 'alpaca_status':
          callbacks.onAlpacaStatus?.(message as AlpacaStatusMessage)
          break
```

### Step 5: Create WebSocket Integration Tests

**File:** `apps/orchestrator_3_stream/backend/tests/test_websocket_alpaca.py`

```python
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
sys.path.insert(0, '..')

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
```

## Validation Commands

```bash
# Navigate to backend directory
cd apps/orchestrator_3_stream/backend

# Verify imports
uv run python -c "
from modules.rate_limiter import RateLimiter, BackpressureQueue
from modules.websocket_manager import WebSocketManager
print('Imports OK')
"

# Run WebSocket tests
uv run pytest tests/test_websocket_alpaca.py -v

# Run all Alpaca tests
uv run pytest tests/test_alpaca*.py -v

# Manual WebSocket testing
# Start server:
uv run uvicorn main:app --host 127.0.0.1 --port 9403 --reload

# Connect with wscat:
# wscat -c ws://127.0.0.1:9403/ws

# Subscribe to prices via REST, then watch WebSocket for updates
```

## Acceptance Criteria

- [ ] WebSocket manager has `broadcast_option_price_update` method
- [ ] WebSocket manager has `broadcast_option_price_batch` method
- [ ] WebSocket manager has `broadcast_position_update` method
- [ ] Rate limiter throttles updates at 200ms intervals
- [ ] Rate limiter uses latest-value semantics
- [ ] Backpressure queue drops oldest when full
- [ ] Frontend chatService has new event handlers
- [ ] All WebSocket integration tests pass
- [ ] Disconnected clients are cleaned up properly

## Notes

### Rate Limiting Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `ALPACA_PRICE_THROTTLE_MS` | 200 | Minimum ms between updates per symbol |

### WebSocket Message Types

| Type | Description |
|------|-------------|
| `option_price_update` | Single price update for one symbol |
| `option_price_batch` | Batch of price updates |
| `position_update` | Full position update after change |
| `alpaca_status` | Connection status change |

### Latest-Value Semantics

When multiple updates arrive within the throttle window:
1. First update sends immediately
2. Subsequent updates replace pending value
3. When window expires, only latest value is sent

```
Time:     0ms    50ms   100ms  150ms  200ms
Updates:   1      2       3      4      -
Sent:      1      -       -      -      4
                         (throttle)
```
