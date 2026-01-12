# Code Review Report

**Generated**: 2026-01-10T14:30:00Z
**Reviewed Work**: Alpaca Trading API Integration Plan for IronCondorCard
**Plan Reference**: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
**Git Diff Summary**: 0 files changed (plan review - no implementation yet)
**Verdict**: ✅ PASS (with recommendations)

---

## Executive Summary

This is a **plan review** for the Alpaca Trading API integration. The plan is well-structured with a solid hybrid REST + WebSocket architecture. The Pydantic models follow codebase conventions, and the AlpacaService design is appropriate. However, there are several medium-risk issues around Decimal/float consistency, deprecated Pydantic Config syntax, and potential thread-safety concerns that should be addressed before implementation.

---

## Quick Reference

| #   | Description                                    | Risk Level | Recommended Solution                        |
| --- | ---------------------------------------------- | ---------- | ------------------------------------------- |
| 1   | Pydantic Config class deprecated in v2         | HIGH       | Use `model_config = ConfigDict(...)`        |
| 2   | Decimal/float inconsistency with codebase      | HIGH       | Use float like existing models do           |
| 3   | Missing HTTP status codes in error responses   | MEDIUM     | Return proper 4xx/5xx with HTTPException    |
| 4   | Thread-safety issue with global service        | MEDIUM     | Use FastAPI dependency injection            |
| 5   | asyncio.get_event_loop() deprecated pattern    | MEDIUM     | Use asyncio.get_running_loop()              |
| 6   | Missing alpaca-py in test dependencies         | MEDIUM     | Add pytest to dev-dependencies              |
| 7   | Inconsistent field naming (snake vs camel)     | LOW        | Use alias for API serialization             |
| 8   | OCCSymbol.parse lacks memoization              | LOW        | Consider caching parsed symbols             |

---

## Issues by Risk Tier

### ⚠️ HIGH RISK (Should Fix Before Merge)

#### Issue #1: Pydantic Config class deprecated in v2

**Description**: The plan uses the deprecated `class Config:` syntax which was superseded in Pydantic v2. The existing codebase (`orch_database_models.py`) uses `Config` but this is for legacy compatibility. New code should use `model_config`.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `320-325`, `397-403`, `429-434`

**Offending Code**:
```python
class Config:
    json_encoders = {
        Decimal: float,
        date: lambda v: v.isoformat()
    }
```

**Recommended Solutions**:
1. **Use ConfigDict** (Preferred)
   ```python
   from pydantic import ConfigDict

   class OptionLeg(BaseModel):
       model_config = ConfigDict(
           from_attributes=True,
           ser_json_timedelta='iso8601',
       )
       # For Decimal serialization, use field serializers instead
   ```
   - Rationale: Modern Pydantic v2 approach, more explicit

2. **Use field_serializer for Decimal**
   ```python
   from pydantic import field_serializer

   @field_serializer('strike', 'entry_price', 'current_price')
   def serialize_decimal(self, v: Decimal) -> float:
       return float(v)
   ```
   - Trade-off: More verbose but more precise control

---

#### Issue #2: Decimal/float inconsistency with codebase patterns

**Description**: The plan uses `Decimal` for financial values, but the existing codebase (`orch_database_models.py`) consistently uses `float` with a `convert_decimal` validator. This inconsistency could cause serialization issues when integrating with the existing database models.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `286-291` (OptionLeg fields)

**Offending Code**:
```python
strike: Decimal
entry_price: Decimal  # Average fill price
current_price: Decimal = Decimal("0")  # Updated via WebSocket
```

**Recommended Solutions**:
1. **Use float like existing models** (Preferred)
   ```python
   strike: float
   entry_price: float
   current_price: float = 0.0

   @field_validator('strike', 'entry_price', 'current_price', mode='before')
   @classmethod
   def convert_decimal(cls, v):
       if isinstance(v, Decimal):
           return float(v)
       return float(v) if v is not None else 0.0
   ```
   - Rationale: Matches existing `OrchestratorAgent.total_cost` pattern in `orch_database_models.py`

2. **Keep Decimal but add proper serialization**
   - Trade-off: More precision for financial data, but requires extra serialization logic throughout

---

### ⚡ MEDIUM RISK (Fix Soon)

#### Issue #3: Missing HTTP status codes in error responses

**Description**: The plan's REST endpoints return error responses with `status: "error"` but don't raise proper HTTP exceptions. This means all responses return 200 OK even for errors, which breaks REST conventions and makes error handling harder for clients.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `949-978` (get_positions endpoint)

**Offending Code**:
```python
@app.get("/api/positions", response_model=GetPositionsResponse)
async def get_positions():
    try:
        # ...
        if not alpaca_service.is_configured:
            return GetPositionsResponse(
                status="error",
                message="Alpaca API not configured"
            )
    except Exception as e:
        return GetPositionsResponse(
            status="error",
            message=str(e)
        )
```

**Recommended Solutions**:
1. **Use HTTPException for errors** (Preferred)
   ```python
   from fastapi import HTTPException

   @app.get("/api/positions", response_model=GetPositionsResponse)
   async def get_positions():
       alpaca_service = get_alpaca_service()

       if not alpaca_service.is_configured:
           raise HTTPException(
               status_code=503,  # Service Unavailable
               detail="Alpaca API not configured"
           )

       try:
           positions = await alpaca_service.get_all_positions()
           return GetPositionsResponse(
               status="success",
               positions=positions,
               total_count=len(positions)
           )
       except Exception as e:
           logger.error(f"Failed to get positions: {e}")
           raise HTTPException(status_code=500, detail=str(e))
   ```
   - Rationale: Follows existing pattern in `main.py` (see `/send_chat`, `/load_chat`)

---

#### Issue #4: Thread-safety issue with global service singleton

**Description**: The `get_alpaca_service()` function uses a module-level global variable without thread-safety protection. While Python's GIL provides some protection, this pattern can cause issues in async FastAPI applications with multiple concurrent requests.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `836-844`

**Offending Code**:
```python
_alpaca_service: Optional[AlpacaService] = None

def get_alpaca_service() -> AlpacaService:
    global _alpaca_service
    if _alpaca_service is None:
        _alpaca_service = AlpacaService()
    return _alpaca_service
```

**Recommended Solutions**:
1. **Use FastAPI app.state like other services** (Preferred)
   ```python
   # In lifespan:
   alpaca_service = await init_alpaca_service()
   app.state.alpaca_service = alpaca_service

   # In endpoint:
   @app.get("/api/positions")
   async def get_positions(request: Request):
       alpaca_service = request.app.state.alpaca_service
       # ...
   ```
   - Rationale: Matches existing pattern for `orchestrator_service` and `autocomplete_service`

2. **Use FastAPI Depends() for dependency injection**
   ```python
   from fastapi import Depends

   async def get_alpaca_service_dep() -> AlpacaService:
       return app.state.alpaca_service

   @app.get("/api/positions")
   async def get_positions(service: AlpacaService = Depends(get_alpaca_service_dep)):
       # ...
   ```
   - Trade-off: More explicit dependency, better for testing

---

#### Issue #5: Deprecated asyncio.get_event_loop() pattern

**Description**: The plan uses `asyncio.get_event_loop()` which is deprecated in Python 3.10+ and will raise DeprecationWarning. In async functions, `asyncio.get_running_loop()` should be used instead.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `612-615`, `761`

**Offending Code**:
```python
loop = asyncio.get_event_loop()
positions = await loop.run_in_executor(
    None, client.get_all_positions
)
```

**Recommended Solutions**:
1. **Use asyncio.get_running_loop()** (Preferred)
   ```python
   loop = asyncio.get_running_loop()
   positions = await loop.run_in_executor(None, client.get_all_positions)
   ```
   - Rationale: Python 3.12+ compatible, no deprecation warnings

2. **Use asyncio.to_thread() for Python 3.9+**
   ```python
   positions = await asyncio.to_thread(client.get_all_positions)
   ```
   - Trade-off: Cleaner syntax but only Python 3.9+

---

#### Issue #6: Missing test dependencies in pyproject.toml

**Description**: The plan adds tests in `tests/test_occ_parser.py` but doesn't add pytest to the project dependencies. The current `pyproject.toml` shows `dev-dependencies = []`.

**Location**:
- File: `apps/orchestrator_3_stream/backend/pyproject.toml`
- Lines: `18-19`

**Offending Code**:
```toml
[tool.uv]
dev-dependencies = []
```

**Recommended Solutions**:
1. **Add pytest to dev-dependencies** (Preferred)
   ```toml
   [tool.uv]
   dev-dependencies = [
       "pytest>=7.0",
       "pytest-asyncio>=0.21",
   ]
   ```
   - Run: `uv add --dev pytest pytest-asyncio`

---

### 💡 LOW RISK (Nice to Have)

#### Issue #7: Inconsistent field naming between Python and TypeScript

**Description**: The Pydantic models use snake_case (`entry_price`, `current_price`) while the plan mentions TypeScript expects camelCase (`entryPrice`, `currentPrice`). The plan includes transform functions, but using Pydantic's alias feature would be cleaner.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `278-324` (OptionLeg model)

**Recommended Solutions**:
1. **Use Pydantic Field aliases with populate_by_name**
   ```python
   from pydantic import Field, ConfigDict

   class OptionLeg(BaseModel):
       model_config = ConfigDict(populate_by_name=True)

       entry_price: float = Field(alias="entryPrice")
       current_price: float = Field(alias="currentPrice", default=0.0)
   ```
   - Rationale: Automatic camelCase serialization in API responses

---

#### Issue #8: OCCSymbol.parse() lacks caching

**Description**: The OCC symbol parser is called potentially hundreds of times per request (once per position, plus in grouping logic). While not expensive, adding a simple cache would improve performance.

**Location**:
- File: `specs/alpaca-ironcondor-integration-plan.md`
- Lines: `234-271`

**Recommended Solutions**:
1. **Add functools.lru_cache**
   ```python
   from functools import lru_cache

   @classmethod
   @lru_cache(maxsize=1000)
   def parse(cls, symbol: str) -> 'OCCSymbol':
       # ... existing logic
   ```
   - Rationale: Same symbols parsed multiple times during position grouping

---

## Plan Compliance Check

The plan covers all major areas well. Checklist against stated acceptance criteria:

- [x] AlpacaService initializes with credentials from .env
- [x] GET /api/positions returns iron condor positions
- [x] WebSocket broadcasts price updates
- [x] OCC parser handles valid symbol formats
- [x] Error handling for missing credentials
- [x] Pydantic models defined for all data structures
- [x] Unit tests specified for OCC parser

**Missing from plan:**
- [ ] Integration test setup with mock Alpaca responses
- [ ] Rate limiting for Alpaca API calls
- [ ] Reconnection backoff strategy for WebSocket streams

---

## Verification Checklist

- [x] No blockers identified
- [ ] High-risk issues reviewed and resolved or accepted (2 issues to address)
- [x] Breaking changes documented with migration guide (N/A - new feature)
- [x] Security vulnerabilities patched (credentials from env, not hardcoded)
- [x] Performance regressions investigated (streaming approach is appropriate)
- [x] Tests cover new functionality (OCC parser tests included)
- [x] Documentation updated for API changes (inline in plan)

---

## Final Verdict

**Status**: ✅ PASS (with recommendations)

**Reasoning**: This is a well-designed plan that follows the existing codebase patterns closely. The hybrid REST + WebSocket architecture is appropriate for the use case. No blockers were identified. The two HIGH risk items are straightforward fixes that should be incorporated before or during implementation:
1. Use modern Pydantic v2 `model_config` instead of deprecated `Config` class
2. Use `float` instead of `Decimal` to match existing codebase patterns

**Next Steps**:
1. Update plan to use `model_config = ConfigDict(...)` instead of `class Config:`
2. Change `Decimal` fields to `float` with proper validators (matching `orch_database_models.py` patterns)
3. Use `app.state.alpaca_service` pattern instead of global singleton
4. Ensure `pytest` and `pytest-asyncio` are added to dev-dependencies before writing tests
5. Use `asyncio.get_running_loop()` instead of deprecated `asyncio.get_event_loop()`
6. Consider using HTTPException for error responses to return proper HTTP status codes

---

**Report File**: `app_review/review_2026-01-10_alpaca-plan-backend.md`
