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
from functools import wraps


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking calls"""
    pass


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

    def record_success(self) -> None:
        """Record a successful call"""
        self._failure_count = 0
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        self._success_count = 0

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit to closed state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0

    async def __aenter__(self) -> "CircuitBreaker":
        """Context manager entry - check if circuit allows call"""
        if self.is_open:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is open. "
                f"Recovery in {self._time_until_recovery()} seconds."
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
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


def with_circuit_breaker(breaker: CircuitBreaker) -> Callable:
    """
    Decorator for functions protected by circuit breaker.

    Usage:
        @with_circuit_breaker(my_breaker)
        async def call_external_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with breaker:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
