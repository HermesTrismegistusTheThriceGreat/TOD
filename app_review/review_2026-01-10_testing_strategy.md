# Code Review Report - Testing Strategy

**Generated**: 2026-01-10T12:00:00Z
**Reviewed Work**: Alpaca Trading API Integration Plan - Testing Strategy Analysis
**Plan Reference**: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
**Git Diff Summary**: Plan file is untracked (new file)
**Verdict**: ⚠️ FAIL

---

## Executive Summary

The plan provides a reasonable testing foundation with OCC parser unit tests and a manual integration test checklist. However, critical gaps exist in integration test automation, edge case coverage, error scenario testing, and frontend testing infrastructure. The plan violates the project's "Do not mock tests" rule by not providing real Alpaca API integration tests and lacks comprehensive validation of the WebSocket streaming functionality.

---

## Quick Reference

| #   | Description | Risk Level | Recommended Solution |
| --- | --- | --- | --- |
| 1 | No integration tests for REST endpoints | BLOCKER | Add pytest tests with TestClient |
| 2 | No WebSocket integration tests | BLOCKER | Add async WebSocket tests |
| 3 | Missing pytest in pyproject.toml dev deps | HIGH | Add pytest, pytest-asyncio deps |
| 4 | Frontend has no test framework | HIGH | Add Vitest for Vue component tests |
| 5 | Missing Alpaca API authentication edge cases | HIGH | Add auth failure test scenarios |
| 6 | Incomplete OCC parser edge case tests | MEDIUM | Add malformed symbol tests |
| 7 | No P/L calculation edge case tests | MEDIUM | Add zero price, negative qty tests |
| 8 | Iron condor validation tests missing | MEDIUM | Add incomplete/invalid IC tests |
| 9 | Manual testing checklist is not automated | MEDIUM | Convert to pytest integration tests |
| 10 | No WebSocket reconnection tests | MEDIUM | Add disconnect/reconnect scenarios |
| 11 | No test data fixtures defined | MEDIUM | Create reusable test fixtures |
| 12 | Missing database cleanup in tests | LOW | Add teardown for ephemeral tests |
| 13 | Validation commands not in CI format | LOW | Create pytest-compatible scripts |

---

## Issues by Risk Tier

### BLOCKER (Must Fix Before Merge)

#### Issue #1: No Integration Tests for REST Endpoints

**Description**: The plan includes 3 REST endpoints (`GET /api/positions`, `GET /api/positions/{id}`, `POST /api/positions/subscribe-prices`) but provides ZERO automated integration tests. The only testing mentioned is a manual `curl` command in "Validation Commands". This violates the project's established testing pattern shown in `test_database.py` which uses real connections.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `2099-2125` (Validation Commands section)

**Offending Code**:
```bash
# Test endpoints (in another terminal)
curl http://127.0.0.1:9403/api/positions | jq .
curl http://127.0.0.1:9403/health | jq .
```

**Recommended Solutions**:
1. **Add FastAPI TestClient Integration Tests** (Preferred)
   - Create `tests/test_alpaca_endpoints.py` with TestClient
   - Test all 3 endpoints with real Alpaca API (paper mode)
   - Include error cases (missing credentials, invalid position ID)
   - Rationale: Follows existing pattern in `test_autocomplete_endpoints.py`

2. **Add pytest-httpx for HTTP Mocking** (If real API unavailable)
   - Note: This conflicts with CLAUDE.md "Do not mock tests" rule
   - Only use if paper trading account unavailable in CI
   - Trade-off: Less realistic tests but CI-friendly

**Example Test File Structure**:
```python
# tests/test_alpaca_endpoints.py
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_get_positions_success(client):
    """Test successful positions fetch"""
    response = client.get("/api/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "error"]

@pytest.mark.asyncio
async def test_get_positions_no_credentials():
    """Test behavior when Alpaca credentials missing"""
    # Remove credentials, verify graceful error
    pass

@pytest.mark.asyncio
async def test_get_position_not_found(client):
    """Test 404-like response for invalid position ID"""
    response = client.get("/api/positions/invalid-uuid")
    assert response.json()["status"] == "error"
```

---

#### Issue #2: No WebSocket Integration Tests

**Description**: The plan adds `broadcast_option_price_update` and `broadcast_position_update` WebSocket methods but provides no automated tests for WebSocket streaming. The existing `test_websocket_raw.py` is a manual debugging script, not an automated test.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `866-909` (WebSocket broadcast section)

**Offending Code**:
```python
async def broadcast_option_price_update(self, update_data: dict):
    """
    Broadcast real-time option price update.
    # NO TEST PROVIDED
    """
```

**Recommended Solutions**:
1. **Add pytest-asyncio WebSocket Tests** (Preferred)
   - Create `tests/test_websocket_alpaca.py`
   - Use `websockets` library with TestClient
   - Verify message format matches TypeScript interfaces
   - Rationale: Critical for real-time price streaming

**Example Test Structure**:
```python
# tests/test_websocket_alpaca.py
import pytest
import asyncio
import websockets
import json

@pytest.mark.asyncio
async def test_option_price_update_broadcast():
    """Verify option_price_update message format"""
    async with websockets.connect("ws://127.0.0.1:9403/ws") as ws:
        # Trigger a price update (or mock it)
        # Verify message structure
        message = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(message)
        if data["type"] == "option_price_update":
            assert "update" in data
            assert "symbol" in data["update"]
            assert "mid_price" in data["update"]
```

---

### HIGH RISK (Should Fix Before Merge)

#### Issue #3: Missing pytest in pyproject.toml Dev Dependencies

**Description**: The `pyproject.toml` shows empty dev dependencies, but tests require pytest and pytest-asyncio. This will cause import failures when running the proposed tests.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/pyproject.toml`
- Lines: `18-19`

**Offending Code**:
```toml
[tool.uv]
dev-dependencies = []
```

**Recommended Solutions**:
1. **Add Test Dependencies** (Preferred)
   ```toml
   [tool.uv]
   dev-dependencies = [
       "pytest>=8.0.0",
       "pytest-asyncio>=0.23.0",
       "httpx>=0.27.0",  # For TestClient async support
   ]
   ```

---

#### Issue #4: Frontend Has No Test Framework

**Description**: The frontend `package.json` has no test framework configured (no Vitest, Jest, or testing-library). The plan adds 2 Vue composables and 1 service that have no test coverage path.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/package.json`
- Lines: `5-9` (scripts section)

**Offending Code**:
```json
"scripts": {
  "dev": "vite",
  "build": "vue-tsc && vite build",
  "preview": "vite preview"
  // No "test" script
}
```

**Recommended Solutions**:
1. **Add Vitest for Vue 3 Testing** (Preferred)
   - Add `vitest`, `@vue/test-utils`, `jsdom`
   - Create `vitest.config.ts`
   - Add test script: `"test": "vitest"`
   - Rationale: Vitest is the standard for Vite projects

2. **Add Testing Dependencies**:
   ```json
   "devDependencies": {
     "@testing-library/vue": "^8.0.0",
     "@vue/test-utils": "^2.4.0",
     "jsdom": "^24.0.0",
     "vitest": "^1.0.0"
   }
   ```

---

#### Issue #5: Missing Alpaca API Authentication Edge Cases

**Description**: The plan checks `is_configured` but doesn't test authentication failures, rate limiting, or API key revocation scenarios. Real trading integrations must handle auth failures gracefully.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `564-567`

**Offending Code**:
```python
@property
def is_configured(self) -> bool:
    """Check if Alpaca credentials are configured"""
    return bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)
    # No test for INVALID credentials
```

**Recommended Solutions**:
1. **Add Authentication Failure Tests**
   - Test with invalid API key
   - Test with revoked credentials
   - Test network timeout to Alpaca
   - Verify user-friendly error messages

**Test Cases Needed**:
```python
@pytest.mark.asyncio
async def test_invalid_api_credentials():
    """Service should gracefully handle invalid credentials"""
    service = AlpacaService()
    # Temporarily set invalid credentials
    with pytest.raises(AuthenticationError):
        await service.get_all_positions()

@pytest.mark.asyncio
async def test_api_rate_limiting():
    """Service should handle rate limit responses"""
    pass
```

---

### MEDIUM RISK (Fix Soon)

#### Issue #6: Incomplete OCC Parser Edge Case Tests

**Description**: The proposed OCC parser tests cover happy paths but miss critical edge cases: leap year dates, year 2100+ dates, maximum strike prices, symbols with trailing/leading spaces.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `1887-1960` (TestOCCSymbolParser class)

**Missing Test Cases**:
```python
def test_parse_february_29_leap_year(self):
    """Parse option expiring on Feb 29 (leap year)"""
    result = OCCSymbol.parse("SPY280229C00500000")
    assert result.expiry_date == date(2028, 2, 29)

def test_parse_invalid_date_raises(self):
    """Invalid date (Feb 30) should raise"""
    with pytest.raises(ValueError):
        OCCSymbol.parse("SPY260230C00500000")  # Feb 30 doesn't exist

def test_parse_high_strike(self):
    """Parse option with very high strike (e.g., BRK.A)"""
    result = OCCSymbol.parse("BRK260117C99999999")  # $99,999.999 strike
    assert result.strike_price == Decimal("99999.999")

def test_parse_whitespace_handling(self):
    """Whitespace should be rejected"""
    with pytest.raises(ValueError):
        OCCSymbol.parse(" SPY260117C00688000")
    with pytest.raises(ValueError):
        OCCSymbol.parse("SPY260117C00688000 ")

def test_parse_empty_string(self):
    """Empty string should raise"""
    with pytest.raises(ValueError):
        OCCSymbol.parse("")
```

---

#### Issue #7: No P/L Calculation Edge Case Tests

**Description**: P/L calculation tests only cover basic profit scenarios. Missing: zero entry price (division by zero), negative quantity handling, very large quantities, Decimal precision edge cases.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `1962-2007` (TestOptionLegPnL class)

**Missing Test Cases**:
```python
def test_zero_entry_price(self):
    """Zero entry price should not cause division by zero"""
    leg = OptionLeg(
        symbol="SPY260117C00688000",
        direction="Short",
        strike=Decimal("688"),
        option_type="Call",
        quantity=10,
        entry_price=Decimal("0"),  # Zero!
        current_price=Decimal("3.00"),
        expiry_date=date(2026, 1, 17),
        underlying="SPY"
    )
    assert leg.pnl_percent == Decimal("0")  # Should handle gracefully

def test_very_large_quantity(self):
    """Large quantities should not overflow"""
    leg = OptionLeg(
        quantity=100000,  # 100k contracts
        entry_price=Decimal("5.00"),
        current_price=Decimal("4.00"),
        # ... other fields
    )
    # P/L = $1 * 100000 * 100 = $10,000,000
    assert leg.pnl_dollars == Decimal("10000000")

def test_decimal_precision(self):
    """Ensure Decimal precision is maintained"""
    leg = OptionLeg(
        entry_price=Decimal("1.235"),
        current_price=Decimal("1.234"),
        quantity=1,
        direction="Short",
        # ...
    )
    # Should maintain sub-cent precision
    assert leg.pnl_dollars != 0
```

---

#### Issue #8: Iron Condor Validation Tests Missing

**Description**: The plan includes `is_valid_iron_condor()` method but no tests for invalid iron condor structures: 3 legs, duplicate legs, wrong strike ordering, mixed expirations.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `385-395`

**Missing Test Cases**:
```python
class TestIronCondorValidation:
    def test_three_legs_invalid(self):
        """3 legs is not a valid iron condor"""
        ic = IronCondorPosition(legs=[leg1, leg2, leg3])  # Only 3
        assert ic.is_valid_iron_condor() is False

    def test_wrong_strike_order_invalid(self):
        """Strikes in wrong order should be invalid"""
        # long_put.strike > short_put.strike is INVALID
        pass

    def test_duplicate_legs_invalid(self):
        """Duplicate leg types should be invalid"""
        pass

    def test_mixed_expirations_invalid(self):
        """Legs with different expirations shouldn't form IC"""
        pass

    def test_mixed_underlyings_invalid(self):
        """Legs on different tickers shouldn't form IC"""
        pass
```

---

#### Issue #9: Manual Testing Checklist Not Automated

**Description**: The plan has a 6-item "Manual Test Checklist" that should be automated to prevent regression.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `2053-2060`

**Offending Code**:
```markdown
**Manual Test Checklist:**
- [ ] Backend starts without errors
- [ ] GET /api/positions returns iron condor data
- [ ] WebSocket connects and receives price updates
- [ ] IronCondorCard displays live data
- [ ] P/L updates when prices change
- [ ] Graceful handling when API credentials missing
```

**Recommended Solution**:
Convert each manual check to an automated test:
```python
# tests/test_integration_checklist.py

@pytest.mark.integration
async def test_backend_starts_without_errors():
    """Checklist #1: Backend starts"""
    # Start app in subprocess, verify no exceptions
    pass

@pytest.mark.integration
async def test_positions_endpoint_returns_data():
    """Checklist #2: GET /api/positions works"""
    pass
```

---

#### Issue #10: No WebSocket Reconnection Tests

**Description**: The plan mentions "reconnection logic handles disconnects" as an acceptance criterion but provides no tests for:
- Server restart handling
- Network interruption recovery
- Stale subscription cleanup

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
- Lines: `2098-2100`

---

#### Issue #11: No Test Data Fixtures Defined

**Description**: Tests will need consistent mock positions, OCC symbols, and price updates. No fixtures are defined for reusable test data.

**Recommended Solution**:
Create `tests/fixtures.py`:
```python
import pytest
from decimal import Decimal
from datetime import date

@pytest.fixture
def sample_occ_symbols():
    return [
        "SPY260117C00688000",
        "SPY260117C00697000",
        "SPY260117P00683000",
        "SPY260117P00688000",
    ]

@pytest.fixture
def sample_iron_condor():
    return IronCondorPosition(
        ticker="SPY",
        expiry_date=date(2026, 1, 17),
        legs=[...],
    )
```

---

### LOW RISK (Nice to Have)

#### Issue #12: Missing Database Cleanup in Tests

**Description**: Per CLAUDE.md: "The trick with database connection is to make sure your tests are ephemeral." The proposed tests don't show teardown/cleanup.

**Location**:
- File: `/Users/muzz/Desktop/tac/TOD/CLAUDE.md`
- Lines: `4-5`

---

#### Issue #13: Validation Commands Not in CI Format

**Description**: The validation commands are shell scripts but not wrapped in pytest for CI integration.

---

## Plan Compliance Check

### Testing Strategy Section Analysis (Lines 2061-2078)

| Criteria | Status | Notes |
|----------|--------|-------|
| Unit Tests - OCC parser | ⚠️ Partial | Missing edge cases (Issue #6) |
| Unit Tests - P/L calculations | ⚠️ Partial | Missing zero/edge cases (Issue #7) |
| Unit Tests - Position grouping | ❌ Missing | No tests for iron condor detection |
| Unit Tests - Pydantic validation | ❌ Missing | No model validation tests |
| Integration Tests - REST endpoints | ❌ Missing | Only manual curl (Issue #1) |
| Integration Tests - WebSocket | ❌ Missing | No automated WS tests (Issue #2) |
| Integration Tests - Frontend composables | ❌ Missing | No test framework (Issue #4) |
| Integration Tests - Store updates | ❌ Missing | No Pinia store tests |
| Manual Testing | ⚠️ Defined | Should be automated (Issue #9) |

### Acceptance Criteria Verification

| Criteria | Testable | Test Provided |
|----------|----------|---------------|
| AlpacaService initializes with credentials | Yes | ❌ No |
| GET /api/positions returns iron condor positions | Yes | ❌ No (only curl) |
| WebSocket broadcasts price updates | Yes | ❌ No |
| OCC parser handles all valid symbol formats | Yes | ⚠️ Partial |
| Error handling for missing credentials | Yes | ❌ No |
| IronCondorCard displays real position data | Yes | ❌ No (no frontend tests) |
| Prices update in real-time via WebSocket | Yes | ❌ No |
| P/L calculations are correct | Yes | ⚠️ Partial |
| Loading and error states work | Yes | ❌ No |
| Mock data mode works for development | Yes | ❌ No |
| End-to-end flow from Alpaca to UI works | Yes | ❌ No |
| Reconnection logic handles disconnects | Yes | ❌ No |
| Multiple positions display correctly | Yes | ❌ No |

---

## Verification Checklist

- [ ] All blockers addressed
- [ ] High-risk issues reviewed and resolved or accepted
- [ ] Breaking changes documented with migration guide
- [ ] Security vulnerabilities patched
- [ ] Performance regressions investigated
- [x] Tests cover new functionality - **INSUFFICIENT COVERAGE**
- [ ] Documentation updated for API changes

---

## Final Verdict

**Status**: ⚠️ FAIL

**Reasoning**:
The plan has 2 BLOCKERS that must be resolved:
1. No integration tests for the 3 REST endpoints (only manual curl)
2. No WebSocket streaming tests

Additionally, 4 HIGH RISK issues compound the testing gaps:
- No pytest dependencies in pyproject.toml
- No frontend test framework at all
- Missing authentication failure scenarios
- Critical for a trading integration where failures = money

The plan provides ~15% of necessary test coverage. The existing test suite in `tests/` follows good patterns (real DB, async, fixtures) that should be replicated for Alpaca integration.

**Next Steps**:
1. **Immediate**: Add integration test file `tests/test_alpaca_endpoints.py` with TestClient
2. **Immediate**: Add WebSocket test file `tests/test_websocket_alpaca.py`
3. **Before Build**: Add pytest, pytest-asyncio to dev dependencies
4. **Before Build**: Set up Vitest in frontend for composable tests
5. **During Build**: Add edge case tests for OCC parser and P/L calculations
6. **Post-Build**: Create CI pipeline that runs all tests with paper trading credentials

---

## Suggested Test File Structure

```
apps/orchestrator_3_stream/
├── backend/
│   ├── tests/
│   │   ├── fixtures.py                    # NEW: Reusable test data
│   │   ├── test_occ_parser.py             # EXISTS in plan (expand)
│   │   ├── test_alpaca_models.py          # NEW: Pydantic validation
│   │   ├── test_alpaca_service.py         # NEW: Service unit tests
│   │   ├── test_alpaca_endpoints.py       # NEW: REST integration
│   │   ├── test_websocket_alpaca.py       # NEW: WS integration
│   │   └── test_integration_e2e.py        # NEW: Full flow tests
│   └── pyproject.toml                     # UPDATE: Add test deps
└── frontend/
    ├── src/
    │   └── composables/
    │       ├── useAlpacaPositions.ts
    │       └── useAlpacaPositions.test.ts # NEW
    ├── vitest.config.ts                   # NEW
    └── package.json                       # UPDATE: Add vitest
```

---

**Report File**: `app_review/review_2026-01-10_testing_strategy.md`
