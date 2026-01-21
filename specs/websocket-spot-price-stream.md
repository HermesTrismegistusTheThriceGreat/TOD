# Plan: WebSocket Spot Price Stream for OpenPositionCard

## Task Description

Create a real-time WebSocket stream for displaying the spot (underlying) price on the OpenPositionCard.vue component. Currently, the spot price is hardcoded as `$421.37` (line 313). This plan implements a live price stream using Alpaca's `StockDataStream` WebSocket API with an Elite subscription, integrated with the existing WebSocket infrastructure.

## Objective

When this plan is complete, the OpenPositionCard.vue component will display a live, real-time spot price for the underlying ticker (e.g., SPY) that updates via WebSocket streaming. The implementation will:
1. Subscribe to Alpaca's stock quote WebSocket stream
2. Broadcast spot price updates through the existing WebSocket manager
3. Update the frontend component to display live prices

## Problem Statement

The OpenPositionCard.vue component currently displays a hardcoded spot price (`$421.37` at line 313 in the template), which does not reflect the actual current market price. For options traders, the underlying spot price is critical for:
- Evaluating position risk relative to strikes
- Making timely exit/adjustment decisions
- Understanding real-time P/L implications

## Solution Approach

Use Alpaca's `StockDataStream` WebSocket API (available with Elite subscription) to stream real-time stock quotes. The solution integrates with the existing WebSocket architecture:

1. **Backend**: Create a new `SpotPriceStreamService` that connects to Alpaca's `StockDataStream` and broadcasts spot price updates via the existing `WebSocketManager`
2. **Frontend**: Extend the existing Alpaca price stream composables and store to handle spot price updates
3. **Component**: Update OpenPositionCard.vue to use reactive spot price data instead of hardcoded value

**Key Architecture Decision**: Mirror the existing `OptionDataStream` pattern in `alpaca_service.py` for consistency and reuse the rate limiter/circuit breaker patterns.

## Relevant Files

Use these files to complete the task:

### Backend Files
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` (Lines 22-46, 327-420) - Existing Alpaca service with OptionDataStream pattern to mirror
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Add new SpotPriceUpdate Pydantic model
- `apps/orchestrator_3_stream/backend/modules/websocket_manager.py` (Lines 280-294) - Add new broadcast method for spot prices
- `apps/orchestrator_3_stream/backend/modules/config.py` (Lines 186-214) - Alpaca config already present
- `apps/orchestrator_3_stream/backend/main.py` (Lines 83-248) - Service initialization in lifespan

### Frontend Files
- `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` (Lines 46, 312-314) - Component with hardcoded spot price
- `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts` (Lines 114-123) - OpenPosition interface (missing spotPrice field)
- `apps/orchestrator_3_stream/frontend/src/services/chatService.ts` (Lines 12-58, 111-143) - WebSocket callback interface
- `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts` (Lines 931-958) - WebSocket event handlers
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts` - Price stream composable to extend

### New Files
- `apps/orchestrator_3_stream/backend/modules/spot_price_service.py` - New service for stock price streaming

### Documentation References
- `alpaca_docs/streaming-market-data.md` - WebSocket stream format and subscription
- `alpaca_docs/alpaca-py-github-readme.md` (Line 103) - StockDataStream client reference
- `.claude/commands/experts/alpaca/expertise.yaml` (Lines 372-444) - WebSocket streaming patterns
- `.claude/commands/experts/websocket/expertise.yaml` - Existing WebSocket architecture

## Implementation Phases

### Phase 1: Foundation
- Create Pydantic models for spot price data
- Add configuration constants for stock data feed
- Create backend spot price service skeleton

### Phase 2: Core Implementation
- Implement `SpotPriceStreamService` with `StockDataStream` integration
- Add WebSocket manager broadcast method for spot prices
- Add frontend TypeScript types and WebSocket handlers
- Update Pinia store with spot price cache

### Phase 3: Integration & Polish
- Wire up OpenPositionCard.vue to use reactive spot price
- Add connection status and loading states
- Test end-to-end flow
- Handle error cases and reconnection

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Add Spot Price Pydantic Model

In `apps/orchestrator_3_stream/backend/modules/alpaca_models.py`:
- Add `SpotPriceUpdate` model with fields: `symbol`, `bid_price`, `ask_price`, `mid_price`, `last_price`, `timestamp`
- Follow the existing `OptionPriceUpdate` pattern (lines 44-55)

### 2. Create SpotPriceStreamService Backend Module

Create new file `apps/orchestrator_3_stream/backend/modules/spot_price_service.py`:
- Import `StockDataStream` from `alpaca.data.live`
- Create `SpotPriceStreamService` class mirroring `AlpacaService` pattern
- Implement `start_spot_streaming(symbols: List[str])` method
- Use existing circuit breaker and rate limiter
- Add quote handler to transform and broadcast updates
- Include `shutdown()` method for cleanup

```python
# Key imports
from alpaca.data.live import StockDataStream

class SpotPriceStreamService:
    def __init__(self):
        self._stock_stream: Optional[StockDataStream] = None
        self._subscribed_symbols: Set[str] = set()
        self._ws_manager = None
        self._rate_limiter = RateLimiter(...)

    async def start_spot_streaming(self, symbols: List[str]) -> None:
        """Subscribe to real-time stock quotes"""
        stream = self._get_stock_stream()
        stream.subscribe_quotes(self._quote_handler, *symbols)
        # ...
```

### 3. Add WebSocket Broadcast Method for Spot Prices

In `apps/orchestrator_3_stream/backend/modules/websocket_manager.py`:
- Add `broadcast_spot_price_update(update_data: dict)` method after line 294
- Use event type `"spot_price_update"`
- Include rate limiter integration like `broadcast_option_price_update`

### 4. Initialize Service in FastAPI Lifespan

In `apps/orchestrator_3_stream/backend/main.py`:
- Import the new service: `from modules.spot_price_service import SpotPriceStreamService, init_spot_price_service, get_spot_price_service`
- Add initialization in lifespan startup (around line 200):
  ```python
  spot_price_service = await init_spot_price_service(app)
  spot_price_service.set_websocket_manager(ws_manager)
  ```
- Add shutdown in lifespan cleanup (around line 240)

### 5. Add REST Endpoint for Spot Price Subscription

In `apps/orchestrator_3_stream/backend/main.py`:
- Add endpoint `POST /api/positions/subscribe-spot-prices`
- Accept `{ "symbols": ["SPY", "QQQ"] }` body
- Call `spot_price_service.start_spot_streaming(symbols)`
- Return subscription confirmation

### 6. Add Frontend TypeScript Types

In `apps/orchestrator_3_stream/frontend/src/services/chatService.ts`:
- Add `SpotPriceUpdateMessage` interface (lines 12-58):
  ```typescript
  export interface SpotPriceUpdateMessage {
    type: 'spot_price_update'
    update: {
      symbol: string
      bid_price: number
      ask_price: number
      mid_price: number
      last_price?: number
      timestamp: string
    }
    timestamp: string
  }
  ```
- Add `onSpotPriceUpdate` to `WebSocketCallbacks` interface (line 139)

### 7. Add WebSocket Message Router Case

In `apps/orchestrator_3_stream/frontend/src/services/chatService.ts`:
- Add case in switch statement (around line 263):
  ```typescript
  case 'spot_price_update':
    callbacks.onSpotPriceUpdate?.(message as SpotPriceUpdateMessage)
    break
  ```

### 8. Add Spot Price State to Pinia Store

In `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`:
- Add `spotPriceCache` state: `const spotPriceCache = shallowRef<Map<string, SpotPriceUpdate>>(new Map())`
- Add `updateSpotPrice(symbol: string, update: SpotPriceUpdate)` action
- Add getter `getSpotPrice(symbol: string): SpotPriceUpdate | undefined`
- Wire up WebSocket handler in `connectWebSocket`:
  ```typescript
  onSpotPriceUpdate: (message: any) => {
    if (message.update) {
      const update = transformSpotPriceUpdate(message.update)
      updateSpotPrice(update.symbol, update)
    }
  },
  ```

### 9. Update OpenPosition Type with SpotPrice

In `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`:
- Add `spot_price?: number` to `RawOpenPosition` (line 29-38)
- Add `spotPrice?: number` to `OpenPosition` (line 114-123)
- Update `transformPosition` to map `spotPrice: raw.spot_price`

### 10. Extend useAlpacaPriceStream Composable

In `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts`:
- Add `getSpotPrice(symbol: string): number | undefined` function
- Add computed property for spot price cache
- Export alongside existing getMidPrice

### 11. Update useAlpacaPositions to Subscribe Spot Prices

In `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`:
- After calling `alpacaService.subscribePrices(symbols)`, also call for spot prices
- Extract unique underlying tickers from positions
- Call `alpacaService.subscribeSpotPrices(underlyingSymbols)`

### 12. Add subscribeSpotPrices API Call

In `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts`:
- Add `subscribeSpotPrices(symbols: string[])` function
- POST to `/api/positions/subscribe-spot-prices`

### 13. Update OpenPositionCard.vue Template

In `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`:
- Import `getSpotPrice` from `useAlpacaPriceStream` composable
- Create computed property for spot price:
  ```typescript
  const spotPrice = computed(() => {
    if (!position.value) return null
    return getSpotPrice(position.value.ticker)?.midPrice ?? position.value.spotPrice
  })
  ```
- Replace hardcoded `$421.37` at line 313 with:
  ```vue
  <span class="spot-value">{{ spotPrice ? formatPrice(spotPrice) : '--' }}</span>
  ```

### 14. Add Loading/Error States for Spot Price

In `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`:
- Add visual indicator when spot price is loading (no data yet)
- Show "--" or skeleton while awaiting first update
- Optionally add subtle animation on price change

### 15. Validate Implementation with Playwright

Use the playwright-validator agent to:
- Verify spot price displays and updates in OpenPositionCard
- Test WebSocket connection status
- Verify price updates flow through correctly

## Testing Strategy

### Unit Tests
- Test `SpotPriceUpdate` model serialization/deserialization
- Test rate limiter with spot price updates
- Test frontend transform functions

### Integration Tests
- Test WebSocket broadcast reaches connected clients
- Test subscription endpoint correctly starts streaming
- Test store updates and computed properties react

### End-to-End Tests
- Use Playwright to verify price displays in UI
- Test reconnection scenarios
- Test with multiple positions/tickers

### Manual Testing
- Connect to paper trading and verify real-time updates
- Test with market closed (should show last available)
- Test error handling when API unavailable

## Acceptance Criteria

1. OpenPositionCard.vue displays a live spot price instead of `$421.37`
2. Spot price updates in real-time via WebSocket (within 200ms of market data)
3. Connection status indicator reflects spot price stream status
4. Spot price shows loading state before first update
5. Backend handles multiple underlying symbols (SPY, QQQ, etc.)
6. Rate limiting prevents excessive WebSocket broadcasts
7. Error handling for API failures with graceful degradation
8. Spot price subscription triggered automatically when positions load

## Validation Commands

Execute these commands to validate the task is complete:

- `uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/spot_price_service.py` - Verify new service compiles
- `uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Verify models compile
- `cd apps/orchestrator_3_stream/frontend && npm run type-check` - Verify TypeScript types
- `cd apps/orchestrator_3_stream/frontend && npm run build` - Verify frontend builds
- `cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_spot_price_service.py -v` - Run spot price service tests
- Manual: Start orchestrator and verify spot price updates in OpenPositionCard

## Notes

### Alpaca StockDataStream Usage
With Elite subscription, use the `StockDataStream` class from `alpaca.data.live`:
```python
from alpaca.data.live import StockDataStream

stream = StockDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)
stream.subscribe_quotes(quote_handler, "SPY", "QQQ")
await stream.run()  # Blocking call - run in executor
```

### WebSocket Endpoint for Market Data
Per Alpaca docs, stock data streams connect to:
- Production: `wss://stream.data.alpaca.markets/v2/sip` (SIP feed for Elite)
- Paper: `wss://stream.data.sandbox.alpaca.markets/v2/test`

### Rate Limiting Consideration
With Elite subscription, API rate limits are 1000 calls/minute. However, WebSocket updates can be high-frequency during market hours. Use the existing `RateLimiter` with 200ms throttle for broadcasts.

### Dependencies
- No new dependencies required - `alpaca-py` already installed and includes `StockDataStream`
- Uses existing `asyncio`, `pydantic`, and WebSocket infrastructure

### Potential Enhancements (Out of Scope)
- Batch multiple spot price updates in single broadcast
- Add historical intraday chart data
- Show price change percentage from open
- Add volume indicator
