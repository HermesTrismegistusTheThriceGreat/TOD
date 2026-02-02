# Requirements: Alpaca Trading Chat

**Defined:** 2026-01-29
**Core Value:** Friends can log in, add their own Alpaca accounts, and trade via chat — each person controls their own money.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Account Management

- [x] **ACCT-01**: User can add multiple Alpaca accounts (API key + secret)
- [x] **ACCT-02**: User can view list of their connected accounts
- [x] **ACCT-03**: User can switch active account via dropdown selector
- [x] **ACCT-04**: User can update credentials for existing account
- [x] **ACCT-05**: User can remove a connected account
- [x] **ACCT-06**: Account selector is touch-friendly on mobile

### Credential Security

- [x] **CRED-01**: API credentials are encrypted at rest in database (Fernet)
- [x] **CRED-02**: Credentials are decrypted only during API calls, never cached
- [x] **CRED-03**: Credentials never appear in logs or error messages
- [x] **CRED-04**: Database enforces user can only access own accounts (RLS/FK)

### Account Display

- [x] **DISP-01**: Active account shows type (paper/live) prominently
- [x] **DISP-02**: Active account shows real-time balance and equity
- [x] **DISP-03**: Active account shows buying power
- [x] **DISP-04**: Visual indicator distinguishes paper vs live (color/banner)

### Trading Context

- [x] **TRADE-01**: Chat executes trades against user's selected account only
- [x] **TRADE-02**: Account context is validated before any trade execution
- [x] **TRADE-03**: Positions display shows only selected account's positions
- [x] **TRADE-04**: Order history shows only selected account's orders

### Data Isolation

- [x] **ISO-01**: User A cannot see User B's accounts
- [x] **ISO-02**: User A cannot see User B's positions or orders
- [ ] **ISO-03**: WebSocket updates are filtered by account ownership (DEFERRED - gap documented)

### Mobile

- [x] **MOB-01**: All pages tested and functional on mobile viewport
- [x] **MOB-02**: Account switcher works well on touch devices
- [x] **MOB-03**: Chat interface usable on mobile

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication Expansion

- **AUTH-01**: User can sign in with Google OAuth
- **AUTH-02**: User can sign in with GitHub OAuth

### AI Model Choice

- **AI-01**: User can select AI backend (Claude or Kimi)
- **AI-02**: Model preference persists across sessions

### Operations

- **OPS-01**: User receives alerts when credential expires soon
- **OPS-02**: Credential rotation workflow (safe key replacement)
- **OPS-03**: Account audit log (who accessed what, when)

### Advanced Features

- **ADV-01**: Account comparison dashboard
- **ADV-02**: Trading history export to CSV
- **ADV-03**: Paper-to-live migration checklist

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Copy trading / trade replication | Compliance liability, execution complexity |
| RBAC / permission matrix | Over-engineering for small trusted group |
| Social features / leaderboards | Wrong fit, creates peer pressure |
| Unified P&L reporting for compliance | Each account is independent |
| Institutional sub-accounts (OmniSub) | Requires Alpaca partnership agreement |
| Multi-currency support | Alpaca is USD-focused, adds complexity |
| Advanced portfolio rebalancing | Overkill for friends trading |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ACCT-01 | Phase 4 | Complete |
| ACCT-02 | Phase 4 | Complete |
| ACCT-03 | Phase 4 | Complete |
| ACCT-04 | Phase 4 | Complete |
| ACCT-05 | Phase 4 | Complete |
| ACCT-06 | Phase 8 | Complete |
| CRED-01 | Phase 1 | Complete |
| CRED-02 | Phase 3 | Complete |
| CRED-03 | Phase 1 | Complete |
| CRED-04 | Phase 2 | Complete |
| DISP-01 | Phase 5 | Complete |
| DISP-02 | Phase 5 | Complete |
| DISP-03 | Phase 5 | Complete |
| DISP-04 | Phase 5 | Complete |
| TRADE-01 | Phase 6 | Complete |
| TRADE-02 | Phase 6 | Complete |
| TRADE-03 | Phase 6 | Complete |
| TRADE-04 | Phase 6 | Complete |
| ISO-01 | Phase 7 | Complete |
| ISO-02 | Phase 7 | Complete |
| ISO-03 | Phase 7 | Deferred (WebSocket filtering gap documented) |
| MOB-01 | Phase 8 | Complete |
| MOB-02 | Phase 8 | Complete |
| MOB-03 | Phase 8 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-02-02 after Phase 8 completion (MILESTONE COMPLETE)*
