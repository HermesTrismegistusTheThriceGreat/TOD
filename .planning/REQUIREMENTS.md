# Requirements: Alpaca Trading Chat

**Defined:** 2026-01-29
**Core Value:** Friends can log in, add their own Alpaca accounts, and trade via chat — each person controls their own money.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Account Management

- [ ] **ACCT-01**: User can add multiple Alpaca accounts (API key + secret)
- [ ] **ACCT-02**: User can view list of their connected accounts
- [ ] **ACCT-03**: User can switch active account via dropdown selector
- [ ] **ACCT-04**: User can update credentials for existing account
- [ ] **ACCT-05**: User can remove a connected account
- [ ] **ACCT-06**: Account selector is touch-friendly on mobile

### Credential Security

- [x] **CRED-01**: API credentials are encrypted at rest in database (Fernet)
- [ ] **CRED-02**: Credentials are decrypted only during API calls, never cached
- [x] **CRED-03**: Credentials never appear in logs or error messages
- [ ] **CRED-04**: Database enforces user can only access own accounts (RLS/FK)

### Account Display

- [ ] **DISP-01**: Active account shows type (paper/live) prominently
- [ ] **DISP-02**: Active account shows real-time balance and equity
- [ ] **DISP-03**: Active account shows buying power
- [ ] **DISP-04**: Visual indicator distinguishes paper vs live (color/banner)

### Trading Context

- [ ] **TRADE-01**: Chat executes trades against user's selected account only
- [ ] **TRADE-02**: Account context is validated before any trade execution
- [ ] **TRADE-03**: Positions display shows only selected account's positions
- [ ] **TRADE-04**: Order history shows only selected account's orders

### Data Isolation

- [ ] **ISO-01**: User A cannot see User B's accounts
- [ ] **ISO-02**: User A cannot see User B's positions or orders
- [ ] **ISO-03**: WebSocket updates are filtered by account ownership

### Mobile

- [ ] **MOB-01**: All pages tested and functional on mobile viewport
- [ ] **MOB-02**: Account switcher works well on touch devices
- [ ] **MOB-03**: Chat interface usable on mobile

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
| ACCT-01 | Phase 4 | Pending |
| ACCT-02 | Phase 4 | Pending |
| ACCT-03 | Phase 4 | Pending |
| ACCT-04 | Phase 4 | Pending |
| ACCT-05 | Phase 4 | Pending |
| ACCT-06 | Phase 8 | Pending |
| CRED-01 | Phase 1 | Complete |
| CRED-02 | Phase 3 | Pending |
| CRED-03 | Phase 1 | Complete |
| CRED-04 | Phase 2 | Pending |
| DISP-01 | Phase 5 | Pending |
| DISP-02 | Phase 5 | Pending |
| DISP-03 | Phase 5 | Pending |
| DISP-04 | Phase 5 | Pending |
| TRADE-01 | Phase 6 | Pending |
| TRADE-02 | Phase 6 | Pending |
| TRADE-03 | Phase 6 | Pending |
| TRADE-04 | Phase 6 | Pending |
| ISO-01 | Phase 7 | Pending |
| ISO-02 | Phase 7 | Pending |
| ISO-03 | Phase 7 | Pending |
| MOB-01 | Phase 8 | Pending |
| MOB-02 | Phase 8 | Pending |
| MOB-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after Phase 1 completion*
