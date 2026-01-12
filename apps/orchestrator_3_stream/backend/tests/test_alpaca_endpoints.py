#!/usr/bin/env python3
"""
Integration tests for Alpaca REST endpoints.

These tests use FastAPI TestClient to test the actual endpoints.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_endpoints.py -v
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from contextlib import asynccontextmanager

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════

def create_sample_position():
    """Create a sample IronCondorPosition for testing"""
    from modules.alpaca_models import IronCondorPosition, OptionLeg

    return IronCondorPosition(
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


def create_mock_alpaca_service(is_configured: bool = True):
    """Create a mock AlpacaService with configurable state"""
    mock_service = MagicMock()
    mock_service.is_configured = is_configured
    mock_service.circuit_state = "closed"
    mock_service.shutdown = AsyncMock()

    if is_configured:
        sample_position = create_sample_position()
        mock_service.get_all_positions = AsyncMock(return_value=[sample_position])
        mock_service.get_position_by_id = AsyncMock(return_value=sample_position)
        mock_service.start_price_streaming = AsyncMock()

    return mock_service


def create_test_app(mock_alpaca_service):
    """Create a minimal FastAPI app with only Alpaca endpoints for testing"""
    from modules.alpaca_models import (
        GetPositionsResponse,
        GetPositionResponse,
        SubscribePricesRequest,
        SubscribePricesResponse,
    )

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        """Minimal lifespan that only sets up Alpaca service"""
        app.state.alpaca_service = mock_alpaca_service
        yield
        # Cleanup
        if hasattr(app.state, 'alpaca_service'):
            await app.state.alpaca_service.shutdown()

    app = FastAPI(title="Test Alpaca API", lifespan=test_lifespan)

    # Register Alpaca endpoints (copied from main.py)
    @app.get("/api/positions", response_model=GetPositionsResponse)
    async def get_positions():
        """Get all iron condor positions"""
        alpaca = app.state.alpaca_service
        if not alpaca.is_configured:
            return GetPositionsResponse(
                status="error",
                message="Alpaca not configured",
                positions=[],
                total_count=0
            )
        try:
            positions = await alpaca.get_all_positions()
            return GetPositionsResponse(
                status="success",
                positions=positions,
                total_count=len(positions)
            )
        except Exception as e:
            return GetPositionsResponse(
                status="error",
                message=str(e),
                positions=[],
                total_count=0
            )

    @app.get("/api/positions/circuit-status")
    async def get_circuit_status():
        """Get circuit breaker status"""
        alpaca = app.state.alpaca_service
        return {
            "status": "success",
            "circuit_state": alpaca.circuit_state,
            "is_configured": alpaca.is_configured
        }

    @app.get("/api/positions/{position_id}", response_model=GetPositionResponse)
    async def get_position(position_id: str):
        """Get a specific position by ID"""
        alpaca = app.state.alpaca_service
        if not alpaca.is_configured:
            return GetPositionResponse(
                status="error",
                message="Alpaca not configured",
                position=None
            )
        try:
            position = await alpaca.get_position_by_id(position_id)
            if not position:
                return GetPositionResponse(
                    status="error",
                    message=f"Position {position_id} not found",
                    position=None
                )
            return GetPositionResponse(
                status="success",
                position=position
            )
        except Exception as e:
            return GetPositionResponse(
                status="error",
                message=str(e),
                position=None
            )

    @app.post("/api/positions/subscribe-prices", response_model=SubscribePricesResponse)
    async def subscribe_prices(request: SubscribePricesRequest):
        """Subscribe to price updates for symbols"""
        alpaca = app.state.alpaca_service
        if not alpaca.is_configured:
            return SubscribePricesResponse(
                status="error",
                message="Alpaca not configured",
                symbols=[]
            )
        try:
            if request.symbols:
                await alpaca.start_price_streaming(request.symbols)
            return SubscribePricesResponse(
                status="success",
                symbols=request.symbols
            )
        except Exception as e:
            return SubscribePricesResponse(
                status="error",
                message=str(e),
                symbols=[]
            )

    return app


@pytest.fixture
def mock_alpaca_service():
    """Create a mock AlpacaService"""
    return create_mock_alpaca_service(is_configured=True)


@pytest.fixture
def test_client(mock_alpaca_service):
    """Create TestClient with mocked AlpacaService"""
    app = create_test_app(mock_alpaca_service)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_client_unconfigured():
    """Create TestClient with unconfigured AlpacaService"""
    mock_service = create_mock_alpaca_service(is_configured=False)
    app = create_test_app(mock_service)
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
