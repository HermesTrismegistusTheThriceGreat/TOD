# Domain Pitfalls: Multi-Tenant Alpaca Trading Platform

**Domain:** Multi-tenant credential management for trading platforms with real-money support
**Researched:** 2026-01-29
**Scope:** OAuth credential management, data isolation, rate limiting, security, Alpaca-specific issues
**Overall confidence:** HIGH (verified with official docs and security sources)

---

## Critical Pitfalls

Mistakes that cause data breaches, complete rewrites, regulatory violations, or financial loss. These deal with real money and require fortress-level security.

### Pitfall 1: Credential Leakage in Code or Logs

**What goes wrong:**
Alpaca API keys, OAuth tokens, or refresh tokens appear in git history, environment logs, error traces, or temporary debugging output. A single leaked credential grants full trading account access (real money) to an attacker.

**Why it happens:**
- Developers embed credentials "temporarily" for local testing and forget to remove them before commit
- Error handling logs sensitive token values or exception stacks containing tokens
- Token appears in query parameters or URLs that get logged
- Hardcoding approach used before secrets manager is in place
- Team members unfamiliar with fintech credential sensitivity
- Copy-pasted debug code into production with print statements

**Consequences:**
- Account takeover: Attacker executes trades, withdraws funds, locks owner out
- Regulatory liability: Credential leak is reportable event (FINRA/SEC)
- Real financial loss (user's real money accounts compromised)
- Breach cascades to multiple users if patterns are similar
- Recovery requires credential rotation, OAuth re-auth flow for all affected users
- Credentials visible in logs accessible to: ops team, contractors, log service employees, breached log system

**Prevention:**
- **Never hardcode credentials** — use environment variables + python-dotenv from day one
- **Gitignore .env files** — add to `.gitignore` before first commit
- **Secrets manager required for production** — use AWS KMS, HashiCorp Vault, or similar for database-encrypted credentials
- **Strip secrets from logs** — implement logging middleware that redacts tokens (last 4 chars only)
- **Pre-commit hooks** — use tools like `detect-secrets` or `gitguardian` to scan for credential patterns before commit
- **Never log full token/key** — log token fingerprint or ID only
- **Audit git history** — even private repos, check for leaked credentials
- **Token rotation policy** — all OAuth tokens rotated 90-180 days minimum
- **Separate credentials per environment** — paper trading tokens != live trading tokens
- **Never print exceptions that might contain credentials** — use unique request IDs for debugging instead
- **Implement credential redaction at logger level:**
  ```python
  REDACTED = "**REDACTED**"
  logger.info(f"Alpaca request for account: {REDACTED}")
  ```
- **Rotate logs aggressively** (daily minimum for sensitive logs)

**Detection:**
- Tokens appearing in error traces or server logs
- Developers asking "can I hardcode this temporarily?"
- Git history containing `.env` or similar with credentials
- Accidental commits with credentials before `.gitignore` set up
- Monitoring alerts for unusual account activity (unexpected trades, withdrawals)
- Credential scanning tools reporting leaks
- Grep logs for API key patterns; check log aggregation service

**Alpaca-specific notes:**
- Alpaca OAuth tokens are the primary attack surface in this architecture
- Refresh tokens are long-lived—their compromise is especially dangerous
- Each token authorizes one account (live OR paper, not both)—one leak per account
- Contact support to revoke compromised tokens: [email protected]
- Paper and live tokens must be stored/rotated separately

**Sources:**
- [GitGuardian Secrets Management](https://blog.gitguardian.com/secrets-api-management/)
- [Cycode Secrets Tools 2026](https://cycode.com/blog/best-secrets-management-tools/)
- [Fintech API Security Challenges - Kong Inc.](https://konghq.com/blog/enterprise/api-security-management-fintech)

---

### Pitfall 2: Insufficient Tenant Data Isolation

**What goes wrong:**
User A's Alpaca account credentials or trading activity becomes visible to User B due to improper access control or query filtering. One user sees another user's trades, balances, or can execute orders on another's account.

**Why it happens:**
- Row-level security (RLS) not implemented in database
- API endpoints don't validate tenant ownership before returning data
- Shared query objects used across tenants without tenant filtering
- OAuth token doesn't encode tenant context; server trusts session alone
- Frontend sends user ID in request; server doesn't validate it belongs to authenticated user
- Shared cache or WebSocket broadcast to wrong audience
- Migration to multi-user missed one endpoint or feature
- Handlers accept `account_id` from request but never validate ownership

**Consequences:**
- Unauthorized access to financial data (regulatory violation, FINRA/SEC reporting required)
- Ability to execute trades on another user's account (real financial loss)
- Loss of customer trust
- CRITICAL data breach
- Legal liability for both platform and affected users
- Immediate service shutdown/rewrite required

**Prevention:**
- **Row-level security (RLS) enforced at database layer** — not just application layer
  - Each query must include `WHERE user_id = current_user` or similar
  - Test every query: does it work if I'm a different user?
  - Use parameterized queries with tenant context automatically injected
- **Tenant context in every token** — encode `user_id` in OAuth token or session, validate on every request
- **Endpoint validation pattern — ALWAYS validate ownership:**
  ```python
  # BAD: Trust user_id from request
  @app.get("/api/positions")
  async def get_positions(account_id: str):
      return Account.query.filter_by(account_id=account_id).first()

  # GOOD: Validate token matches requested user_id
  @app.get("/api/positions")
  async def get_positions(account_id: str, tenant: TenantContext = Depends(get_tenant_context)):
      if tenant.account_id != account_id:
          raise Unauthorized()
      return Account.query.filter_by(account_id=account_id).first()
  ```
- **Never trust user input for tenant determination** — derive tenant from authenticated session/token
- **Shared resource protection:**
  - Cache keys include tenant ID: `f"account:{user_id}:{account_id}"`
  - WebSocket subscriptions validated per message, not just on connection
  - Background jobs tagged with user_id and validated before processing
- **Regular audit of data access patterns** — run queries as if you're User A, verify you can't see User B's data
- **Integration tests proving isolation** — test that User A cannot access User B's data through any endpoint
- **Add FK constraints for data integrity:**
  ```sql
  ALTER TABLE user_credentials
  ADD FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE CASCADE;
  ```

**Detection:**
- Logging shows cross-user data access
- Users report seeing other users' activity or balances
- Monitoring alert: unusual access patterns
- Penetration test: "Can I access another user's account via API?"
- FINRA CAT reporting would catch systematic misaccesses
- Customer reports "I see another user's trades in my account"

**Alpaca-specific notes:**
- Each Alpaca account is authorized by a single OAuth token
- Your system must map: User → Multiple Alpaca Accounts → Token per account
- Isolation failure means one user can access another's Alpaca account
- Paper and live accounts are separate Alpaca accounts; isolation must work for both
- Both environments enforce Pattern Day Trader protections

**Sources:**
- [Multi-Tenant Security Risks - QRvey](https://qrvey.com/blog/multi-tenant-security/)
- [Multitenancy Security - TechTarget](https://www.techtarget.com/searchsecurity/tip/How-to-overcome-3-multi-tenancy-security-issues)
- [Multi-Tenant Architecture - Frontegg](https://frontegg.com/guides/multi-tenant-architecture)

---

### Pitfall 3: OAuth Token Expiration Not Handled

**What goes wrong:**
A user's OAuth access token expires during an active session. Without proper refresh token handling, user is kicked out mid-trade, or worse, the system silently fails to refresh and executes trades with a dead token (which fails, potentially at critical moments).

**Why it happens:**
- Token expiration time not documented by Alpaca (found via support tickets, not official docs)
- Refresh token logic only implemented on initial setup, not on every API call
- Race condition: multiple simultaneous API calls compete to refresh the same token
- Refresh token itself expires (users don't realize refresh tokens can expire too)
- No monitoring of token age; token is discovered to be expired only when it fails
- Clock skew: server's clock differs from broker's; token appears valid locally but is expired upstream
- No serialization around refresh; concurrent requests both try to refresh, one succeeds, others get invalid_grant

**Consequences:**
- User unable to trade mid-session (UX failure, lost opportunity, financial loss)
- Silent failures: request returns 401/403, system doesn't handle gracefully
- Token refresh fails with cryptic error (users don't know why)
- Race condition: two threads both attempt refresh, one succeeds, other gets invalid_grant error
- User's session corrupted; re-login required even though token could be refreshed
- Orders silently fail because token is dead

**Prevention:**
- **Understand Alpaca token expiration from official docs** — query support if not documented
  - Access tokens are short-lived (typically 1-2 hours industry standard)
  - Refresh tokens are longer-lived (typically days to months)
  - Refresh requires backend-to-backend call (not visible to frontend)
- **Implement token refresh before expiration:**
  ```python
  # Check token age before making request
  if token_age > expiration_threshold:  # e.g., 90% of lifetime
      refresh_token()
  ```
- **Serialize token refresh** — use lock/mutex to prevent concurrent refresh attempts
  ```python
  token_lock.acquire()
  try:
      if token_age > threshold:
          refresh_token()
  finally:
      token_lock.release()
  ```
- **Track refresh token expiration** — refresh tokens expire too; monitor and re-auth if needed
- **Handle 401/403 gracefully:**
  - Return 401 to frontend with "please re-authenticate" message
  - Don't retry silently with old token
  - Log token failure for monitoring
  - Don't cascade failure to other users
- **Monitor token age in metrics** — alert if token is >90% of lifetime
- **Test expiration scenarios:**
  - Manually expire a token in staging
  - Verify system handles it gracefully
  - Verify refresh succeeds and trades continue
  - Test with multiple users to verify serialization works
- **Paper and live tokens refresh independently** — each must be refreshed separately

**Detection:**
- Users report "suddenly can't trade"
- 401 errors in logs with valid session cookie
- Invalid_grant errors on token refresh attempts
- Token age metrics show tokens approaching expiration
- Integration test failing with 401 after token expected to expire
- Multiple 401 errors from same user in short time span (indicates refresh loop)

**Alpaca-specific notes:**
- Alpaca doesn't publicly document token expiration time (must ask support)
- Refresh requires backend-to-backend call (token exchange in backend, never frontend)
- Paper and live tokens are separate; each has independent expiration
- Contact support: [email protected] for token lifecycle details
- Community forum has historical "invalid_grant" issues

**Sources:**
- [OAuth 2.0 Refresh Token Handling - Nango Blog](https://nango.dev/blog/concurrency-with-oauth-token-refreshes)
- [Refresh Tokens Guide - Frontegg](https://frontegg.com/blog/oauth-2-refresh-tokens)
- [OAuth 2.1 Features 2026 - Medium](https://rgutierrez2004.medium.com/oauth-2-1-features-you-cant-ignore-in-2026-a15f852cb723)
- [Alpaca OAuth Documentation](https://docs.alpaca.markets/docs/using-oauth2-and-trading-api)
- [Alpaca OAuth Issues - Community Forum](https://forum.alpaca.markets/t/oauth-invalid-grant-error-when-requesting-access-token/15964)

---

### Pitfall 4: Rate Limit Hitting Silently or With No Backoff

**What goes wrong:**
The system hits Alpaca's 200 requests/minute rate limit, receives a 429 error, and either silently drops the request (user thinks trade was submitted but it wasn't) or crashes without retry logic. In multi-user scenarios, one user's heavy trading can starve other users.

**Why it happens:**
- Rate limit threshold not accounted for in design (200 req/min per account, 10 req/sec burst)
- No exponential backoff implemented; system retries immediately, hits limit again
- Request counting logic doesn't account for multiple users sharing same system
- Alpaca's limit is per-account, but developers don't understand per-account implications
- 10 requests/second burst limit not understood; system tries to burst trade execution
- No monitoring of rate limit consumption; teams discover limit by hitting it in production
- Chat-based order entry generates multiple API calls per order (get balance, get positions, then order) compounding the issue
- No graceful degradation; orders dropped instead of queued

**Consequences:**
- Orders silently dropped: user submits trade via chat but it never reaches Alpaca
- User confusion: "I said buy 100 shares but nothing happened"
- Race condition for order fill: rate limit hit mid-order, partial execution
- System slowdown: endless retry loops consuming CPU
- One user's activity blocks other users (if system shares rate limit across users)
- False sense of security: system "works" on test data, fails in production with real traffic
- Financial loss: missed opportunities, orders that should have executed don't

**Prevention:**
- **Understand Alpaca's limits (CRITICAL):**
  - 200 requests/minute per account (hard limit)
  - 10 requests/second burst limit (hard limit)
  - Cannot be increased self-service (requires support at [email protected])
  - Each user/account has independent limit
- **Count requests to Alpaca carefully:**
  - Every API call counts: orders, positions, account, market data
  - Chat order generation: get balances → get positions → validate → place order = 3+ calls minimum
  - If system calls `get_positions()` on every order chat, rate limit is easy to hit
  - Cache positions/balance locally when possible
- **Implement exponential backoff with jitter:**
  ```python
  retry_count = 0
  while True:
      try:
          response = alpaca_api.place_order(...)
          return response
      except RateLimitError:
          retry_count += 1
          if retry_count > max_retries:
              raise
          wait_time = (2 ** retry_count) + random.uniform(0, 1)
          time.sleep(wait_time)
  ```
- **Optimize API call patterns:**
  - Cache account balance/positions (don't fetch every request)
  - Batch orders when possible
  - Avoid redundant API calls in chat command flow
  - Pre-fetch data when user signs in
- **Monitor rate limit consumption:**
  - Track API call count per user per minute
  - Alert at 80% of limit
  - Return "too busy" error to user before hitting hard limit
  - Never silently drop orders
- **Graceful degradation for users:**
  - If approaching limit, queue orders with message: "Order queued, will execute when rate limit resets"
  - Don't drop orders silently
  - Queue should persist and retry (in database, not memory)
- **Rate limit per user in multi-tenant:**
  - Each user's orders should be counted separately
  - Each user gets their own rate limit budget
  - Don't let one user's trading block another user
- **Test rate limit scenarios:**
  - Simulate hitting rate limit in staging
  - Verify system behavior (should not drop orders silently)
  - Run load test: multiple users trading simultaneously
  - Verify rate limit doesn't cross-contaminate between users

**Detection:**
- Users report orders not executing
- 429 errors in logs
- Exponential increase in retry attempts
- Rate limit consumption metrics approach 100%
- Orders in queue but never sent to Alpaca
- Production outage after heavy trading period
- Multiple users affected simultaneously (shared rate limit issue)

**Alpaca-specific notes:**
- Rate limit is 200 requests/minute per account (non-negotiable without support ticket)
- Burst limit 10 requests/second is harder to hit but possible in tight loops
- Limits are per OAuth token (each user/account has separate token)
- Paper and live accounts have separate rate limits (independent 200 req/min each)
- Contact support at [email protected] for exceptions (though approval is unlikely)

**Sources:**
- [Alpaca Rate Limits - Support](https://alpaca.markets/support/usage-limit-api-calls)
- [Alpaca API Rate Limiting - APIPark](https://apipark.com/technews/knVpYNIB.html)
- [Trading API Limitations - Alpaca Community Forum](https://forum.alpaca.markets/t/trading-api-limitations/9743)

---

### Pitfall 5: Paper vs Live Trading Logic Divergence

**What goes wrong:**
System works perfectly in paper trading but fails in live trading, or vice versa. Differences in order execution, fees, or margin calculations between environments cause unexpected behavior when users switch to real money.

**Why it happens:**
- Developers assume paper and live APIs are identical (they have identical schemas but different behaviors)
- Paper trading doesn't simulate borrow fees, slippage, order queue position, or price improvement
- Paper trading fills orders instantly at displayed price; live trading may fail or fill at worse price
- Tests pass in paper environment but fail in production
- Developers unaware that Pattern Day Trader (PDT) protections apply to both environments
- Code path assumes certain order fills that don't happen in live
- Paper account doesn't send order fill notifications; live account does
- No testing with live credentials before deployment

**Consequences:**
- User's strategy shows great returns in paper, fails catastrophically in live
- Unexpected fees charged in live (borrow fees not simulated in paper)
- Orders expected to execute don't, breaking strategy logic
- User loses money on difference between paper and live behavior
- Lack of fill notifications causes code to hang waiting for fills that come late
- Users lose real money due to incomplete testing

**Prevention:**
- **Understand paper vs live differences (from Alpaca official docs):**
  - Paper does NOT simulate: market impact, info leakage, slippage, order queue, price improvement, regulatory fees, dividends
  - Paper does NOT charge borrow fees (marked "Coming Soon")
  - Paper does NOT send order fill notifications
  - Both enforce Pattern Day Trader (PDT) rules: 4th day trade within 5 business days requires $25K+ net worth
  - API schema is identical; behavior differs
  - Different endpoints: `https://paper-api.alpaca.markets` vs `https://api.alpaca.markets`
  - Separate OAuth tokens required for paper vs live
- **Test both environments with real-like scenarios:**
  - Run same strategy in paper for full week before go-live
  - Execute small live trades to verify behavior matches paper
  - Monitor divergence between expected and actual fills
  - Have staging environment connected to paper account
- **Implement fill notification handling for live:**
  - Paper doesn't send fills; live may not send immediately
  - Use polling fallback: if fill not notified within timeout, query position
- **Mock both environments in tests:**
  - Unit tests mock Alpaca API
  - Integration tests run against paper-api.alpaca.markets in CI
  - Staging environment connected to paper account for final verification
- **Document differences for team:**
  - Create checklist of paper vs live gotchas
  - Before go-live, explicitly verify each difference
- **Separate credentials for clear context:**
  - Paper OAuth token != live OAuth token
  - Config clearly indicates which environment
  - Prevent accidental live trading with test code
  - Use environment variable to force paper during testing
- **Pre-live checklist:**
  - Verify PDT rules understood (4th trade in 5 days requires $25K+)
  - Verify borrow fees accounted for in live (not charged in paper)
  - Verify order fills handled asynchronously in live
  - Run full test suite against live endpoint
  - Test with small order first, verify behavior matches paper

**Detection:**
- Test passes with paper key but fails with live key
- User reports "strategy works in paper but loses money in live"
- Unexpected fees appearing in live account
- Orders not executing as expected
- PDT violations in live account (4th trade within 5 business days)
- Missing fill notifications causing code to hang
- User loses money on paper/live divergence

**Alpaca-specific notes:**
- Alpaca explicitly documents paper vs live differences in official docs
- Different endpoints require different configuration
- Separate OAuth tokens required for paper vs live
- PDT rules apply to both (account < $25K subject to day trade restrictions)
- Borrow fees in live (stocks you short incur borrowing costs)
- Paper fills orders instantly; live has realistic market conditions

**Sources:**
- [Alpaca Paper Trading Documentation](https://docs.alpaca.markets/docs/paper-trading)
- [Alpaca Paper vs Live Trading Support](https://alpaca.markets/support/difference-paper-live-trading)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, operational issues, or data integrity problems. Not immediately catastrophic but cause ongoing problems.

### Pitfall 6: Cross-Tenant WebSocket Hijacking

**What goes wrong:**
An attacker opens a WebSocket connection from a malicious site to your trading API. Due to missing origin validation, the connection succeeds and receives real-time order fills, position updates, or account data intended for another user. Browser silently sends cookies, authenticating the connection.

**Why it happens:**
- WebSocket connections don't enforce same-origin policy like regular HTTP requests
- Origin header not validated on WebSocket handshake
- Authentication token in query parameter instead of header (browser doesn't protect query params)
- Revoked session doesn't close existing WebSocket connections
- WebSocket event handlers don't re-check authentication on each message

**Consequences:**
- Data leakage: attacker eavesdrops on order fills, position changes
- Account enumeration: attacker discovers which accounts are connected
- Information edge: attacker sees your trades in real-time
- Cross-site forgery: attacker can send messages as authenticated user if WebSocket is duplex
- Trading strategy leakage (competitor sees what you're trading)

**Prevention:**
- **Validate origin on WebSocket handshake:**
  ```python
  # Check Origin header matches expected domain
  origin = request.headers.get('Origin')
  if origin not in ALLOWED_ORIGINS:
      reject_connection()
  ```
- **Never put auth token in query parameters** — use headers or cookies with secure flags
- **Close WebSocket when session revoked** — don't leave stale connections open
- **Re-validate authentication on each message** (not just connection):
  ```python
  @websocket.on('message')
  def handle_message(data):
      if not validate_session(request.sid):
          disconnect()
      process_message(data)
  ```
- **Use secure cookies for connection auth:**
  - HttpOnly flag (can't be accessed via JavaScript)
  - Secure flag (HTTPS only)
  - SameSite=Strict (prevent cross-site requests)
- **Filter data by tenant before broadcast:**
  - Don't broadcast all order fills to all connected clients
  - Send only fills for current user's accounts

**Detection:**
- Unauthorized connections from unexpected origins in logs
- WebSocket connection attempts from different domain
- User reports seeing other users' data in real-time updates
- Penetration test: open WebSocket from attacker domain
- Multiple connections from same user (indicates hijacking)

**Sources:**
- [WebSocket Security Best Practices - Ably](https://ably.com/topic/websocket-security)
- [Cross-Site WebSocket Hijacking - PortSwigger](https://portswigger.net/web-security/websockets/cross-site-websocket-hijacking)
- [WebSocket Security Checklist - Invicti](https://www.invicti.com/blog/web-security/websocket-security-best-practices)

---

### Pitfall 7: Race Conditions in Order Execution

**What goes wrong:**
Two chat commands execute simultaneously: "buy 100 shares" and "sell 50 shares". Due to race conditions, the system buys 100, then tries to sell 100 (instead of 50), hitting margin requirements or overselling.

**Why it happens:**
- No locking around order submission for a single account
- Concurrent requests from same user don't serialize
- Position check and order placement aren't atomic
- Multiple order commands in quick succession
- Chat bot doesn't rate-limit per-user order submissions
- WebSocket allows multiple concurrent message handlers
- Alpaca orders execute asynchronously; can't assume fill before next order

**Consequences:**
- Wrong number of shares ordered (oversold position)
- Margin call triggered unexpectedly
- Two orders execute when only one was intended
- System state diverges from Alpaca's actual position
- User loses money on unexpected execution
- Regulatory violations (oversold positions violate rules)

**Prevention:**
- **Serialize order operations per account:**
  ```python
  # Use lock keyed by user_id
  order_locks[user_id].acquire()
  try:
      get_current_position()
      validate_order()
      place_order()
  finally:
      order_locks[user_id].release()
  ```
- **Make order placement atomic:** check balance + place order in single transaction
- **Rate-limit orders per user:** queue orders if submitted too rapidly
- **Idempotent order IDs:** use `client_order_id` to detect duplicate orders (Alpaca will reject duplicate client_order_id)
- **Validate against latest state:** fetch fresh position before order, not cached
- **Queue orders if approaching limits:**
  - Don't execute concurrently, queue and process sequentially
  - Persist queue in database (survive restarts)
- **Test concurrency:**
  - Submit 2 orders simultaneously from same user
  - Verify only one succeeds or both are queued
  - Verify position accuracy post-execution
  - Load test with multiple users

**Detection:**
- User reports wrong number of shares ordered
- Two similar orders found in history from same user at same time
- Position mismatch between expected and actual
- Margin call alerts
- Race conditions caught in load testing
- Oversold position alerts from Alpaca

**Alpaca-specific notes:**
- Alpaca enforces position limits; order will reject if oversold
- Use `client_order_id` (idempotent key) to prevent duplicate orders
- Orders execute asynchronously; can't assume fill before next order placed
- Alpaca will reject duplicate client_order_id in same account

**Sources:**
- [Race Conditions in Production - Steve Bang](https://www.steve-bang.com/blog/race-condition-silent-bug-breaks-production)
- [Race Conditions in Automated Trading - TradersPost](https://blog.traderspost.io/article/understanding-race-conditions-in-automated-trading)

---

### Pitfall 8: Insufficient Audit Logging for Compliance

**What goes wrong:**
A user claims "I didn't execute that trade" or a regulator asks "who executed this trade and when?" but your system has no audit trail. No logs showing who issued the order, when, via what method (chat command), with what parameters.

**Why it happens:**
- Audit logging treated as "nice to have," not foundational
- Logs don't capture sufficient context (user, timestamp, action, parameters, result)
- Logs are written but not indexed or searchable
- Logs expire/rotate before any investigation needed
- Sensitive data (like full order details) in logs without redaction policy
- CAT (Consolidated Audit Trail) reporting requirements not understood
- Logging only added after regulatory pressure

**Consequences:**
- Cannot prove who executed a trade (user claims unauthorized, platform has no defense)
- Regulatory investigation impossible (FINRA/SEC cannot audit your controls)
- Dispute resolution fails (user disputes order, you have no evidence)
- Fines from SEC/FINRA for missing audit trail (millions of dollars)
- No way to debug who/when account was compromised
- Unable to prosecute insider trading or unauthorized access

**Prevention:**
- **Audit log every trade-related action:**
  - User authentication (login/logout)
  - Account credential changes
  - Account switching (user A → user B account)
  - Order submission (user, ticker, quantity, price, timestamp, result)
  - Order fill/rejection (with fill price, quantity)
  - Permission changes
  - Credential access/decryption
- **Audit log structure:**
  ```python
  audit_log = {
      "timestamp": "2026-01-29T14:23:45Z",
      "user_id": "user_123",
      "action": "order_placed",
      "resource": "order",
      "resource_id": "order_456",
      "details": {
          "symbol": "AAPL",
          "quantity": 100,
          "order_type": "market",
          "side": "buy"
      },
      "result": "success",
      "ip_address": "192.0.2.1",
      "user_agent": "ChatBot/1.0"
  }
  ```
- **Immutable storage:** logs append-only, cannot be deleted/modified (protects against tampering)
- **Long retention:** keep logs for at least 7 years (SEC requirement)
- **Searchable and indexed:** must be able to query by user, date range, order ID, etc.
- **Redact sensitive data:** don't log full OAuth tokens, only IDs
- **CAT reporting readiness:** ensure logs can answer "prove this user executed this order"
- **Cross-reference with Alpaca:**
  - Your audit logs + Alpaca's order history together prove who did what

**Detection:**
- Regulator asks for audit trail and you can't provide it
- User disputes an order and you have no evidence
- CAT reporting deadline approaching and no audit data
- Compliance team says logs are insufficient
- Breach investigation can't trace who accessed credentials

**Alpaca-specific notes:**
- Alpaca provides order history API; cross-reference your audit logs with Alpaca's authoritative order history
- User says Alpaca charged fees they didn't authorize; you must prove (via logs) who authorized the account connection
- Paper vs live orders must be separately auditable
- Token refresh events should be logged for audit trail

**Sources:**
- [FINRA 2026 Regulatory Oversight Report](https://www.finra.org/sites/default/files/2025-12/2026-annual-regulatory-oversight-report.pdf)
- [Compliance Automation Tools 2026 - Cynomi](https://cynomi.com/learn/compliance-automation-tools/)
- [FedRAMP Audit Log Retention - Ignyute](https://www.ignyteplatform.com/blog/fedramp/fedramp-audit-log-retention/)

---

### Pitfall 9: Account Switching Without Visual Confirmation

**What goes wrong:**
User switches from Paper Account to Live Account in a dropdown without realizing it. Issues a market order expecting it to execute on paper, but it executes on their real money live account. Loses thousands in seconds.

**Why it happens:**
- Account switching UI doesn't provide clear visual confirmation
- No warning dialog before executing order on live account
- System doesn't remember "you were on paper last, switching to live"
- Users don't look carefully when switching contexts
- Paper and live accounts named similarly ("AAPL Paper" vs "AAPL Live")
- No prominent warning banner showing current account

**Consequences:**
- User executes trade on wrong account (real money loss)
- User gets angry, sues platform
- Platform blamed for unclear UX, not user error
- Financial loss for user
- Regulatory complaints

**Prevention:**
- **Visual account indicator:**
  - Large, persistent banner showing current account (Paper or Live)
  - Different background colors (green for paper, red for live)
  - Account balance shown prominently
- **Confirmation dialog on account switch:**
  ```
  Are you sure? You are switching from Paper to Live.
  Live orders use REAL MONEY.
  Current account: [Account Name]
  Balance: $[amount]

  [Cancel] [Continue]
  ```
- **Warn before order on live account:**
  ```
  WARNING: This order will execute on LIVE account using REAL MONEY.
  Account: [Name]
  Balance: $[amount]
  [Review Order] [Cancel] [Execute]
  ```
- **Clear account naming:** "Paper Trading: AAPL" vs "LIVE: AAPL" — don't be ambiguous
- **Remember user's last account:** don't auto-switch on re-login
- **Mobile-friendly warning:** warning UI works on mobile (where users may be less careful)
- **Require explicit confirmation on live account orders:**
  - Checkboxes: "I understand this will use real money"

**Detection:**
- User reports executing on wrong account
- Checking logs: order from "live" token immediately after switch
- Complaints in support tickets
- Multiple users making same mistake

**Alpaca-specific notes:**
- Alpaca OAuth tokens are account-specific (one token = paper OR live, not both)
- Paper and live tokens must be managed separately
- Token name/identifier should make environment clear
- Can't accidentally trade on paper if using live token (and vice versa)

**Sources:**
- [Payload CMS Multi-Tenant State Management](https://www.buildwithmatija.com/blog/payload-cms-multi-tenant-state-management/)
- [Multi-Tenant Application Challenges - Clerk](https://clerk.com/blog/what-are-the-risks-and-challenges-of-multi-tenancy)

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major disruption. Good to address but lower priority than critical/moderate.

### Pitfall 10: Cryptic Token Refresh Errors

**What goes wrong:**
Token refresh fails with "invalid_grant" error (HTTP 422). User has no idea why. Error message from Alpaca isn't helpful. Support escalates but takes days to resolve.

**Why it happens:**
- Alpaca's error messages are cryptic (known issue from community forum)
- Paper account token expiration handled differently than live
- Clock skew between your server and Alpaca's
- Token already revoked but system tries to refresh it
- Refresh token itself expired (forgotten by dev)
- Authorization code expired (was already exchanged)

**Consequences:**
- User can't reconnect account
- Support tickets pile up
- User loses patience, tries different approach (insecure workaround)
- Bad UX (user frustrated)

**Prevention:**
- **Log full error response from Alpaca:**
  ```python
  response = alpaca.refresh_token(refresh_token)
  if response.status_code != 200:
      logger.error(f"Token refresh failed: {response.status_code} {response.text}")
  ```
- **Add context in error message to user:**
  ```
  "Account reconnection failed. Please try again or contact support.
   (Error code: ${error_id} - support can help faster with this code)"
  ```
- **Sync server time regularly** (NTP) to avoid clock skew
- **Test all refresh error paths:**
  - Expired refresh token
  - Already-exchanged auth code
  - Revoked token
  - Paper vs live differences
- **Document Alpaca's error codes internally** so support can resolve faster
- **Provide user with clear action:**
  - "Try disconnecting and reconnecting your account"
  - "Contact support if this persists"

**Detection:**
- Support tickets mentioning "invalid_grant"
- Error logs with cryptic Alpaca errors
- Multiple users reporting account reconnection issues on same day
- Token refresh metric shows high failure rate

**Alpaca-specific notes:**
- Community forum has historical "invalid_grant" issues
- Paper account token issues sometimes resolve after delete + re-auth
- Test paper vs live token refresh separately
- Contact Alpaca support at [email protected] if errors are systematic

**Sources:**
- [Alpaca OAuth Issues - Community Forum](https://forum.alpaca.markets/t/oauth-invalid-grant-error-when-requesting-access-token/15964)

---

### Pitfall 11: Order Submission Feedback Gap

**What goes wrong:**
User types "buy 100 AAPL" in chat. Chat bot says "Order submitted!" but never tells user if it was actually placed or what the order ID is. Minutes later, user doesn't see the order fill and doesn't know if order was rejected.

**Why it happens:**
- Chat response sent before Alpaca API returns
- Chat messages are ephemeral (disappear after a while)
- System doesn't link chat message to order ID
- No follow-up notification when order fills or rejects
- User assumes silence = success

**Consequences:**
- User confusion: "Did my order work?"
- Multiple submissions of same order (user retries thinking first failed)
- User misses fill notification in chat noise
- Orders silently rejected (insufficient funds) but user doesn't know

**Prevention:**
- **Link chat message to Alpaca order ID:**
  - Chat response includes order ID: "Order placed: #ORD-12345"
  - User can use ID to query order status
- **Confirm submission asynchronously:**
  - Chat: "Submitting order..."
  - Response from Alpaca comes back
  - Chat updated: "Order placed: #ORD-12345" or "Order rejected: reason"
- **Notify user on fill/reject:**
  - Chat: "ORD-12345 filled: 100 AAPL @ $180.50"
  - Or: "ORD-12345 rejected: Insufficient funds"
- **Persistent order history:**
  - User can see all orders in past 24h or past week
  - Link to Alpaca's order detail
  - Show order status: pending, filled, rejected, cancelled
- **Rate-limit per user to prevent accidental duplicates:**
  - "Too many orders too fast, try again in 5 seconds"

**Detection:**
- User report: "I submitted order but don't know if it worked"
- Logs show order placed but no fill notification reached user
- Duplicate orders from user for same stock at same time
- Support tickets: "Did my order execute?"

**Alpaca-specific notes:**
- Alpaca returns order ID on placement; always capture and return to user
- Order status can be polled via Alpaca API: get_order(order_id)
- Order fills may come asynchronously; provide order ID so user can query
- Paper trading doesn't send fill notifications; live trading may not send immediately

---

### Pitfall 12: Insufficient Testing of Multi-Tenant Scenarios

**What goes wrong:**
Tests pass with one user account, but the system breaks when a second user is added. Cross-tenant data leakage, race conditions, or token collisions not caught until production.

**Why it happens:**
- Tests use single user ID hardcoded
- Shared test database not cleaned between tests
- Integration tests don't simulate multiple users trading simultaneously
- Token/session management tests missing
- Feature branches tested alone, not together with other users' changes

**Consequences:**
- Multi-tenant bugs shipped to production
- Data isolation failure caught by user, not test
- Race conditions appear only under load
- Regression when features added later
- Users affected by isolation bugs

**Prevention:**
- **Test templates for multi-tenant scenarios:**
  - Create 2+ user accounts in test fixture
  - Run same operation with both users
  - Verify isolation (User A doesn't see User B's data)
- **Concurrent order tests:**
  - User A submits order
  - User B submits order simultaneously
  - Verify both are queued/executed correctly
  - Verify no race condition
- **Token refresh tests with multiple users:**
  - User A token refreshes
  - User B's token doesn't change
  - Verify isolation
- **Data cleanup:**
  - Tests are ephemeral: start clean, end clean
  - Each test creates its own users
  - No shared test data between test runs
- **Load testing with multiple concurrent users:**
  - Simulate 10 users trading simultaneously
  - Verify rate limits don't cross-contaminate
  - Verify session isolation
- **CI/CD enforces multi-user tests:**
  - Any feature touching user/account logic requires multi-user test
  - Tests run against paper-api.alpaca.markets in CI

**Detection:**
- Multi-user test fails
- Single-user test passes
- Production issue with multiple users trading simultaneously
- Data isolation test fails
- Race condition in production

**Sources:**
- General software testing best practices

---

## Phase-Specific Warnings

| Phase | Topic | Pitfall | Mitigation |
|-------|-------|---------|-----------|
| Phase 0 (User Auth) | Credential storage | Hardcoded keys in source | Implement secrets manager from day 1; use .env + python-dotenv |
| Phase 0 (User Auth) | Logging | Credentials in logs/exceptions | Never log tokens; implement credential redaction |
| Phase 1 (OAuth Connect) | Token handling | Token expiration not handled | Test token refresh; implement backoff; monitor token age |
| Phase 1 (OAuth Connect) | Token refresh | Race conditions in refresh | Serialize refresh with locks; test concurrent access |
| Phase 2 (Multi-user) | Data isolation | User A sees User B's data | Add row-level security; test isolation; endpoint validation |
| Phase 2 (Multi-user) | Account switching | Wrong account execution | Clear visual account indicator; confirmation dialog before live order |
| Phase 2 (Multi-user) | Testing | Insufficient multi-tenant tests | Create 2+ users per test; verify isolation; load test |
| Phase 3 (Chat Trading) | Order execution | Orders silently dropped (rate limit) | Implement exponential backoff; queue orders; monitor rate limit consumption |
| Phase 3 (Chat Trading) | Concurrency | Race conditions in orders | Serialize per-user order operations; atomic order + check |
| Phase 3 (Chat Trading) | Feedback | Order submission feedback gap | Link chat message to order ID; notify on fill/reject |
| Phase 4 (Live Trading) | Paper vs live | System works in paper, fails in live | Test both environments; document differences; separate credentials |
| Phase 4 (Live Trading) | Security | Credentials leaked | Pre-commit hooks; audit git history; enable 2FA; rotate credentials |
| All phases | Audit trail | Can't prove who did what | Immutable audit logs; long retention; compliant with FINRA CAT |
| All phases | WebSocket security | Cross-tenant hijacking | Validate origin; close on session revoke; re-auth on message |

---

## Summary of Prevention Strategies

### Immediate (implement before Phase 1 OAuth)
1. Secrets manager (env vars + KMS-encrypted credentials)
2. Pre-commit credential scanning (detect-secrets, gitguardian)
3. Credential redaction at logger level (never log tokens)
4. Audit logging infrastructure (immutable, searchable, long retention)
5. TenantContext dependency for every API endpoint

### Before Phase 2 (multi-user)
6. Row-level security at database layer
7. Data isolation tests (User A can't access User B's data)
8. Multi-user integration tests (2+ users per test)
9. Token refresh logic with serialization and backoff
10. Account switching UI with clear warnings

### Before Phase 3 (chat trading)
11. Rate limit monitoring and graceful handling
12. Order deduplication (client_order_id)
13. Exponential backoff retry logic
14. Order feedback system (link message to order ID)
15. Concurrent order tests (verify no race conditions)

### Before Phase 4 (live trading)
16. Full audit trail compliance (CAT-ready)
17. WebSocket origin validation
18. Session revocation that closes connections
19. Paper vs live environment separation (separate configs, tokens)
20. Pre-flight checklist (regulatory requirements, paper vs live differences)

### Ongoing (every phase)
- Monitor rate limit consumption
- Track token age and refresh frequency
- Audit data access patterns (verify no cross-tenant access)
- Run multi-user integration tests on every PR
- Verify isolation in production (sampling queries, monitoring)
- Security scanning (credentials, dependencies)
- Compliance checklist (FINRA CAT readiness)

---

## References

### Security & Credential Management
- [GitGuardian Secrets Management](https://blog.gitguardian.com/secrets-api-management/)
- [Cycode Secrets Tools 2026](https://cycode.com/blog/best-secrets-management-tools/)
- [Fintech API Security - Kong Inc.](https://konghq.com/blog/enterprise/api-security-management-fintech)

### Multi-Tenant Architecture
- [QRvey Multi-Tenant Security](https://qrvey.com/blog/multi-tenant-security/)
- [TechTarget Multi-Tenancy Security](https://www.techtarget.com/searchsecurity/tip/How-to-overcome-3-multi-tenancy-security-issues)
- [Frontegg Multi-Tenant Guide](https://frontegg.com/guides/multi-tenant-architecture)

### OAuth & Token Management
- [Nango OAuth Token Refresh](https://nango.dev/blog/concurrency-with-oauth-token-refreshes)
- [Frontegg Refresh Tokens](https://frontegg.com/blog/oauth-2-refresh-tokens)
- [OAuth 2.1 2026 Standards - Medium](https://rgutierrez2004.medium.com/oauth-2-1-features-you-cant-ignore-in-2026-a15f852cb723)

### Alpaca-Specific
- [Alpaca OAuth Documentation](https://docs.alpaca.markets/docs/using-oauth2-and-trading-api)
- [Alpaca Paper Trading](https://docs.alpaca.markets/docs/paper-trading)
- [Alpaca Rate Limits](https://alpaca.markets/support/usage-limit-api-calls)
- [Alpaca Community Forum - OAuth Issues](https://forum.alpaca.markets/t/oauth-invalid-grant-error-when-requesting-access-token/15964)

### WebSocket Security
- [Ably WebSocket Security](https://ably.com/topic/websocket-security)
- [PortSwigger CSWSH](https://portswigger.net/web-security/websockets/cross-site-websocket-hijacking)
- [Invicti WebSocket Best Practices](https://www.invicti.com/blog/web-security/websocket-security-best-practices)

### Compliance & Audit
- [FINRA 2026 Regulatory Oversight Report](https://www.finra.org/sites/default/files/2025-12/2026-annual-regulatory-oversight-report.pdf)
- [Race Conditions in Automated Trading - TradersPost](https://blog.traderspost.io/article/understanding-race-conditions-in-automated-trading)
