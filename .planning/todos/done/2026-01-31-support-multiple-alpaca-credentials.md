---
created: 2026-01-31T10:33
title: Support multiple Alpaca credentials per account
area: api
files:
  - apps/orchestrator_3_stream/backend/routers/credentials.py
  - apps/orchestrator_3_stream/backend/modules/user_models.py
  - apps/orchestrator_3_stream/frontend/src/views/AccountListView.vue
---

## Problem

Users get HTTP 409 Conflict error when trying to add a second Alpaca credential. The database has a unique constraint on `(user_account_id, credential_type)` which only allows ONE credential per type (alpaca/polygon) per account.

**User Impact:**
- Cannot add multiple paper accounts (e.g., paper1, paper2 for different strategies)
- Cannot have both paper and live credentials simultaneously
- Must delete existing credential before adding a new one

**Discovery:** Found during Phase 05-03 validation when testing with second set of Alpaca paper credentials.

## Solution

TBD - Options to consider:

1. **Remove unique constraint** - Allow multiple credentials of same type
2. **Add nickname/label field** - Let users distinguish credentials ("Paper Strategy A", "Live Trading")
3. **Store account_type separately** - Change credential_type from "alpaca" to "alpaca_paper" / "alpaca_live"
4. **Add credential selector UI** - When multiple exist, let user pick which to use as active

Database migration needed. UI updates for credential management and selection.
