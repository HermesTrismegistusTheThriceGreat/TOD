# Review Report: Alpaca Integration Tests & Pytest Config

**Date**: 2025-01-10
**Reviewer**: Build Agent
**Scope**: Part 3 - REST Endpoints Integration Tests

---

## Summary

| Item | Status | Notes |
|------|--------|-------|
| `test_alpaca_endpoints.py` | **MISSING** | File does not exist |
| `pytest.ini` | **MISSING** | File does not exist (config in pyproject.toml) |
| pytest dev dependencies | **PARTIAL** | httpx missing from dev-dependencies |

---

## Detailed Findings

### 1. Dev Dependencies in `pyproject.toml`

**Current State:**
```toml
[tool.uv]
dev-dependencies = [
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
]
```

**Issues:**
- **pytest**: Present
- **pytest-asyncio**: Present
- **httpx**: **MISSING** from dev-dependencies

**Note:** httpx IS in the main dependencies (line 21 shows `"httpx>=0.28.1"` but this appears to be added by another dependency). It should be explicitly added to dev-dependencies for testing.

### 2. Pytest Configuration in `pyproject.toml`

**Current State:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

**Findings:**
- `asyncio_mode = "auto"` is correctly configured
- `asyncio_default_fixture_loop_scope = "function"` is properly set
- Custom marker for slow tests is defined
- **No separate pytest.ini file exists** (configuration is in pyproject.toml, which is acceptable)

### 3. Missing Test File: `test_alpaca_endpoints.py`

The file `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/tests/test_alpaca_endpoints.py` **does not exist**.

**Existing Alpaca-related tests:**
- `test_alpaca_models.py` - Tests for Pydantic models (305 lines)
- `test_alpaca_service.py` - Tests for AlpacaService class (481 lines)

**Alpaca Endpoints that need tests (from main.py):**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/positions` | GET | Get all iron condor positions |
| `/api/positions/{position_id}` | GET | Get specific position by ID |
| `/api/positions/subscribe-prices` | POST | Subscribe to price streaming |
| `/api/positions/circuit-status` | GET | Get circuit breaker status |

---

## Checklist Review

| Requirement | Status | Notes |
|-------------|--------|-------|
| pytest, pytest-asyncio, httpx in dev deps | **PARTIAL** | httpx needs to be added to dev-dependencies |
| pytest.ini has asyncio_mode = auto | **PASS** | Configured in pyproject.toml |
| Fixtures properly mock AlpacaService | **FAIL** | test_alpaca_endpoints.py missing |
| Test classes cover all endpoints | **FAIL** | test_alpaca_endpoints.py missing |
| Tests check success cases | **FAIL** | test_alpaca_endpoints.py missing |
| Tests check error cases | **FAIL** | test_alpaca_endpoints.py missing |
| Tests verify response model fields | **FAIL** | test_alpaca_endpoints.py missing |
| Tests use proper assertions | **FAIL** | test_alpaca_endpoints.py missing |

---

## Recommendations

### Immediate Actions Required

1. **Create `test_alpaca_endpoints.py`** with:
   - Fixtures to mock `AlpacaService`
   - Test class for each endpoint
   - Success case tests
   - Error case tests (not configured, position not found, etc.)
   - Response model field verification

2. **Update `pyproject.toml`** dev-dependencies:
   ```toml
   [tool.uv]
   dev-dependencies = [
       "pytest>=9.0.2",
       "pytest-asyncio>=1.3.0",
       "httpx>=0.28.1",
   ]
   ```

### Test Structure Template

The missing `test_alpaca_endpoints.py` should follow the pattern from `test_autocomplete_endpoints.py`:

```python
"""
Integration tests for Alpaca API Endpoints

Tests the /api/positions endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

class TestGetPositions:
    """Tests for GET /api/positions"""

    @pytest.mark.asyncio
    async def test_get_positions_success(self):
        """Should return positions when Alpaca configured"""
        pass

    @pytest.mark.asyncio
    async def test_get_positions_not_configured(self):
        """Should return error when Alpaca not configured"""
        pass

class TestGetPositionById:
    """Tests for GET /api/positions/{position_id}"""

    @pytest.mark.asyncio
    async def test_get_position_success(self):
        """Should return position when found"""
        pass

    @pytest.mark.asyncio
    async def test_get_position_not_found(self):
        """Should return error when position not found"""
        pass

class TestSubscribePrices:
    """Tests for POST /api/positions/subscribe-prices"""
    pass

class TestCircuitStatus:
    """Tests for GET /api/positions/circuit-status"""
    pass
```

---

## Existing Test Coverage

The existing tests provide good coverage for:

- **Models** (`test_alpaca_models.py`):
  - OCC symbol parsing
  - OptionLeg P/L calculations
  - IronCondorPosition validation
  - Model serialization

- **Service** (`test_alpaca_service.py`):
  - Circuit breaker pattern
  - TTL cache functionality
  - AlpacaService configuration
  - Trading client creation
  - Option stream creation
  - Helper functions

**Gap**: No integration tests for the HTTP endpoints that expose this functionality.

---

## Conclusion

The Alpaca integration is missing endpoint-level integration tests. The existing model and service tests are comprehensive, but the REST API layer remains untested. Priority should be given to creating `test_alpaca_endpoints.py` to ensure the endpoints correctly integrate with the mocked service layer.
