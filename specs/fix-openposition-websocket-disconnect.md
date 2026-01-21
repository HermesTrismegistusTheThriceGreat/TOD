# Plan: Fix OpenPositionCard WebSocket Disconnection and P&L Updates

## Task Description

The OpenPositionCard.vue component shows "Disconnected" status indicator even when the WebSocket is active and receiving data. P&L values are not updating regularly via the WebSocket price stream. This plan troubleshoots the root causes and implements fixes for both the connection status display and the price streaming reliability.

## Objective

When this plan is complete:
1. The connection status indicator accurately reflects the Alpaca price stream state
2. P&L values update in real-time as prices stream from Alpaca
3. WebSocket reconnection logic handles disconnections gracefully
4. Status mapping between backend and frontend is consistent

## Problem Statement

Based on expert analysis and codebase scouting:

### Root Cause #1: Status String Mismatch

**Backend broadcasts:** `'streaming_started'`, `'streaming_stopped'`, `'spot_streaming_started'`, `'spot_streaming_stopped'`

**Frontend expects:** `'connected' | 'disconnected' | 'error'`

The `setAlpacaConnectionStatus()` function (orchestratorStore.ts:525-526) only accepts `'connected' | 'disconnected' | 'error'`, but the backend sends different status strings like `'streaming_started'`. This causes the status to remain at initial value `'disconnected'` or potentially set an invalid value.

### Root Cause #2: No WebSocket Reconnection Logic

The chatService.ts WebSocket implementation (lines 299-307) only logs disconnections and calls callbacks - there is no automatic reconnection with exponential backoff. Network interruptions cause permanent loss of price updates until manual page refresh.

### Root Cause #3: No Re-subscription After Reconnect

The `useAlpacaPositions` composable sets `isSubscribed.value = true` after initial subscription. If the WebSocket reconnects, the backend doesn't remember previous subscriptions, but the frontend guard prevents re-subscription.

### Root Cause #4: Heartbeat Not Scheduled

The backend has a `send_heartbeat()` method (websocket_manager.py:372-380) but it's never called periodically. This prevents detecting stale/zombie connections.

## Solution Approach

1. **Add status mapping** in the frontend to translate backend status strings to expected values
2. **Implement WebSocket reconnection** with exponential backoff
3. **Reset subscription state** on reconnection to allow re-subscription
4. **Set connection status to 'connected'** when price updates are received (infer connection health from data flow)

## Relevant Files

### Frontend Files to Modify
- `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts` (Lines 135, 525-527, 975-978) - Add status mapping, reconnection logic
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts` (Lines 129-154) - Reset subscription on reconnect
- `apps/orchestrator_3_stream/frontend/src/services/chatService.ts` (Lines 299-319) - Add reconnection with backoff

### Frontend Files for Reference
- `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` (Lines 35, 324-327) - Displays connection status
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts` (Line 22) - Exposes connectionStatus

### Backend Files for Reference
- `apps/orchestrator_3_stream/backend/modules/spot_price_service.py` (Lines 140-143, 217) - Broadcasts status strings
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` (Lines 362-366, 443) - Broadcasts status strings
- `apps/orchestrator_3_stream/backend/modules/websocket_manager.py` (Lines 342-356, 372-380) - Status broadcast method, heartbeat method

## Implementation Phases

### Phase 1: Quick Fix - Status Mapping
Add status mapping in the frontend store to translate backend statuses to expected values.

### Phase 2: Reconnection Logic
Implement WebSocket auto-reconnection with exponential backoff.

### Phase 3: Subscription Recovery
Reset subscription state and re-subscribe after WebSocket reconnects.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Add Status Mapping in orchestratorStore.ts

In `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`:

- Locate the `onAlpacaStatus` handler around line 975-978
- Add a status mapping object to translate backend statuses to frontend-expected values
- Update the handler to use the mapping

```typescript
// Add this status mapping object near the top of the connectWebSocket function or as a module-level constant
const ALPACA_STATUS_MAP: Record<string, 'connected' | 'disconnected' | 'error'> = {
  'connected': 'connected',
  'streaming_started': 'connected',
  'spot_streaming_started': 'connected',
  'disconnected': 'disconnected',
  'streaming_stopped': 'disconnected',
  'spot_streaming_stopped': 'disconnected',
  'error': 'error',
}

// Update the onAlpacaStatus handler
onAlpacaStatus: (message: any) => {
  if (message.status) {
    const mappedStatus = ALPACA_STATUS_MAP[message.status] || 'disconnected'
    setAlpacaConnectionStatus(mappedStatus)
  }
},
```

### 2. Add Connection Status Inference from Price Updates

In `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`:

- Update `onOptionPriceUpdate` and `onSpotPriceUpdate` handlers to set connection status to 'connected' when receiving data
- This provides real-time connection health feedback based on actual data flow

```typescript
onOptionPriceUpdate: (message: any) => {
  if (message.update) {
    const update = transformPriceUpdate(message.update)
    updateAlpacaPrice(update.symbol, update)
    // Infer connected status from receiving price data
    if (alpacaConnectionStatus.value !== 'connected') {
      setAlpacaConnectionStatus('connected')
    }
  }
},
onSpotPriceUpdate: (message: any) => {
  if (message.update) {
    const update = transformSpotPriceUpdate(message.update)
    updateSpotPrice(update.symbol, update)
    // Infer connected status from receiving price data
    if (alpacaConnectionStatus.value !== 'connected') {
      setAlpacaConnectionStatus('connected')
    }
  }
},
```

### 3. Implement WebSocket Reconnection in chatService.ts

In `apps/orchestrator_3_stream/frontend/src/services/chatService.ts`:

- Add reconnection state tracking (attempt counter, timeout reference)
- Implement exponential backoff reconnection in `onclose` handler
- Add configuration constants for max retries and base delay
- Provide a way to distinguish manual disconnect from unexpected disconnect

```typescript
// Add reconnection configuration at module level
const RECONNECT_CONFIG = {
  maxAttempts: 5,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
}

// Add reconnection state
let reconnectAttempts = 0
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let isManualDisconnect = false

// Update connectWebSocket to accept reconnection callback
export function connectWebSocket(
  url: string,
  callbacks: WebSocketCallbacks,
  onReconnect?: () => void // New parameter for reconnection hook
): WebSocket {
  const ws = new WebSocket(url)

  // Reset reconnect attempts on successful connection
  ws.onopen = () => {
    reconnectAttempts = 0
    isManualDisconnect = false
    console.log('WebSocket connected')
    callbacks.onConnected?.()
    onReconnect?.() // Call reconnection hook if this is a reconnection
  }

  // ... existing onmessage handler ...

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    callbacks.onError(error)
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected')
    callbacks.onDisconnected?.()

    // Only attempt reconnection if not manually disconnected
    if (!isManualDisconnect && reconnectAttempts < RECONNECT_CONFIG.maxAttempts) {
      const delay = Math.min(
        RECONNECT_CONFIG.baseDelayMs * Math.pow(2, reconnectAttempts),
        RECONNECT_CONFIG.maxDelayMs
      )
      reconnectAttempts++
      console.log(`Attempting reconnection ${reconnectAttempts}/${RECONNECT_CONFIG.maxAttempts} in ${delay}ms`)

      reconnectTimeout = setTimeout(() => {
        connectWebSocket(url, callbacks, onReconnect)
      }, delay)
    } else if (reconnectAttempts >= RECONNECT_CONFIG.maxAttempts) {
      console.error('Max reconnection attempts reached')
      // Optionally notify via callback
    }
  }

  return ws
}

// Update disconnect function to set manual flag
export function disconnect(ws: WebSocket) {
  isManualDisconnect = true
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
  ws.close()
}
```

### 4. Add Re-subscription Hook in orchestratorStore.ts

In `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`:

- Add a callback parameter to `connectWebSocket` for handling reconnection
- Emit an event or call a function that triggers re-subscription

```typescript
// Add reconnection state
let needsResubscription = false

function connectWebSocket() {
  // ... existing cleanup code ...

  try {
    wsConnection = chatService.connectWebSocket(wsUrl, {
      // ... existing callbacks ...
      onDisconnected: () => {
        isConnected.value = false
        setAlpacaConnectionStatus('disconnected')
        needsResubscription = true // Mark for re-subscription
        console.log('WebSocket disconnected')
      }
    }, () => {
      // Reconnection callback - triggered after successful reconnect
      if (needsResubscription) {
        needsResubscription = false
        // Emit custom event for composables to re-subscribe
        window.dispatchEvent(new CustomEvent('alpaca-reconnect'))
      }
    })
  } catch (error) {
    console.error('Failed to connect WebSocket:', error)
  }
}
```

### 5. Listen for Reconnection in useAlpacaPositions.ts

In `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`:

- Add event listener for reconnection event
- Reset `isSubscribed` flag on reconnection
- Call `subscribeToUpdates()` again after reconnection

```typescript
// Add inside the composable setup
import { onMounted, onUnmounted, ref } from 'vue'

// ... existing code ...

// Listen for reconnection events to re-subscribe
function handleReconnect() {
  console.log('WebSocket reconnected, re-subscribing to price updates')
  isSubscribed.value = false
  subscribeToUpdates()
}

onMounted(() => {
  window.addEventListener('alpaca-reconnect', handleReconnect)
})

onUnmounted(() => {
  window.removeEventListener('alpaca-reconnect', handleReconnect)
})
```

### 6. Verify Price Update Flow

After implementing the above changes:
- Start the orchestrator backend and frontend
- Open OpenPositionCard and verify:
  - Status indicator shows "Connected" when streaming starts
  - P&L values update in real-time
  - Disconnecting network briefly triggers reconnection
  - After reconnection, prices resume updating

### 7. Test Edge Cases

- Test with network throttling (DevTools)
- Test rapid connect/disconnect cycles
- Test when backend restarts (should reconnect automatically)
- Test when Alpaca API is unavailable (should show 'error' status)

## Testing Strategy

### Unit Tests
- Test status mapping function with all backend status strings
- Test exponential backoff calculation
- Test reconnection state management

### Integration Tests
- Test WebSocket reconnection after simulated disconnect
- Test re-subscription after reconnection
- Test status indicator reflects correct state

### Manual Tests
- Open DevTools, throttle network to "Offline", verify "Disconnected" shows
- Restore network, verify reconnection and "Connected" status
- Verify P&L updates after reconnection
- Test with multiple browser tabs

## Acceptance Criteria

1. Connection status shows "Connected" (green) when price streaming is active
2. Connection status shows "Disconnected" (amber) when stream is inactive
3. P&L values update within 200ms of price changes during market hours
4. WebSocket automatically reconnects after network interruption
5. Price subscriptions resume after reconnection
6. Status changes reflect actual data flow, not just connection events
7. No memory leaks from reconnection timeout handling

## Validation Commands

Execute these commands to validate the task is complete:

- `cd apps/orchestrator_3_stream/frontend && npm run type-check` - Verify TypeScript compiles
- `cd apps/orchestrator_3_stream/frontend && npm run build` - Verify production build succeeds
- Manual: Start orchestrator and verify status shows "Connected" when receiving prices
- Manual: Disconnect network, verify "Disconnected" status, reconnect, verify "Connected"

## Notes

### WebSocket Expert Consultation Summary
- Current WebSocket architecture is sound (centralized WebSocketManager, write-through persistence)
- Known issue: Heartbeat scheduling not implemented (send_heartbeat exists but unused)
- Recommendation: Status mapping is safest fix (no backend changes required)

### Alpaca Expert Consultation Summary
- Elite subscription supports StockDataStream for spot prices
- Rate limiting (200ms throttle) is appropriate for Elite tier
- WebSocket endpoints: `wss://stream.data.alpaca.markets/v2/sip` for production

### Backend Status Strings Reference
From codebase analysis, backend broadcasts these status strings:
- `spot_streaming_started` - SpotPriceStreamService started successfully
- `spot_streaming_stopped` - SpotPriceStreamService stopped
- `streaming_started` - AlpacaService option streaming started
- `streaming_stopped` - AlpacaService option streaming stopped
- `strategy_closed` - Position strategy was closed

### Alternative Approach (Not Recommended)
Could modify backend to send `'connected'` instead of `'streaming_started'`, but this would:
- Require backend deployment
- Potentially break other consumers expecting current status strings
- The frontend mapping approach is safer and more flexible
