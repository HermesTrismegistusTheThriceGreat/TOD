# Plan: Alpaca Close Strategy Implementation

## Task Description
Implement the close strategy functionality for the Alpaca trading integration. The "Close Strategy" button exists in `IronCondorCard.vue:238` but is NOT connected to any backend endpoint. This plan covers implementing backend methods to close positions via Alpaca API, adding REST endpoints, and wiring up the frontend with confirmation dialogs and loading states.

## Objective
Enable users to close entire option strategies (all legs) or individual legs via the IronCondorCard UI, with proper confirmation dialogs, loading states, error handling, and real-time position refresh after successful closes.

## Problem Statement
The trading UI has "Close Strategy" and "Close Leg" buttons that are non-functional placeholders. Users cannot close their option positions from the application, requiring them to use Alpaca's web interface directly. This breaks the workflow and creates friction for position management.

## Solution Approach
1. **Backend Service Layer**: Add methods to `AlpacaService` that use Alpaca's `TradingClient` to submit closing orders for option positions
2. **API Endpoints**: Add REST endpoints for closing strategies and individual legs
3. **Frontend Integration**: Wire up buttons with confirmation dialogs, loading states, and error handling
4. **Position Refresh**: Automatically refresh positions after successful close to update the UI

## Relevant Files

### Existing Files to Modify
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` - Add close methods using TradingClient
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Add request/response Pydantic models
- `apps/orchestrator_3_stream/backend/main.py` - Add API endpoints
- `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts` - Add API client functions
- `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts` - Add TypeScript interfaces
- `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue` - Wire up buttons with UX

### Reference Files
- `apps/orchestrator_3_stream/backend/modules/config.py` - Alpaca configuration (ALPACA_PAPER setting)
- `apps/orchestrator_3_stream/backend/modules/circuit_breaker.py` - Circuit breaker pattern to follow

## Implementation Phases

### Phase 1: Foundation (Backend Models)
Add Pydantic models for close operations request/response handling.

### Phase 2: Core Implementation (Backend Service + Endpoints)
Implement the actual Alpaca API integration for closing positions and expose via REST.

### Phase 3: Integration & Polish (Frontend)
Wire up the UI components with proper UX patterns (confirmation, loading, error handling).

## Step by Step Tasks

### 1. Add Pydantic Models for Close Operations
Add to `apps/orchestrator_3_stream/backend/modules/alpaca_models.py`:

- Add `CloseOrderResult` model:
  ```python
  class CloseOrderResult(BaseModel):
      """Result of a single close order"""
      symbol: str
      order_id: str
      status: Literal['submitted', 'filled', 'failed']
      filled_qty: int = 0
      filled_avg_price: Optional[float] = None
      error_message: Optional[str] = None
  ```

- Add `CloseStrategyRequest` model:
  ```python
  class CloseStrategyRequest(BaseModel):
      """Request to close an entire strategy (all legs)"""
      position_id: str
      order_type: Literal['market', 'limit'] = 'market'
      limit_price_offset: Optional[float] = None  # For limit orders: offset from mid price
  ```

- Add `CloseStrategyResponse` model:
  ```python
  class CloseStrategyResponse(BaseModel):
      """Response for close strategy operation"""
      status: Literal['success', 'partial', 'error']
      position_id: str
      orders: List[CloseOrderResult] = []
      message: Optional[str] = None
      total_legs: int = 0
      closed_legs: int = 0
  ```

- Add `CloseLegRequest` model:
  ```python
  class CloseLegRequest(BaseModel):
      """Request to close a single leg"""
      leg_id: str
      order_type: Literal['market', 'limit'] = 'market'
      limit_price: Optional[float] = None
  ```

- Add `CloseLegResponse` model:
  ```python
  class CloseLegResponse(BaseModel):
      """Response for close leg operation"""
      status: Literal['success', 'error']
      order: Optional[CloseOrderResult] = None
      message: Optional[str] = None
  ```

- Update `__all__` exports list

### 2. Add Close Methods to AlpacaService
Add to `apps/orchestrator_3_stream/backend/modules/alpaca_service.py`:

- Add imports at top:
  ```python
  from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
  from alpaca.trading.enums import OrderSide, TimeInForce
  ```

- Add new section comment:
  ```python
  # ═══════════════════════════════════════════════════════════
  # POSITION CLOSING (REST)
  # ═══════════════════════════════════════════════════════════
  ```

- Add `close_leg()` method:
  - Parameters: `symbol: str`, `quantity: int`, `direction: str`, `order_type: str = 'market'`, `limit_price: Optional[float] = None`
  - Logic:
    1. Determine order side (buy to close short, sell to close long)
    2. Create appropriate order request (Market or Limit)
    3. Submit order via TradingClient using run_in_executor
    4. Return CloseOrderResult with order details
  - Use circuit breaker for API resilience
  - Log all operations with logger

- Add `close_strategy()` method:
  - Parameters: `position_id: str`, `order_type: str = 'market'`
  - Logic:
    1. Get position from cache or fetch
    2. For each leg, call `close_leg()`
    3. Collect results and determine overall status
    4. Clear position from cache on success
    5. Broadcast status update via WebSocket
  - Return CloseStrategyResponse with all order results

- Add helper method `_determine_close_side()`:
  ```python
  def _determine_close_side(self, direction: str) -> OrderSide:
      """Determine the order side needed to close a position"""
      # Short positions: buy to close
      # Long positions: sell to close
      return OrderSide.BUY if direction == 'Short' else OrderSide.SELL
  ```

### 3. Add API Endpoints to main.py
Add to `apps/orchestrator_3_stream/backend/main.py`:

- Add imports for new models:
  ```python
  from modules.alpaca_models import (
      ...,
      CloseStrategyRequest,
      CloseStrategyResponse,
      CloseLegRequest,
      CloseLegResponse,
  )
  ```

- Add POST `/api/positions/{position_id}/close-strategy` endpoint:
  ```python
  @app.post("/api/positions/{position_id}/close-strategy", response_model=CloseStrategyResponse, tags=["Alpaca"])
  async def close_strategy(request: Request, position_id: str, close_request: CloseStrategyRequest):
  ```
  - Validate position exists
  - Call `alpaca_service.close_strategy()`
  - Return CloseStrategyResponse

- Add POST `/api/positions/{position_id}/close-leg` endpoint:
  ```python
  @app.post("/api/positions/{position_id}/close-leg", response_model=CloseLegResponse, tags=["Alpaca"])
  async def close_leg(request: Request, position_id: str, close_request: CloseLegRequest):
  ```
  - Validate position and leg exist
  - Call `alpaca_service.close_leg()` for the specific leg
  - Return CloseLegResponse

### 4. Add Frontend TypeScript Types
Add to `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`:

- Add raw types (snake_case from backend):
  ```typescript
  export interface RawCloseOrderResult {
    symbol: string
    order_id: string
    status: 'submitted' | 'filled' | 'failed'
    filled_qty: number
    filled_avg_price?: number
    error_message?: string
  }

  export interface RawCloseStrategyResponse {
    status: 'success' | 'partial' | 'error'
    position_id: string
    orders: RawCloseOrderResult[]
    message?: string
    total_legs: number
    closed_legs: number
  }

  export interface RawCloseLegResponse {
    status: 'success' | 'error'
    order?: RawCloseOrderResult
    message?: string
  }
  ```

- Add frontend types (camelCase):
  ```typescript
  export interface CloseOrderResult {
    symbol: string
    orderId: string
    status: 'submitted' | 'filled' | 'failed'
    filledQty: number
    filledAvgPrice?: number
    errorMessage?: string
  }

  export interface CloseStrategyResponse {
    status: 'success' | 'partial' | 'error'
    positionId: string
    orders: CloseOrderResult[]
    message?: string
    totalLegs: number
    closedLegs: number
  }

  export interface CloseLegResponse {
    status: 'success' | 'error'
    order?: CloseOrderResult
    message?: string
  }
  ```

- Add transform functions:
  ```typescript
  export function transformCloseOrderResult(raw: RawCloseOrderResult): CloseOrderResult
  export function transformCloseStrategyResponse(raw: RawCloseStrategyResponse): CloseStrategyResponse
  export function transformCloseLegResponse(raw: RawCloseLegResponse): CloseLegResponse
  ```

### 5. Add Frontend API Service Functions
Add to `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts`:

- Add imports for new types

- Add `closeStrategy()` function:
  ```typescript
  export async function closeStrategy(
    positionId: string,
    orderType: 'market' | 'limit' = 'market'
  ): Promise<CloseStrategyResponse> {
    const response = await apiClient.post<RawCloseStrategyResponse>(
      `/api/positions/${positionId}/close-strategy`,
      { position_id: positionId, order_type: orderType }
    )
    return transformCloseStrategyResponse(response.data)
  }
  ```

- Add `closeLeg()` function:
  ```typescript
  export async function closeLeg(
    positionId: string,
    legId: string,
    orderType: 'market' | 'limit' = 'market'
  ): Promise<CloseLegResponse> {
    const response = await apiClient.post<RawCloseLegResponse>(
      `/api/positions/${positionId}/close-leg`,
      { leg_id: legId, order_type: orderType }
    )
    return transformCloseLegResponse(response.data)
  }
  ```

### 6. Wire Up IronCondorCard Component
Modify `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`:

- Add imports:
  ```typescript
  import { ElMessageBox, ElMessage } from 'element-plus'
  import * as alpacaService from '../services/alpacaService'
  ```

- Add local state:
  ```typescript
  const closingStrategy = ref(false)
  const closingLegId = ref<string | null>(null)
  ```

- Add `handleCloseStrategy()` method:
  ```typescript
  async function handleCloseStrategy() {
    if (!position.value) return

    try {
      await ElMessageBox.confirm(
        `Are you sure you want to close all ${position.value.legs.length} legs of this ${position.value.strategy}? This will submit market orders to close all positions.`,
        'Close Strategy',
        { confirmButtonText: 'Close All', cancelButtonText: 'Cancel', type: 'warning' }
      )

      closingStrategy.value = true
      const result = await alpacaService.closeStrategy(position.value.id)

      if (result.status === 'success') {
        ElMessage.success(`Successfully closed ${result.closedLegs} legs`)
        await refresh()
      } else if (result.status === 'partial') {
        ElMessage.warning(`Partially closed: ${result.closedLegs}/${result.totalLegs} legs. ${result.message}`)
        await refresh()
      } else {
        ElMessage.error(result.message || 'Failed to close strategy')
      }
    } catch (e) {
      if (e !== 'cancel') {
        ElMessage.error('Failed to close strategy')
        console.error('Close strategy error:', e)
      }
    } finally {
      closingStrategy.value = false
    }
  }
  ```

- Add `handleCloseLeg()` method:
  ```typescript
  async function handleCloseLeg(leg: OptionLeg) {
    if (!position.value) return

    try {
      await ElMessageBox.confirm(
        `Close ${leg.direction} ${leg.optionType} $${leg.strike} (${leg.quantity} contracts)?`,
        'Close Leg',
        { confirmButtonText: 'Close', cancelButtonText: 'Cancel', type: 'warning' }
      )

      closingLegId.value = leg.id
      const result = await alpacaService.closeLeg(position.value.id, leg.id)

      if (result.status === 'success') {
        ElMessage.success(`Closed ${leg.symbol}`)
        await refresh()
      } else {
        ElMessage.error(result.message || 'Failed to close leg')
      }
    } catch (e) {
      if (e !== 'cancel') {
        ElMessage.error('Failed to close leg')
        console.error('Close leg error:', e)
      }
    } finally {
      closingLegId.value = null
    }
  }
  ```

- Update Close Strategy button in template:
  ```vue
  <el-button
    type="danger"
    size="small"
    :loading="closingStrategy"
    @click="handleCloseStrategy"
  >
    {{ closingStrategy ? 'Closing...' : 'Close Strategy' }}
  </el-button>
  ```

- Update Close Leg button in template:
  ```vue
  <el-button
    class="close-leg-btn"
    size="small"
    type="danger"
    plain
    :loading="closingLegId === row.id"
    @click="handleCloseLeg(row)"
  >
    {{ closingLegId === row.id ? 'Closing...' : 'Close Leg' }}
  </el-button>
  ```

### 7. Validate Implementation
- Start backend and frontend servers
- Verify endpoints appear in API docs at `/docs`
- Test with paper trading account
- Verify confirmation dialogs appear
- Verify loading states work
- Verify position refreshes after close
- Tail backend logs to monitor operations

## Testing Strategy

### Backend Testing
1. **Unit Tests**: Add tests to `test_alpaca_service.py`:
   - Test `_determine_close_side()` returns correct side
   - Test `close_leg()` with mock TradingClient
   - Test `close_strategy()` handles partial failures

2. **Integration Tests**: Add endpoint tests:
   - Test 404 for non-existent position
   - Test successful close with mock service
   - Test error handling

### Frontend Testing
1. **Component Tests**:
   - Verify confirmation dialog appears on button click
   - Verify loading state activates during API call
   - Verify success/error messages display correctly

2. **E2E Tests** (with Playwright):
   - Click close strategy button
   - Confirm dialog
   - Verify position list updates

## Acceptance Criteria
- [ ] "Close Strategy" button opens confirmation dialog before closing
- [ ] "Close Leg" button opens confirmation dialog before closing
- [ ] Loading spinners show during close operations
- [ ] Success message displays on successful close
- [ ] Error message displays on failed close
- [ ] Position list refreshes automatically after close
- [ ] Backend logs all close operations with full details
- [ ] Circuit breaker protects against API failures
- [ ] Paper trading mode is respected (ALPACA_PAPER config)

## Validation Commands
Execute these commands to validate the task is complete:

- `cd apps/orchestrator_3_stream/backend && uv run python -m py_compile modules/alpaca_service.py modules/alpaca_models.py main.py` - Verify Python files compile
- `cd apps/orchestrator_3_stream/frontend && npm run type-check` - Verify TypeScript types
- `cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_service.py -v` - Run backend tests
- `curl -X POST http://localhost:8002/api/positions/test-id/close-strategy -H "Content-Type: application/json" -d '{"position_id": "test-id"}'` - Test endpoint exists (will return error for invalid position, but confirms route works)

## Notes

### Alpaca SDK Order Submission
The Alpaca SDK uses synchronous methods, so we wrap them with `asyncio.run_in_executor()` following the existing pattern in `get_all_positions()`.

### Order Types
- **Market Orders** (default): Execute immediately at best available price
- **Limit Orders** (future enhancement): Allow specifying price offset from mid

### Safety Considerations
- Always verify `ALPACA_PAPER=true` in `.env` for testing
- Confirmation dialogs prevent accidental closes
- Full logging enables audit trail
- Circuit breaker prevents cascading failures

### WebSocket Broadcasting
After successful close, broadcast position update via WebSocket so all connected clients see the change immediately.
