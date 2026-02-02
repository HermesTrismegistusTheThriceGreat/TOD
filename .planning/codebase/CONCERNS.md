# Technical Concerns

## Technical Debt
- **Broad Exception Handling** - `alpaca_agent_service.py`, `main.py` - Catch-all blocks mask specific errors
- **Async Tasks Without Tracking** - `main.py`, `agent_manager.py` - Background tasks not awaited
- **Cache Without Eviction** - `alpaca_service.py` - Manual eviction could allow memory growth

## Known Issues
- **File Parent Detection Incomplete** - `FileTreeView.vue:88,105` - TODO stub
- **Modal Creation Unimplemented** - `App.vue:153` - TODO feature
- **Stream Reconnect Logic Missing** - `alpaca_service.py`, `spot_price_service.py`

## Security Considerations
- **MCP Credential Handling** - Credentials via env vars could leak in process listings
- **IDE Command Path Validation** - No path normalization for directory traversal
- **Database URL Logging** - Credentials logged at startup

## Performance
- **N+1 Query on Agent Enrichment** - `main.py:811-819` - Should use GROUP BY
- **Event Sorting in Python** - Should sort in SQL with indexes
- **Price Update Broadcast Frequency** - No batching for high-frequency updates

## Fragile Areas
- **WebSocket Error Handling** - Connection failures during send
- **Database Pool Race Condition** - No lock on initialization
- **Circuit Breaker State** - Side effects in property getter

## TODOs Found
- `FileTreeView.vue:88` - TODO: Find actual parent of file
- `FileTreeView.vue:105` - TODO: Find actual parent of file
- `App.vue:153` - TODO: Open modal to create new agent
