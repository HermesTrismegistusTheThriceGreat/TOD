# Part 3: REST API Endpoints

## Overview

**Scope:** Create FastAPI REST endpoints for Alpaca position data
**Dependencies:** Part 1 (Models), Part 2 (Service)
**Estimated Time:** 1-2 hours

## Objectives

1. Add REST endpoints for position fetching
2. Add pytest to dev dependencies
3. Create integration tests with TestClient
4. Update FastAPI lifespan for AlpacaService initialization

## Review Feedback Addressed

| Issue | Severity | Fix |
|-------|----------|-----|
| No integration tests for REST endpoints | BLOCKER | Add pytest tests with TestClient |
| Missing pytest in dev dependencies | HIGH | Add pytest to pyproject.toml |

## Files to Create/Modify

### Files to Modify

| File | Change |
|------|--------|
| `apps/orchestrator_3_stream/backend/main.py` | Add REST endpoints and lifespan init |
| `apps/orchestrator_3_stream/backend/pyproject.toml` | Add pytest dev dependency |

### New Files

| File | Purpose |
|------|---------|
| `apps/orchestrator_3_stream/backend/tests/test_alpaca_endpoints.py` | Integration tests |

## Implementation Steps

### Step 1: Add pytest to Dependencies

**File:** `apps/orchestrator_3_stream/backend/pyproject.toml`

Add to dev dependencies:

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",  # For TestClient async support
]
```

Install:

```bash
cd apps/orchestrator_3_stream/backend
uv add --dev pytest pytest-asyncio httpx
```

### Step 2: Update main.py with Lifespan and Endpoints

**File:** `apps/orchestrator_3_stream/backend/main.py`

Add imports at top of file:

```python
from fastapi import Request
from modules.alpaca_service import init_alpaca_service, get_alpaca_service
from modules.alpaca_models import (
    GetPositionsResponse,
    GetPositionResponse,
    SubscribePricesRequest,
    SubscribePricesResponse,
)
from modules.websocket_manager import get_websocket_manager
```

Update the lifespan context manager to initialize AlpacaService:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.

    Startup:
    - Initialize database pool
    - Initialize AlpacaService
    - Connect WebSocket manager to AlpacaService

    Shutdown:
    - Shutdown AlpacaService
    - Close database pool
    """
    # ─── STARTUP ───────────────────────────────────────────────
    logger.info("Starting application...")

    # Initialize database pool
    await init_pool()
    logger.success("Database pool initialized")

    # Initialize Alpaca service
    alpaca_service = await init_alpaca_service(app)

    # Connect WebSocket manager to Alpaca service for price broadcasts
    ws_manager = get_websocket_manager()
    alpaca_service.set_websocket_manager(ws_manager)

    yield

    # ─── SHUTDOWN ──────────────────────────────────────────────
    logger.info("Shutting down application...")

    # Shutdown Alpaca service
    if hasattr(app.state, 'alpaca_service'):
        await app.state.alpaca_service.shutdown()

    # Close database pool
    await close_pool()
    logger.success("Application shutdown complete")
```

Add REST endpoints (after ADW endpoints, before WebSocket):

```python
# ============================================================================
# ALPACA TRADING ENDPOINTS
# ============================================================================

@app.get("/api/positions", response_model=GetPositionsResponse, tags=["Alpaca"])
async def get_positions(request: Request):
    """
    Get all iron condor positions from Alpaca.

    Returns grouped iron condor positions with all leg details.
    Positions are cached and circuit breaker protects against API failures.

    Returns:
        GetPositionsResponse with list of iron condor positions
    """
    try:
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            return GetPositionsResponse(
                status="error",
                message="Alpaca API not configured. Set ALPACA_API_KEY and ALPACA_SECRET_KEY."
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


@app.get("/api/positions/{position_id}", response_model=GetPositionResponse, tags=["Alpaca"])
async def get_position(request: Request, position_id: str):
    """
    Get a specific iron condor position by ID.

    Args:
        position_id: UUID of the position

    Returns:
        GetPositionResponse with position details or error
    """
    try:
        alpaca_service = get_alpaca_service(request.app)

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


@app.post("/api/positions/subscribe-prices", response_model=SubscribePricesResponse, tags=["Alpaca"])
async def subscribe_prices(request: Request, subscribe_request: SubscribePricesRequest):
    """
    Subscribe to real-time price updates for option symbols.

    Call this after loading positions to start receiving
    WebSocket price updates for the specified symbols.

    Args:
        subscribe_request: Request with list of OCC symbols

    Returns:
        SubscribePricesResponse with subscription status
    """
    try:
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            return SubscribePricesResponse(
                status="error",
                message="Alpaca API not configured"
            )

        await alpaca_service.start_price_streaming(subscribe_request.symbols)

        return SubscribePricesResponse(
            status="success",
            message=f"Subscribed to {len(subscribe_request.symbols)} symbols",
            symbols=subscribe_request.symbols
        )

    except Exception as e:
        logger.error(f"Failed to subscribe to prices: {e}")
        return SubscribePricesResponse(
            status="error",
            message=str(e)
        )


@app.get("/api/positions/circuit-status", tags=["Alpaca"])
async def get_circuit_status(request: Request):
    """
    Get current circuit breaker status for Alpaca API.

    Returns:
        Dict with circuit state and configuration
    """
    try:
        alpaca_service = get_alpaca_service(request.app)

        return {
            "status": "success",
            "circuit_state": alpaca_service.circuit_state,
            "is_configured": alpaca_service.is_configured,
        }

    except Exception as e:
        logger.error(f"Failed to get circuit status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
```

### Step 3: Create Integration Tests

**File:** `apps/orchestrator_3_stream/backend/tests/test_alpaca_endpoints.py`

```python
#!/usr/bin/env python3
"""
Integration tests for Alpaca REST endpoints.

These tests use FastAPI TestClient to test the actual endpoints.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date

import sys
sys.path.insert(0, '..')


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_alpaca_service():
    """Create a mock AlpacaService"""
    from modules.alpaca_models import IronCondorPosition, OptionLeg

    mock_service = MagicMock()
    mock_service.is_configured = True
    mock_service.circuit_state = "closed"

    # Create sample position data
    sample_position = IronCondorPosition(
        id="test-position-123",
        ticker="SPY",
        expiry_date=date(2026, 1, 17),
        legs=[
            OptionLeg(
                id="leg-1",
                symbol="SPY260117P00680000",
                direction="Long",
                strike=680.0,
                option_type="Put",
                quantity=10,
                entry_price=1.00,
                current_price=0.80,
                expiry_date=date(2026, 1, 17),
                underlying="SPY"
            ),
            OptionLeg(
                id="leg-2",
                symbol="SPY260117P00685000",
                direction="Short",
                strike=685.0,
                option_type="Put",
                quantity=10,
                entry_price=2.00,
                current_price=1.60,
                expiry_date=date(2026, 1, 17),
                underlying="SPY"
            ),
            OptionLeg(
                id="leg-3",
                symbol="SPY260117C00695000",
                direction="Short",
                strike=695.0,
                option_type="Call",
                quantity=10,
                entry_price=2.00,
                current_price=1.60,
                expiry_date=date(2026, 1, 17),
                underlying="SPY"
            ),
            OptionLeg(
                id="leg-4",
                symbol="SPY260117C00700000",
                direction="Long",
                strike=700.0,
                option_type="Call",
                quantity=10,
                entry_price=1.00,
                current_price=0.80,
                expiry_date=date(2026, 1, 17),
                underlying="SPY"
            ),
        ]
    )

    mock_service.get_all_positions = AsyncMock(return_value=[sample_position])
    mock_service.get_position_by_id = AsyncMock(return_value=sample_position)
    mock_service.start_price_streaming = AsyncMock()

    return mock_service


@pytest.fixture
def test_client(mock_alpaca_service):
    """Create TestClient with mocked AlpacaService"""
    # Import main app
    from main import app

    # Store the mock in app.state
    app.state.alpaca_service = mock_alpaca_service

    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_client_unconfigured():
    """Create TestClient with unconfigured AlpacaService"""
    from main import app

    mock_service = MagicMock()
    mock_service.is_configured = False

    app.state.alpaca_service = mock_service

    with TestClient(app) as client:
        yield client


# ═══════════════════════════════════════════════════════════
# GET /api/positions TESTS
# ═══════════════════════════════════════════════════════════

class TestGetPositions:
    """Tests for GET /api/positions endpoint"""

    def test_get_positions_success(self, test_client, mock_alpaca_service):
        """Successfully get positions"""
        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["total_count"] == 1
        assert len(data["positions"]) == 1

        position = data["positions"][0]
        assert position["ticker"] == "SPY"
        assert len(position["legs"]) == 4

    def test_get_positions_not_configured(self, test_client_unconfigured):
        """Returns error when Alpaca not configured"""
        response = test_client_unconfigured.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "not configured" in data["message"].lower()

    def test_get_positions_api_error(self, test_client, mock_alpaca_service):
        """Returns error on API failure"""
        mock_alpaca_service.get_all_positions = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "API connection failed" in data["message"]

    def test_get_positions_empty(self, test_client, mock_alpaca_service):
        """Returns empty list when no positions"""
        mock_alpaca_service.get_all_positions = AsyncMock(return_value=[])

        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["total_count"] == 0
        assert data["positions"] == []


# ═══════════════════════════════════════════════════════════
# GET /api/positions/{id} TESTS
# ═══════════════════════════════════════════════════════════

class TestGetPositionById:
    """Tests for GET /api/positions/{id} endpoint"""

    def test_get_position_success(self, test_client, mock_alpaca_service):
        """Successfully get position by ID"""
        response = test_client.get("/api/positions/test-position-123")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["position"]["id"] == "test-position-123"
        assert data["position"]["ticker"] == "SPY"

    def test_get_position_not_found(self, test_client, mock_alpaca_service):
        """Returns error when position not found"""
        mock_alpaca_service.get_position_by_id = AsyncMock(return_value=None)

        response = test_client.get("/api/positions/nonexistent-id")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    def test_get_position_not_configured(self, test_client_unconfigured):
        """Returns error when Alpaca not configured"""
        response = test_client_unconfigured.get("/api/positions/any-id")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "not configured" in data["message"].lower()


# ═══════════════════════════════════════════════════════════
# POST /api/positions/subscribe-prices TESTS
# ═══════════════════════════════════════════════════════════

class TestSubscribePrices:
    """Tests for POST /api/positions/subscribe-prices endpoint"""

    def test_subscribe_success(self, test_client, mock_alpaca_service):
        """Successfully subscribe to prices"""
        symbols = ["SPY260117C00688000", "SPY260117P00683000"]

        response = test_client.post(
            "/api/positions/subscribe-prices",
            json={"symbols": symbols}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert len(data["symbols"]) == 2

        # Verify service was called
        mock_alpaca_service.start_price_streaming.assert_called_once_with(symbols)

    def test_subscribe_empty_symbols(self, test_client, mock_alpaca_service):
        """Successfully handles empty symbols list"""
        response = test_client.post(
            "/api/positions/subscribe-prices",
            json={"symbols": []}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["symbols"] == []

    def test_subscribe_not_configured(self, test_client_unconfigured):
        """Returns error when Alpaca not configured"""
        response = test_client_unconfigured.post(
            "/api/positions/subscribe-prices",
            json={"symbols": ["SPY260117C00688000"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "not configured" in data["message"].lower()

    def test_subscribe_streaming_error(self, test_client, mock_alpaca_service):
        """Returns error on streaming failure"""
        mock_alpaca_service.start_price_streaming = AsyncMock(
            side_effect=Exception("Stream connection failed")
        )

        response = test_client.post(
            "/api/positions/subscribe-prices",
            json={"symbols": ["SPY260117C00688000"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "Stream connection failed" in data["message"]


# ═══════════════════════════════════════════════════════════
# GET /api/positions/circuit-status TESTS
# ═══════════════════════════════════════════════════════════

class TestCircuitStatus:
    """Tests for GET /api/positions/circuit-status endpoint"""

    def test_circuit_status_closed(self, test_client, mock_alpaca_service):
        """Returns closed circuit status"""
        response = test_client.get("/api/positions/circuit-status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["circuit_state"] == "closed"
        assert data["is_configured"] is True

    def test_circuit_status_open(self, test_client, mock_alpaca_service):
        """Returns open circuit status"""
        mock_alpaca_service.circuit_state = "open"

        response = test_client.get("/api/positions/circuit-status")

        assert response.status_code == 200
        data = response.json()

        assert data["circuit_state"] == "open"


# ═══════════════════════════════════════════════════════════
# RESPONSE MODEL VALIDATION TESTS
# ═══════════════════════════════════════════════════════════

class TestResponseModels:
    """Tests for response model validation"""

    def test_position_response_contains_computed_fields(self, test_client, mock_alpaca_service):
        """Response includes computed fields like pnl_dollars"""
        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        position = data["positions"][0]
        leg = position["legs"][0]

        # Computed fields should be present
        assert "pnl_dollars" in leg
        assert "pnl_percent" in leg

    def test_position_response_date_serialization(self, test_client, mock_alpaca_service):
        """Dates are serialized as ISO strings"""
        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        position = data["positions"][0]

        # Dates should be ISO strings
        assert isinstance(position["expiry_date"], str)
        assert "2026-01-17" in position["expiry_date"]

    def test_position_includes_all_required_fields(self, test_client, mock_alpaca_service):
        """Response includes all required position fields"""
        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        position = data["positions"][0]
        required_fields = ["id", "ticker", "strategy", "expiry_date", "legs", "created_at"]

        for field in required_fields:
            assert field in position, f"Missing field: {field}"

    def test_leg_includes_all_required_fields(self, test_client, mock_alpaca_service):
        """Response includes all required leg fields"""
        response = test_client.get("/api/positions")

        assert response.status_code == 200
        data = response.json()

        leg = data["positions"][0]["legs"][0]
        required_fields = [
            "id", "symbol", "direction", "strike", "option_type",
            "quantity", "entry_price", "current_price", "expiry_date", "underlying"
        ]

        for field in required_fields:
            assert field in leg, f"Missing field: {field}"
```

### Step 4: Create pytest Configuration

**File:** `apps/orchestrator_3_stream/backend/pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

## Validation Commands

```bash
# Navigate to backend directory
cd apps/orchestrator_3_stream/backend

# Install dev dependencies
uv add --dev pytest pytest-asyncio httpx

# Verify pytest is installed
uv run pytest --version

# Run integration tests
uv run pytest tests/test_alpaca_endpoints.py -v

# Run all Alpaca tests
uv run pytest tests/test_alpaca*.py -v

# Test endpoints manually (start server first)
# Terminal 1:
uv run uvicorn main:app --host 127.0.0.1 --port 9403 --reload

# Terminal 2:
curl http://127.0.0.1:9403/api/positions | jq .
curl http://127.0.0.1:9403/api/positions/circuit-status | jq .
curl -X POST http://127.0.0.1:9403/api/positions/subscribe-prices \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["SPY260117C00688000"]}' | jq .
```

## Acceptance Criteria

- [ ] pytest added to dev dependencies
- [ ] GET /api/positions returns iron condor positions
- [ ] GET /api/positions/{id} returns single position
- [ ] POST /api/positions/subscribe-prices starts streaming
- [ ] GET /api/positions/circuit-status returns circuit state
- [ ] All endpoints handle errors gracefully
- [ ] All integration tests pass
- [ ] Response models include computed fields (pnl_dollars, etc.)
- [ ] Dates serialize correctly as ISO strings

## Notes

### Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/positions | Get all iron condor positions |
| GET | /api/positions/{id} | Get specific position by ID |
| POST | /api/positions/subscribe-prices | Subscribe to price updates |
| GET | /api/positions/circuit-status | Get circuit breaker status |

### Testing Strategy

1. **Unit tests** (Part 1, 2): Test models and service in isolation
2. **Integration tests** (Part 3): Test endpoints with mocked service
3. **E2E tests** (Manual): Test with real Alpaca API in paper mode
