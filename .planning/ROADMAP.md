# Roadmap: Alpaca Trading Chat Multi-Tenant

## Overview

This roadmap transforms a working single-user Alpaca trading chat into a multi-tenant platform where friends can connect their own trading accounts. The journey progresses from security foundations (encrypted credential storage) through account management UI, trading context integration, data isolation, and mobile polish. Security and data isolation are non-negotiable foundations that cascade through every phase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Security Foundation** - Encrypted credential infrastructure before any user data
- [x] **Phase 2: Database Schema** - User accounts and credentials tables with RLS
- [x] **Phase 3: Credential Management** - Backend services for encrypted storage/retrieval
- [x] **Phase 4: Account Management UI** - Frontend for adding, viewing, switching accounts
- [ ] **Phase 5: Account Display** - Show account type, balance, equity, buying power
- [x] **Phase 5.1: Multiple Credentials Support** - Enable multiple Alpaca credentials per account (INSERTED)
- [ ] **Phase 6: Trading Context** - Chat executes against selected account only
- [ ] **Phase 7: Data Isolation** - User A cannot see User B's data anywhere
- [ ] **Phase 8: Mobile Polish** - Touch-friendly account switcher and responsive audit

## Phase Details

### Phase 1: Security Foundation
**Goal**: Establish encrypted credential infrastructure before storing any user secrets
**Depends on**: Nothing (first phase)
**Requirements**: CRED-01, CRED-03
**Success Criteria** (what must be TRUE):
  1. Fernet encryption key loads from environment variable on server start
  2. Credential values are encrypted/decrypted correctly in round-trip tests
  3. API credentials never appear in application logs (verified via log audit)
  4. Pre-commit hook blocks commits containing secrets
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Create encryption service and config
- [x] 01-02-PLAN.md — Add log redaction filter and pre-commit hooks
- [x] 01-03-PLAN.md — Write tests and verify phase success criteria

### Phase 2: Database Schema
**Goal**: Create user_accounts and user_credentials tables with row-level security
**Depends on**: Phase 1
**Requirements**: CRED-04
**Success Criteria** (what must be TRUE):
  1. user_accounts table exists with user_id foreign key
  2. user_credentials table exists with encrypted API key/secret columns
  3. Row-level security policy enforces user can only query own accounts
  4. Database migration runs successfully on NeonDB
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Create user_accounts and user_credentials tables with indexes
- [x] 02-02-PLAN.md — Implement Row-Level Security policies for user isolation
- [x] 02-03-PLAN.md — Create SQLAlchemy ORM with EncryptedString TypeDecorator and tests

### Phase 3: Credential Management
**Goal**: Backend services to store, retrieve, and never cache decrypted credentials
**Depends on**: Phase 1, Phase 2
**Requirements**: CRED-02
**Success Criteria** (what must be TRUE):
  1. API endpoint accepts Alpaca API key + secret and stores encrypted
  2. Credentials are decrypted only during Alpaca API calls
  3. Decrypted credentials are never held in session state or cache
  4. Credential update endpoint allows changing existing account credentials
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Create Pydantic schemas and credential service with decrypt-on-demand
- [x] 03-02-PLAN.md — Create FastAPI credential API endpoints with RLS middleware
- [x] 03-03-PLAN.md — Integrate decrypt-on-demand into Alpaca agent and create test suite

### Phase 4: Account Management UI
**Goal**: Users can add, view, switch, update, and remove their Alpaca accounts
**Depends on**: Phase 3
**Requirements**: ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05
**Success Criteria** (what must be TRUE):
  1. User can add a new Alpaca account by entering API key + secret
  2. User can view a list of all their connected accounts
  3. User can switch active account via dropdown selector
  4. User can update credentials for an existing account
  5. User can remove a connected account
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Backend user_accounts API (router + schemas)
- [x] 04-02-PLAN.md — Frontend service layer (types + credentialService + accountStore)
- [x] 04-03-PLAN.md — Frontend components (dialog, list, selector, header integration)

### Phase 5: Account Display
**Goal**: Active account shows type (paper/live), balance, equity, and buying power
**Depends on**: Phase 4
**Requirements**: DISP-01, DISP-02, DISP-03, DISP-04
**Success Criteria** (what must be TRUE):
  1. Active account displays type (paper or live) prominently
  2. Active account shows real-time balance and equity
  3. Active account shows buying power
  4. Visual indicator clearly distinguishes paper vs live (color/banner)
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md — Backend account-data endpoint with Alpaca API integration
- [ ] 05-02-PLAN.md — Frontend service layer (types, getAccountData, store state)
- [ ] 05-03-PLAN.md — AccountDataDisplay component with header integration

### Phase 5.1: Multiple Credentials Support (INSERTED)
**Goal**: Enable users to add multiple Alpaca credentials per account with nickname/label field and selection UI
**Depends on**: Phase 5
**Requirements**: CRED-05 (new)
**Success Criteria** (what must be TRUE):
  1. User can add multiple credentials of the same type (e.g., multiple paper accounts)
  2. Each credential has a distinguishing nickname/label
  3. User can select which credential to use as active
  4. No 409 Conflict error when adding second credential
**Plans**: 3 plans

Plans:
- [x] 05.1-01-PLAN.md — Database migration (drop unique constraint, add nickname column)
- [x] 05.1-02-PLAN.md — Backend schemas and service layer (nickname support)
- [x] 05.1-03-PLAN.md — Frontend types and components (nickname input and display)

### Phase 6: Trading Context
**Goal**: Chat and positions/orders display use only the selected account
**Depends on**: Phase 4, Phase 5
**Requirements**: TRADE-01, TRADE-02, TRADE-03, TRADE-04
**Success Criteria** (what must be TRUE):
  1. Chat executes trades against user's selected account only
  2. Account context is validated before any trade execution
  3. Positions page shows only selected account's positions
  4. Order history shows only selected account's orders
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Data Isolation
**Goal**: Complete tenant isolation - users cannot see each other's data
**Depends on**: Phase 2, Phase 6
**Requirements**: ISO-01, ISO-02, ISO-03
**Success Criteria** (what must be TRUE):
  1. User A cannot see User B's accounts (verified via integration test)
  2. User A cannot see User B's positions or orders (verified via integration test)
  3. WebSocket updates are filtered by account ownership
  4. No endpoint leaks data across tenants
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

### Phase 8: Mobile Polish
**Goal**: Touch-friendly account management and responsive design across all pages
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: ACCT-06, MOB-01, MOB-02, MOB-03
**Success Criteria** (what must be TRUE):
  1. Account selector is touch-friendly on mobile
  2. All pages tested and functional on mobile viewport
  3. Account switcher works well on touch devices
  4. Chat interface is usable on mobile
**Plans**: TBD

Plans:
- [ ] 08-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 5.1 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security Foundation | 3/3 | ✓ Complete | 2026-01-29 |
| 2. Database Schema | 3/3 | ✓ Complete | 2026-01-30 |
| 3. Credential Management | 3/3 | ✓ Complete | 2026-01-31 |
| 4. Account Management UI | 3/3 | ✓ Complete | 2026-01-31 |
| 5. Account Display | 0/3 | Planning complete | - |
| 5.1 Multiple Credentials | 3/3 | ✓ Complete (INSERTED) | 2026-01-31 |
| 6. Trading Context | 0/TBD | Not started | - |
| 7. Data Isolation | 0/TBD | Not started | - |
| 8. Mobile Polish | 0/TBD | Not started | - |

## Requirement Coverage

| Requirement | Phase | Description |
|-------------|-------|-------------|
| CRED-01 | Phase 1 | API credentials encrypted at rest (Fernet) |
| CRED-03 | Phase 1 | Credentials never appear in logs |
| CRED-04 | Phase 2 | Database enforces user owns accounts (RLS/FK) |
| CRED-02 | Phase 3 | Credentials decrypted only during API calls |
| ACCT-01 | Phase 4 | User can add multiple Alpaca accounts |
| ACCT-02 | Phase 4 | User can view list of connected accounts |
| ACCT-03 | Phase 4 | User can switch active account via dropdown |
| ACCT-04 | Phase 4 | User can update credentials for existing account |
| ACCT-05 | Phase 4 | User can remove a connected account |
| DISP-01 | Phase 5 | Active account shows type (paper/live) |
| DISP-02 | Phase 5 | Active account shows real-time balance/equity |
| DISP-03 | Phase 5 | Active account shows buying power |
| DISP-04 | Phase 5 | Visual indicator distinguishes paper vs live |
| CRED-05 | Phase 5.1 | User can add multiple credentials per account |
| TRADE-01 | Phase 6 | Chat executes against selected account only |
| TRADE-02 | Phase 6 | Account context validated before trade |
| TRADE-03 | Phase 6 | Positions display shows selected account only |
| TRADE-04 | Phase 6 | Order history shows selected account only |
| ISO-01 | Phase 7 | User A cannot see User B's accounts |
| ISO-02 | Phase 7 | User A cannot see User B's positions/orders |
| ISO-03 | Phase 7 | WebSocket updates filtered by ownership |
| ACCT-06 | Phase 8 | Account selector touch-friendly on mobile |
| MOB-01 | Phase 8 | All pages tested on mobile viewport |
| MOB-02 | Phase 8 | Account switcher works on touch devices |
| MOB-03 | Phase 8 | Chat interface usable on mobile |

**Coverage:** 25/25 requirements mapped

---
*Roadmap created: 2026-01-29*
*Phase 1 planned: 2026-01-29*
*Phase 1 executed: 2026-01-29*
*Phase 2 planned: 2026-01-29*
*Phase 2 executed: 2026-01-30*
*Phase 3 planned: 2026-01-30*
*Phase 3 executed: 2026-01-31*
*Phase 4 executed: 2026-01-31*
*Phase 5 planned: 2026-01-31*
*Phase 5.1 inserted: 2026-01-31 (urgent - 409 conflict fix)*
*Phase 5.1 executed: 2026-01-31*
*Depth: comprehensive (8 phases + 1 insertion)*
