# ISO-03 WebSocket Filtering Analysis

**Date:** 2026-02-01
**Plan:** 08-03
**Requirement:** ISO-03 - WebSocket updates filtered by account ownership

## Executive Summary

**STATUS: NOT IMPLEMENTED - Gap Identified**

The current WebSocket implementation broadcasts all events to all connected clients without any user or account-level filtering. This is a data isolation vulnerability for multi-tenant trading applications.

## Current Implementation

### WebSocket Connection (main.py:896-997)

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates and chat messages"""

    await ws_manager.connect(websocket)
    # No authentication or user context captured
```

**Issue:** WebSocket connections are accepted without any authentication or user identification.

### WebSocket Manager (websocket_manager.py)

The `WebSocketManager` class stores connections in a flat list:

```python
def __init__(self):
    self.active_connections: List[WebSocket] = []
    self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
```

The `connect()` method only stores a generic `client_id`:

```python
async def connect(self, websocket: WebSocket, client_id: str = None):
    client_id = client_id or f"client_{len(self.active_connections)}"
    self.connection_metadata[websocket] = {
        "client_id": client_id,
        "connected_at": datetime.now().isoformat(),
    }
```

**Issue:** No `user_id` or `account_id` is captured or associated with the connection.

### Broadcasting Behavior

All broadcast methods send to ALL connected clients:

```python
async def broadcast(self, data: dict, exclude: WebSocket = None):
    """Broadcast JSON data to all connected clients (except optionally one)"""
    for connection in self.active_connections:
        if connection == exclude:
            continue
        try:
            await connection.send_json(data)
```

**Issue:** No filtering by user ownership or account association.

### Trading Data Broadcasts

Position updates and price updates are broadcast without filtering:

```python
# websocket_manager.py:332
async def broadcast_position_update(self, position_data: dict):
    """Broadcast position update (e.g., after order fill)."""
    await self.broadcast({
        "type": "position_update",
        "position": position_data,
        "timestamp": datetime.now().isoformat()
    })

# alpaca_service.py:469
await self._ws_manager.broadcast_option_price_update(data)
```

**Issue:** Position and price updates are sent to ALL clients, not just the account owner.

## Security Implications

### For Multi-Tenant Trading Application

In a trading application like this (Alpaca integration), broadcasting position and account updates to all users means:

1. **User A can see User B's positions** via WebSocket
2. **User A can see User B's order fills** via WebSocket
3. **User A can see User B's account balance changes** via WebSocket
4. **Cross-user data leakage** violates ISO-03 requirement

### Current Mitigations

The REST API endpoints ARE properly secured:
- `/alpaca-agent/positions` requires authentication and filters by `credential_id`
- All credential operations use RLS policies (when BYPASSRLS is fixed)
- Frontend only requests data for the active credential

**However**, the WebSocket layer bypasses all of these protections by broadcasting to everyone.

## Gap Analysis

### What's Missing

1. **No WebSocket authentication** - No way to identify which user owns a connection
2. **No connection-to-user mapping** - Can't filter broadcasts by user
3. **No credential-aware broadcasts** - Can't target specific account owners
4. **No frontend filtering** - Client receives all updates and must filter (insecure)

### Required Changes

To implement ISO-03 properly:

1. **WebSocket Authentication:**
   ```python
   @app.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
       # Validate token and extract user_id
       user = await get_user_from_token(token)
       await ws_manager.connect(websocket, user_id=user.id)
   ```

2. **Connection Metadata:**
   ```python
   self.connection_metadata[websocket] = {
       "client_id": client_id,
       "user_id": user_id,  # NEW
       "account_ids": [],   # NEW - list of account IDs user can access
       "connected_at": datetime.now().isoformat(),
   }
   ```

3. **Filtered Broadcasting:**
   ```python
   async def broadcast_position_update(self, position_data: dict, user_id: str):
       """Broadcast position update ONLY to the account owner"""
       for connection in self.active_connections:
           metadata = self.connection_metadata.get(connection, {})
           if metadata.get("user_id") == user_id:
               await connection.send_json(data)
   ```

4. **Caller Responsibility:**
   ```python
   # alpaca_service.py
   await self._ws_manager.broadcast_position_update(
       position_data=data,
       user_id=self.current_user_id  # Must be passed in
   )
   ```

## Workaround: Frontend-Side Filtering

The frontend COULD filter WebSocket events client-side:

```typescript
// In store/accountStore.ts or similar
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'position_update') {
    // Only process if it matches our active credential
    if (message.position.credential_id === activeCredentialId.value) {
      // Update UI
    }
  }
}
```

**However, this is NOT secure:**
- User still receives other users' data over the wire
- Malicious user can inspect network traffic and see others' positions
- Violates principle of least privilege
- Does not satisfy ISO-03 requirement

## Recommendation

**Priority: HIGH (but not blocking for mobile polish phase)**

This is a **data isolation vulnerability** but:
- Not specific to mobile (affects all clients)
- Not a new regression (existed before Phase 8)
- REST API is properly secured (primary data path)
- WebSocket is supplementary (UI updates, not primary data fetch)

**Action Plan:**

1. **Phase 8 (Mobile Polish):** Document this gap but DO NOT block completion
2. **Post-Phase 8:** Create todo for "Phase 7.5: WebSocket Isolation"
3. **Implementation:** Add user authentication to WebSocket connections and filtered broadcasting

**Estimated Effort:** 2-3 hours (authentication + filtered broadcast methods)

## Related Issues

- **BYPASSRLS Issue:** Also affects REST API, separate from WebSocket gap
- **07-02 RLS Verification:** Verified REST API isolation, but WebSocket was not in scope

## Testing ISO-03 (Human Verification)

Since WebSocket filtering is NOT implemented, we cannot verify ISO-03 compliance in this plan.

**What CAN be tested:**
- REST API endpoints properly filter by credential_id ✓ (verified in 07-03)
- Frontend only requests data for active credential ✓ (verified in 07-03)
- RLS policies enforce database-level isolation ✓ (verified in 07-02, pending BYPASSRLS fix)

**What CANNOT be tested:**
- WebSocket updates filtered by user ✗ (not implemented)
- Cross-user WebSocket isolation ✗ (not implemented)

## Conclusion

**ISO-03 Status:** Partially implemented
- ✓ REST API properly secured
- ✓ Database RLS policies in place
- ✗ **WebSocket broadcasting NOT filtered by user/account**

This gap should be tracked as a post-Phase 8 todo, not a blocking issue for mobile polish verification.
