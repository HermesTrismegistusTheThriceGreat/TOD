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
import logging
from datetime import datetime, timedelta
from typing import Dict, Callable, Awaitable, Optional, Any
from dataclasses import dataclass, field
from collections import deque, OrderedDict


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
        # Use OrderedDict for LRU eviction - oldest entries are at the front
        self._pending: OrderedDict[str, ThrottledMessage] = OrderedDict()
        self._flush_tasks: Dict[str, asyncio.Task] = {}
        self._logger = logging.getLogger(__name__)
        self._evicted_count = 0

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
            # Enforce max_queue_size with LRU eviction before adding new entry
            self._enforce_queue_limit(key)

            # Store for later (latest-value semantics)
            # If key exists, move to end (most recently used)
            if key in self._pending:
                self._pending.move_to_end(key)
            self._pending[key] = ThrottledMessage(data=data)

            # Schedule flush if not already scheduled
            if key not in self._flush_tasks or self._flush_tasks[key].done():
                self._flush_tasks[key] = asyncio.create_task(
                    self._flush_pending(key, send_callback)
                )

            return False

    def _enforce_queue_limit(self, key: str) -> None:
        """
        Enforce max_queue_size by evicting oldest entries (LRU eviction).

        If the key already exists in pending, it doesn't count as a new entry.
        """
        if key in self._pending:
            # Key already exists, no need to evict
            return

        # Evict oldest entries until we have room
        while len(self._pending) >= self._max_queue_size:
            # Pop the oldest entry (first item in OrderedDict)
            evicted_key, evicted_msg = self._pending.popitem(last=False)
            self._evicted_count += 1
            # Cancel the flush task for evicted key if it exists
            if evicted_key in self._flush_tasks:
                self._flush_tasks[evicted_key].cancel()
                del self._flush_tasks[evicted_key]
            self._logger.debug(f"Evicted throttled message for {evicted_key} (LRU eviction)")

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
            try:
                await send_callback(message.data)
            except Exception as e:
                # Log error but don't crash - message is already removed from pending
                self._logger.error(f"Error sending throttled message for {key}: {e}")
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

    @property
    def evicted_count(self) -> int:
        """Total number of messages evicted due to queue overflow"""
        return self._evicted_count

    @property
    def max_queue_size(self) -> int:
        """Maximum pending messages before LRU eviction"""
        return self._max_queue_size


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
