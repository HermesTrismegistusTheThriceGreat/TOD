# Research Synthesis: Multi-Tenant Alpaca Trading Platform

**Project:** Alpaca Trading Platform with Multi-User, Multi-Account Support
**Synthesized:** 2026-01-29
**Scope:** Adding multi-user credential management to an existing single-user trading chat system

---

## Executive Summary

This project extends a working single-user Alpaca trading chat to support multiple friends managing separate trading accounts in a shared application. The research identifies a secure, pragmatic approach using application-level encryption (Fernet), PostgreSQL Row-Level Security (RLS), and per-request client factories—avoiding premature complexity while maintaining fortress-level security for real money.

**Core insight:** The existing FastAPI + Vue 3 + PostgreSQL stack is sufficient. Don't add external vaults or institutional account structures yet. Instead, encrypt credentials at the application level, enforce data isolation at the database layer, and create per-user Alpaca clients on-demand per request. This balances security with simplicity for the current scale (under 1000 users).

**Critical risk:** This system handles real money. Credential leakage, data isolation failures, and race conditions can cause financial loss or regulatory violations. Every phase requires security-first design, comprehensive testing, and audit-trail readiness. The roadmap must prioritize these non-negotiable foundations before feature expansion.

---

## Key Findings by Research Dimension

### Stack: Recommended Technologies

**Core Additions:**
- **cryptography (47.0.0+) with Fernet** – Symmetric encryption for API keys at rest. Provides authenticated encryption (AES-128-CBC + HMAC-SHA256) out of the box, eliminating manual cryptography mistakes. Industry standard in Python ecosystem.
- **sqlalchemy-tenants (0.1.0+)** – Thin wrapper around PostgreSQL Row-Level Security, automating tenant context in queries. Prevents accidental data leakage from application bugs.
- **python-dotenv (1.0.0+)** – Load Fernet key from `.env` locally; separate from hardcoded secrets in code.

**Database:**
- PostgreSQL 14+ (or NeonDB serverless) with native RLS support. No external vault needed for MVP (<1000 users).

**Not Recommended (Yet):**
- AWS KMS, HashiCorp Vault – Adds operational complexity (network calls, key management). Defer until 10k+ users or compliance mandates.
- Database-per-tenant – NeonDB charges per database; RLS in shared schema is more cost-effective.

**Version Requirements:**
- SQLAlchemy 2.0+ (existing) – Strong TypeDecorator support for encryption.
- FastAPI + Better Auth (existing) – No changes needed.
- alpaca-py 0.21.0+ (existing) – No special multi-tenant features; client instantiation per user is handled at application level.

**Confidence:** HIGH. Stack recommendations verified against official PostgreSQL docs, FastAPI security patterns, and cryptography library standards.

---

### Features: Table Stakes vs Differentiators

**Must-Build for MVP:**
1. **Account Selector Dropdown** (Low complexity) – Core UX for switching between accounts without re-login
2. **API Credential Secure Storage** (Medium complexity) – Encrypted at rest in database; never logged
3. **Account Metadata Display** (Low complexity) – Show account type (paper/live), balance, buying power at a glance
4. **Per-Account Balance/Equity Display** (Low complexity) – Auto-update after trades
5. **Order History per Account** (Low complexity) – Time-series view, filterable by account
6. **Trade Execution within Account Context** (Medium complexity) – Validate account selection before any trade

**Differentiators (Post-MVP):**
- Account Comparison Dashboard (side-by-side P&L, performance metrics)
- Paper-to-Live Migration Checklist (guided workflow, prevents accidents)
- Account Audit Log (who accessed which account, when, what actions)
- Alert Rules per Account (email/Slack notifications on thresholds)

**Explicitly Avoid:**
- Copy Trading (liability, compliance risk)
- Role-Based Access Control (RBAC) (overkill for trusted friends)
- Social Features / Leaderboards (wrong fit for small group)
- Institutional Account Types (OmniSub, Broker API) (premature complexity)
- Real-time Trade Synchronization across accounts (failure modes, reconciliation bugs)

**Feature Dependencies:** Account authentication → Account selector → Credential storage → Trade execution context → Real-time balance updates.

**Confidence:** HIGH. Recommendations based on multi-account platform patterns (3Commas, Bitsgap, WunderTrading) and Alpaca-specific constraints.

---

### Architecture: Core Patterns

**Recommended Architecture:**

```
Frontend (Vue 3) ← Session (HTTPOnly cookie)
    ↓
FastAPI Backend
  ├─ Authentication Layer (Better Auth)
  ├─ Account Context Dependency (validates ownership)
  ├─ Credential Manager (encrypt/decrypt)
  ├─ Alpaca Client Factory (per-request clients)
  └─ Route Handlers (scoped to user's account)
    ↓
PostgreSQL (with RLS)
  ├─ users (Better Auth)
  ├─ user_accounts (NEW: one-many relationship)
  ├─ user_credentials (NEW: encrypted API keys)
  ├─ alpaca_orders, alpaca_positions (scoped by account_id)
  └─ agent_logs (extend with account_id)
```

**Key Patterns:**

1. **TenantContext Dependency Injection** – Every handler receives validated tenant context (user_id + account_id). Database query validates user owns account before processing.

2. **Encrypted Credential Storage** – API keys encrypted with Fernet in database, decrypted in-memory only during request, never cached or logged.

3. **Per-User Alpaca Client Factory** – Create new Alpaca() instance per request from decrypted credentials. Client automatically disposed after request completes.

4. **Account Switching via Headers** – Store selected account_id in localStorage (NOT HTTPOnly), pass via `X-Account-ID` header per-request. No session refresh needed.

**Critical Anti-Patterns to Avoid:**
- Storing plaintext credentials in database
- Caching decrypted credentials in session state
- Logging API keys or tokens
- Single global Alpaca client for all users
- Including account_id in HTTPOnly session cookie
- Missing foreign key constraints on tenant-scoped tables

**Data Isolation:** Every query must include `WHERE account_id = $1` AND `user_id = $2` (enforced at database level via RLS).

**Confidence:** HIGH. Patterns verified against AWS multi-tenant SaaS guidance, Azure architecture, PostgreSQL security documentation, and FastAPI security patterns.

---

### Pitfalls: Critical, Moderate, Minor

**Critical Pitfalls (Prevent Before Launch):**

1. **Credential Leakage in Code/Logs** – Alpaca API keys hardcoded or logged = account takeover, regulatory reporting, financial loss. **Prevention:** Use python-dotenv + KMS-encrypted storage; pre-commit hooks (detect-secrets); credential redaction in logs; never print tokens.

2. **Insufficient Tenant Data Isolation** – User A sees User B's account data = unauthorized access, FINRA violation, immediate service shutdown. **Prevention:** Row-level security at database layer; validate ownership on every endpoint; integration tests proving isolation; no shared caches.

3. **OAuth Token Expiration Not Handled** – Access token expires, user can't trade mid-session or orders silently fail. **Prevention:** Understand Alpaca token lifecycle; refresh before expiration; serialize refresh with locks; test expiration scenarios.

4. **Rate Limit Hitting Silently** – 200 req/min Alpaca limit hit, orders dropped without user knowing. **Prevention:** Count requests carefully; implement exponential backoff; monitor consumption; gracefully queue orders; never silently drop.

5. **Paper vs Live Trading Logic Divergence** – System works in paper (instant fills, no fees) but fails in live (realistic fills, borrow fees, PDT rules). **Prevention:** Understand differences; test both environments; run strategy in paper for 1+ week before live; separate credentials.

**Moderate Pitfalls (Critical for Phase 2+):**
- Cross-tenant WebSocket hijacking (validate origin; re-auth per message)
- Race conditions in order execution (serialize per-account; atomic checks)
- Insufficient audit logging for compliance (immutable logs; FINRA CAT ready)
- Account switching without visual confirmation (big banner; warning dialog before live order)

**Minor Pitfalls (Good to Address):**
- Cryptic token refresh errors (log full error; provide error ID to support)
- Order submission feedback gap (link chat message to order ID; notify on fill/reject)
- Insufficient multi-tenant testing (create 2+ users per test; load test concurrency)

**Confidence:** HIGH. Pitfalls sourced from Alpaca community forum, fintech security literature, multi-tenant SaaS case studies, and trading platform failures documented in 2024-2026 incidents.

---

## Implications for Roadmap

### Proposed Phase Structure

**Phase 0: Security Foundation (Week 1-2)**
*Prerequisites for all subsequent work*

- Set up environment variable management (.env + python-dotenv)
- Implement Fernet encryption key generation and loading
- Add credential redaction to logging (never log tokens)
- Implement pre-commit hooks for credential scanning (detect-secrets)
- Create audit logging infrastructure (immutable, searchable, long retention)

**Deliverable:** All credentials handled securely from day one; no leakage vectors.
**Risk:** CRITICAL. Skipping this phase makes all subsequent phases vulnerable to credential breaches.

---

**Phase 1: Multi-Account Foundation (Week 2-4)**
*Enable account management without breaking existing single-user functionality*

- Create `user_accounts` table (one-to-many relationship with users)
- Create `user_credentials` table with encrypted storage
- Implement credential encryption/decryption service
- Build account selector UI (dropdown showing user's accounts)
- Implement account switching logic (localStorage + X-Account-ID header)
- Create TenantContext dependency (validates user owns account)
- Update all existing handlers to require TenantContext
- Add foreign key constraints to all tenant-scoped tables

**Deliverable:** Users can see and switch between multiple accounts without re-login.
**Testing:** Multi-user integration tests proving User A can't see User B's data.
**Gotchas:** Ensure existing single-user functionality still works during transition; every endpoint must validate ownership.

---

**Phase 2: Per-User Alpaca Clients (Week 4-6)**
*Enable trades against correct account via decrypted credentials*

- Build AlpacaClientFactory (per-request client creation)
- Refactor Alpaca service to use factory instead of global client
- Implement token refresh logic with serialization (locks, exponential backoff)
- Add token age monitoring and alerting
- Test token expiration scenarios (manual expiration in staging)
- Verify paper and live token refresh work independently

**Deliverable:** Each user's trades execute against their own Alpaca account.
**Testing:** Multi-user concurrent order tests; token refresh race condition tests.
**Gotchas:** Token expiration lifecycle not well documented by Alpaca; contact support if unclear.

---

**Phase 3: Real-Time Account Data (Week 6-8)**
*Display live balances, positions, order history per account*

- Add account_id to existing alpaca_orders, alpaca_positions tables
- Backfill account_id for existing orders/positions
- Update balance display to show per-account equity/buying power
- Update order history to filter by account_id
- Update WebSocket broadcasting to filter by account (don't leak data)
- Implement account metadata display (type, balance, status)

**Deliverable:** Users see real-time data for their selected account only.
**Testing:** Verify data isolation across accounts; WebSocket origin validation tests.
**Gotchas:** WebSocket broadcasts must validate subscriber ownership; easy to leak data if not careful.

---

**Phase 4: Safety Guards & UX (Week 8-10)**
*Prevent catastrophic mistakes (trading on wrong account, rate limiting)*

- Add visual account indicator (banner showing paper/live status)
- Add confirmation dialog before account switching
- Add warning dialog before live account orders
- Implement rate limit monitoring (track 200 req/min per user)
- Implement exponential backoff for Alpaca API failures
- Link chat messages to order IDs (track order status)
- Add order submission feedback (pending → filled/rejected)
- Create paper-to-live migration checklist

**Deliverable:** Users have visual confirmation of account context; orders are never silently dropped.
**Testing:** UX tests proving paper/live distinction is obvious; rate limit stress tests.
**Gotchas:** Paper trading can be dangerous UX (users think it's real); need very clear visual distinction.

---

**Phase 5: Compliance & Audit (Week 10-12)**
*Regulatory readiness for FINRA/SEC compliance*

- Implement immutable audit log (append-only, cannot delete/modify)
- Add audit entries for: login/logout, credential changes, account switching, order execution
- Ensure logs searchable and indexed by user/date/order_id
- Test audit trail completeness (can reconstruct who did what when)
- Verify logs can answer SEC inquiry: "prove User A executed Order X"
- Cross-reference audit logs with Alpaca order history
- Set long retention policy (7+ years for SEC)

**Deliverable:** Regulatory-ready audit trail; FINRA CAT compliance ready.
**Testing:** Audit log completeness tests; regulatory scenario tests.
**Gotchas:** Compliance not always visible in code but critical for deployment.

---

**Phase 6: Advanced Features (Post-MVP)**
*Only after core system is stable and secure*

- Account Comparison Dashboard (aggregate stats, P&L)
- Alert Rules (email/Slack notifications)
- Credential Rotation Workflow (guided safe key rotation)
- Advanced Position Tracking (unified view across accounts)

**Deliverable:** Nice-to-have features that differentiate from competitors.
**Testing:** All previous phases' tests must still pass.

---

## Research Flags

**Phases Requiring Deep Dives:**

- **Phase 1 (Multi-Account Foundation):** Research token refresh lifecycle with Alpaca support. Email [email protected] for documentation on token expiration times, refresh behavior, error handling. *Standard Pattern Risk:* Unclear documentation could cause Phase 2 failures.

- **Phase 2 (Per-User Clients):** Stress test token refresh under concurrent access. Verify serialization prevents race conditions. *Standard Pattern Risk:* Concurrency bugs won't show up in unit tests; need load tests.

- **Phase 3 (Real-Time Data):** Verify WebSocket origin validation and broadcaster filtering. *Security Risk:* Easy to leak data across tenants if broadcast filtering is wrong.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Fernet + sqlalchemy-tenants are proven, documented, community-validated. Version constraints clear. |
| **Features** | HIGH | MVP features based on industry patterns (3Commas, Bitsgap); anti-features clearly justified. Dependencies well-defined. |
| **Architecture** | HIGH | Patterns align with AWS multi-tenant guidance, PostgreSQL RLS documentation, FastAPI security docs. Data isolation approach solid. |
| **Pitfalls** | HIGH | Critical pitfalls sourced from Alpaca community forum, fintech security literature, documented 2024-2026 trading platform failures. Prevention strategies concrete. |
| **Roadmap Phases** | MEDIUM-HIGH | Phase sequence logical and dependency-driven. Phase 0 is non-negotiable. Later phases may uncover unforeseen Alpaca API constraints. |

**Gaps & Unknowns:**

1. **Alpaca Token Lifecycle** – Official docs don't specify token expiration times clearly. Will need to contact support. Impact: Phase 2 token refresh logic.

2. **Paper vs Live API Behavior** – Docs list differences but don't specify all edge cases (fill notifications, fees, order queue behavior). Recommend 1-week paper testing before live rollout. Impact: Phase 4 UX and Phase 6 advanced features.

3. **Rate Limit Exceptions** – Alpaca doesn't allow rate limit increases via self-service. Unknown if exceptions possible for legitimate multi-user platforms. Impact: Phase 3 if multiple accounts hit limit simultaneously.

4. **PostgreSQL RLS Performance** – Assumed acceptable for <1000 users. Unverified at scale. Recommend load testing in Phase 1. Impact: scalability post-MVP.

---

## Top 5 Things the Roadmap MUST Address

1. **Credential Security from Day 1** – No plaintext API keys in code, logs, or database. Use Fernet encryption, environment variables, and pre-commit scanning. Phase 0 is non-negotiable.

2. **Database-Level Data Isolation** – Row-Level Security on every tenant-scoped table. Not just application-level filtering. Verify with integration tests that User A cannot see User B's data through ANY endpoint.

3. **Token Refresh Serialization** – OAuth tokens expire. Concurrent requests must not race to refresh. Implement locks. Test with multiple simultaneous API calls.

4. **Account Context Visibility** – Users must KNOW which account they're trading on (paper vs live). Large banner, color coding, confirmation dialogs before any live trade. Prevent paper/live mistakes.

5. **Audit Trail Readiness** – Every trade, credential access, and account switch logged. Immutable, searchable, 7-year retention. FINRA CAT compliance non-negotiable. Don't bolt on after launch.

---

## Sources Aggregated

**Official Documentation:**
- cryptography.io Fernet Documentation
- PostgreSQL Row-Level Security Documentation
- FastAPI Security Documentation
- Alpaca Official Trading Documentation

**Multi-Tenant Architecture:**
- AWS SaaS Multi-Tenant Guidance
- Azure Multi-Tenant Architecture
- sqlalchemy-tenants GitHub Library

**Security & Compliance:**
- GitGuardian Secrets Management
- FINRA 2026 Regulatory Oversight Report
- OAuth 2.0 Token Refresh Standards

**Platform Patterns:**
- 3Commas / Bitsgap / WunderTrading (Multi-Account Platforms)
- Alpaca Community Forum (Real-World Issues)
- PortSwigger / Ably (WebSocket Security)

---

## Ready for Requirements Definition

All research dimensions converge on a pragmatic, security-first approach:
- Stack is clear (Fernet + RLS + per-request clients)
- Features are prioritized (table stakes in MVP, differentiators in Phase 2+)
- Architecture patterns are proven (TenantContext, encrypted storage, per-user clients)
- Pitfalls are documented with prevention strategies (critical, moderate, minor)
- Roadmap phases are sequential, dependency-driven, and security-first

**Next Step:** Roadmapper consumes this SUMMARY to structure the project requirements and phase planning. Security and data isolation are non-negotiable constraints that cascade through every phase.
