# Plan: Fix OptionDataStream Async Handler Pattern

## Task Description
Fix the OptionDataStream quote handler in `alpaca_service.py` to use async handler pattern instead of the broken sync handler with thread bridging. The current implementation causes option quotes to stop flowing after initial subscription.

## Objective
Option quotes should stream continuously through the backend WebSocket, matching the behavior of spot price quotes which already work correctly.

## Problem Statement
The `alpaca_service.py` file uses a synchronous handler with `run_coroutine_threadsafe()` bridging (lines 354-372) to handle option quotes. However, the Alpaca SDK now requires async coroutine handlers. This causes:
1. Option quotes appear briefly at startup then stop
2. "[SYNC HANDLER] Quote received" log messages stop appearing
3. "connection limit exceeded" errors when attempting new connections

## Solution Approach
Update `alpaca_service.py` to match the working async handler pattern used in `spot_price_service.py`:
1. Replace the sync handler with an async handler
2. Remove the `_main_loop` storage and thread bridging logic
3. Keep the existing `_handle_quote_update()` method unchanged (already async)

## Relevant Files
Use these files to complete the task:

- **backend/modules/alpaca_service.py** (lines 349-372) - Contains the broken sync handler pattern that needs to be replaced with async pattern
- **backend/modules/spot_price_service.py** (lines 125-130) - Reference implementation showing the correct async handler pattern

## Step by Step Tasks

### 1. Remove Thread Bridging Infrastructure
- Delete line 139: `self._main_loop: Optional[asyncio.AbstractEventLoop] = None` from `__init__`
- Delete lines 349-350: The `_main_loop` storage in `start_price_streaming()`

### 2. Replace Sync Handler with Async Handler
Replace lines 354-372 (the sync handler block):

**Current (BROKEN):**
```python
# CRITICAL FIX: Use synchronous handler that bridges to main event loop
# stream.run() creates its own event loop in a thread, so async handlers
# won't work directly. We use run_coroutine_threadsafe to bridge back.
def sync_quote_handler(quote: Any) -> None:
    """Synchronous wrapper that safely bridges to async handler"""
    logger.debug(f"[SYNC HANDLER] Quote received for {quote.symbol}")
    try:
        # Schedule the async handler on the main event loop
        future = asyncio.run_coroutine_threadsafe(
            self._handle_quote_update(quote),
            self._main_loop
        )
        # Wait for completion with timeout (don't block too long)
        future.result(timeout=5.0)
    except Exception as e:
        logger.error(f"[SYNC HANDLER] Error bridging quote to async handler: {e}")

# Subscribe to quotes for new symbols
stream.subscribe_quotes(sync_quote_handler, *new_symbols)
```

**New (FIXED):**
```python
# Register async quote handler (Alpaca SDK requires coroutine handlers)
async def quote_handler(quote: Any) -> None:
    await self._handle_quote_update(quote)

# Subscribe to quotes for new symbols
stream.subscribe_quotes(quote_handler, *new_symbols)
```

### 3. Update Diagnostic Log Message (Optional)
In `_handle_quote_update()` at line 409, update the log message to remove "[SYNC HANDLER]" reference since we're now using async:

```python
# Before
logger.info(f"[OPTION QUOTE RECEIVED] {quote.symbol}: bid={quote.bid_price}, ask={quote.ask_price}")

# No change needed - this message is already correct
```

### 4. Validate the Fix
- Restart the backend
- Open the frontend with positions
- Check logs for continuous `[OPTION QUOTE RECEIVED]` messages
- Verify option prices update in the UI

## Acceptance Criteria
- [ ] Option quotes stream continuously after subscription (not just at startup)
- [ ] `[OPTION QUOTE RECEIVED]` log messages appear continuously in logs
- [ ] No "connection limit exceeded" errors during normal operation
- [ ] Spot price streaming continues to work (no regression)
- [ ] Frontend receives and displays option price updates

## Validation Commands
Execute these commands to validate the task is complete:

1. **Restart backend and check logs:**
```bash
# Stop existing backend
lsof -ti:9403 | xargs kill -9 2>/dev/null

# Start backend
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_be.sh &

# Wait for startup, then check for option quotes in logs
sleep 10 && grep -E "\[OPTION QUOTE RECEIVED\]" backend/logs/$(date +%Y-%m-%d)_*.log | tail -20
```

2. **Run diagnostic script (after stopping backend):**
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run python tmp_scripts/test_option_stream.py
```

3. **Check for continuous quotes over time:**
```bash
# Watch for new option quotes (should appear continuously)
tail -f /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/logs/$(date +%Y-%m-%d)_*.log | grep "OPTION QUOTE"
```

## Notes
- The fix is minimal - only 2 locations need changes in `alpaca_service.py`
- The `_handle_quote_update()` method is already async and doesn't need changes
- The `_run_stream()` method using `run_in_executor()` is correct and doesn't need changes
- This aligns with how `spot_price_service.py` handles stock quotes (which works)
