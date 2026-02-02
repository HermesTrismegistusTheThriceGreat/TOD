# Phase 7: Data Isolation - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete tenant isolation — users cannot see each other's data anywhere in the system. Verify through real browser testing that:
1. Same user switching accounts sees correct positions for each account
2. Different users don't see each other's data after logout/login cycle

</domain>

<decisions>
## Implementation Decisions

### Testing Approach
- Use `agent-browser` skill for automated browser-based verification
- Two test scenarios with real accounts:
  1. **Same-user account switching:** seagerjoe@gmail.com (password123) has 2 paper accounts — switch between them and verify Open Positions page updates to correct account
  2. **Cross-user isolation:** Logout, login as muzz@gmail.com (password123) — this user has no Alpaca accounts, Open Positions page should be empty, no data from previous user
- Any test failure blocks progress — fix immediately before continuing

### Backend Status (Verified Phase 6 Completion)
- ✅ Positions endpoint now uses credential_id from request (fixed in Phase 6)
- ✅ Orders endpoint uses credential_id correctly (fixed in Phase 6)
- ✅ Chat endpoint working correctly with credential switching
- All three endpoints use `get_connection_with_rls()` and `get_decrypted_alpaca_credential()`

### Phase 7 Focus
- Verification testing (browser-based)
- Integration tests for RLS policies
- Logging for suspicious access attempts

### Failure Handling
- Test failures block and fix immediately (isolation is critical)
- Runtime: Log suspicious access attempts with user/credential details
- Return empty data or appropriate error, but log the attempt
- No active alerting (email/notification) — logs sufficient for small trusted group

### Claude's Discretion
- Exact logging format for suspicious access
- Whether to add integration tests alongside browser tests
- How to structure the positions endpoint fix

</decisions>

<specifics>
## Specific Ideas

- seagerjoe@gmail.com / password123 — test user with 2 paper accounts for account switching
- muzz@gmail.com / password123 — test user with no Alpaca accounts for empty state verification
- The positions page specifically is the problem — it shows the same data regardless of which account is selected or which user is logged in

</specifics>

<deferred>
## Deferred Ideas

- **WebSocket isolation:** Investigate WS broadcast scope and fix if needed — deferred to Phase 8 or backlog (only 1 elite subscription for testing, price data filtering unclear)
- **Full endpoint audit:** Comprehensive review of all trading endpoints — focus on positions/orders for now

</deferred>

---

*Phase: 07-data-isolation*
*Context gathered: 2026-02-01*
