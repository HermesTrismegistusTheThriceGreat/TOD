# Phase 5: Account Display - Research

**Researched:** 2026-01-31
**Domain:** Vue 3 Real-Time Account Data Display (TypeScript + Axios + Element Plus + Alpaca API)
**Confidence:** HIGH

## Summary

Phase 5 implements the display of active account information (type, balance, equity, buying power) in the UI. This phase requires fetching real-time account data from the Alpaca API through the backend and displaying it prominently in the frontend.

The phase builds directly on Phase 4's account management infrastructure and requires:

1. **Backend Enhancement**: New endpoint to fetch Alpaca account details via the stored credential
2. **Frontend Service Layer**: Extend `credentialService` with account data fetching
3. **UI Components**: Display account metrics in header or dedicated panel with visual indicators for paper/live accounts
4. **Type Safety**: TypeScript interfaces matching Alpaca's TradeAccount model

The technical complexity is LOW because:
- Alpaca SDK is already integrated (alpaca-py in backend)
- Credential decryption pattern is established (`get_decrypted_alpaca_credential`)
- Frontend service pattern is proven (Phase 4)
- Element Plus has all necessary display components (Card, Statistic, Badge)
- Vue 3 reactivity handles real-time updates seamlessly

**Key architectural insight:** Account data must be fetched on-demand (when credential changes) rather than polling continuously. Store the fetched data in the Pinia store and update it when the active credential changes.

**Primary recommendation:** Create a new backend endpoint `/api/credentials/{credential_id}/account-data` that fetches real-time Alpaca account info using the stored credential. Extend the frontend credential service with `getAccountData()` method. Create an `AccountDataDisplay.vue` component that shows type badge, balance, equity, and buying power. Integrate into the AppHeader or create a dedicated account info panel. Use Element Plus Card + Badge + Statistic components for clean, readable display.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue | ^3.4.0 | Reactive UI framework | Phase 4 standard; reactivity handles data updates |
| TypeScript | ^5.0.0 | Type safety | Project-wide standard; critical for API response types |
| Axios | ^1.6.0 | HTTP client | Already configured; used throughout codebase |
| Element Plus | ^2.13.1 | UI components | Phase 4 standard; provides Card, Badge, Statistic components |
| Pinia | ^2.1.7 | State management | Phase 4 standard; stores account data with active credential |
| Alpaca SDK (alpaca-py) | Latest | Python trading API client | Already in backend; handles account data retrieval |
| FastAPI | Latest | Python web framework | Backend standard; handles new account endpoint |

### Supporting (Element Plus Components)
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| el-card | 2.13.1 | Container for account info | Main container for account display panel |
| el-badge | 2.13.1 | Status indicator | Label for account type (Paper/Live) with color |
| el-statistic | 2.13.1 | Metric display | Display balance, equity, buying power values |
| el-divider | 2.13.1 | Visual separator | Separate account metrics in display |
| el-icon | 2.13.1 | Icon support | Visual cues for account metrics |
| el-skeleton | 2.13.1 | Loading placeholder | Show while account data is loading |

### Backend Dependencies (Python)
| Package | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alpaca-py | Latest | Alpaca Trading API SDK | Official SDK; already integrated; provides TradeAccount model |
| httpx | Latest | Async HTTP client | For fallback HTTP calls if SDK unavailable |
| pydantic | Latest | Data validation | Schema validation for account response |
| sqlalchemy | Latest | ORM for credential lookup | Already in use; query encrypted credentials |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Element Plus Card/Badge | DIV with custom CSS | More work; Element Plus components proven and tested in Phase 4 |
| On-demand fetching | WebSocket streaming | Simpler implementation; unnecessary overhead for occasional updates |
| Pinia store | Component local state | Pinia allows sharing data across multiple components (header, dedicated panel) |
| Alpaca SDK | Raw HTTP requests | SDK abstracts authentication; reduces error handling code |

**Installation:**
```bash
# Backend: alpaca-py already installed
# Frontend: packages already installed

# Verify in backend:
uv pip show alpaca-py
```

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── routers/
│   ├── credentials.py              # Existing; extend with new endpoint
│   └── (new account data endpoint here)
├── schemas/
│   ├── credential_schemas.py       # Existing; add AccountDataResponse
│   └── account_schemas.py          # NEW: Account data response schemas
├── modules/
│   ├── credential_service.py       # Existing; already has decrypt function
│   └── account_service.py          # NEW: Fetch Alpaca account data

frontend/
├── services/
│   ├── credentialService.ts        # Existing; extend with getAccountData()
│   └── api.ts                      # Already configured
├── stores/
│   ├── accountStore.ts             # Existing; extend with accountData state
│   └── orchestratorStore.ts        # Existing
├── components/
│   ├── AccountDataDisplay.vue      # NEW: Display account metrics
│   ├── AppHeader.vue               # Existing; integrate account display
│   └── (other existing components)
├── types/
│   └── account.ts                  # Existing; add AccountDataResponse types
└── composables/
    └── (existing composables)
```

### Pattern 1: Backend Account Data Endpoint

**What:** FastAPI endpoint that validates the credential, decrypts it, fetches live account data from Alpaca API, and returns formatted account information.

**When to use:** Frontend requests account data when user selects a credential or page loads with active credential.

**Example:**
```python
# Source: Phase 4 credentials router pattern + credential_service.py
# Backend endpoint: /api/credentials/{credential_id}/account-data

from fastapi import APIRouter, Depends, HTTPException
from modules.credential_service import get_decrypted_alpaca_credential
from modules.account_service import fetch_alpaca_account_data

@router.get(
    "/credentials/{credential_id}/account-data",
    response_model=AccountDataResponse,
    summary="Get real-time account data for credential"
)
async def get_credential_account_data(
    credential_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Fetch real-time account data from Alpaca using stored credential.
    
    - Validates credential ownership
    - Decrypts credential (decrypt-on-demand pattern)
    - Calls Alpaca /v2/account endpoint
    - Returns formatted account data with type (paper/live)
    
    Returns:
        AccountDataResponse with:
        - account_type: "paper" or "live"
        - balance: Current cash balance
        - equity: Total equity (cash + positions)
        - buying_power: Available buying power
        - currency: Account currency (USD)
        - trading_blocked: Whether trading is blocked
    """
    try:
        async with get_connection_with_rls(user.id) as conn:
            # Decrypt credential
            async with get_decrypted_alpaca_credential(
                conn, credential_id, user.id
            ) as (api_key, secret_key):
                # Fetch account data
                account_data = await fetch_alpaca_account_data(
                    api_key, secret_key, credential.credential_type
                )
                
                return AccountDataResponse(
                    account_type=account_data['account_type'],
                    balance=account_data['cash'],
                    equity=account_data['equity'],
                    buying_power=account_data['buying_power'],
                    currency=account_data.get('currency', 'USD'),
                    trading_blocked=account_data.get('trading_blocked', False),
                    last_updated=datetime.utcnow().isoformat()
                )
    except Exception as e:
        logger.error(f"Failed to fetch account data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 2: Frontend Account Data Service Method

**What:** Extend the existing `credentialService` with a method to fetch account data from the backend endpoint.

**When to use:** In `accountStore` when active credential changes, or in `AccountDataDisplay` component when mounted.

**Example:**
```typescript
// Source: Phase 4 credentialService pattern
// frontend/src/services/credentialService.ts

// Add to existing credentialService object:
async getAccountData(credentialId: string): Promise<AccountDataResponse> {
  try {
    const response = await apiClient.get<AccountDataResponse>(
      `/api/credentials/${credentialId}/account-data`
    )
    return response.data
  } catch (err) {
    console.error('[credentialService] Failed to fetch account data:', err)
    throw err
  }
}
```

### Pattern 3: Account Store Enhancement

**What:** Extend `accountStore` with account data state and action to fetch it.

**When to use:** Automatically fetch account data when active credential changes.

**Example:**
```typescript
// Source: Phase 4 accountStore pattern
// frontend/src/stores/accountStore.ts - new reactive state

// Add to store state:
const accountData = ref<AccountDataResponse | null>(null)
const accountDataLoading = ref<boolean>(false)

// Add action:
async function fetchAccountData(credentialId: string): Promise<void> {
  try {
    accountDataLoading.value = true
    accountData.value = await credentialService.getAccountData(credentialId)
    console.log('[AccountStore] Account data loaded:', accountData.value)
  } catch (err) {
    console.error('[AccountStore] Failed to load account data:', err)
    accountData.value = null
  } finally {
    accountDataLoading.value = false
  }
}

// In setActiveCredential, call:
function setActiveCredential(credentialId: string): void {
  activeCredentialId.value = credentialId
  localStorage.setItem('activeCredentialId', credentialId)
  
  // Auto-fetch account data when credential changes
  fetchAccountData(credentialId)
}
```

### Pattern 4: Account Data Display Component

**What:** Vue 3 component that displays account information with visual indicators for account type.

**When to use:** In header or dedicated account info panel to show active account status and metrics.

**Example:**
```vue
<!-- Source: Phase 4 component patterns -->
<!-- frontend/src/components/AccountDataDisplay.vue -->

<template>
  <el-card class="account-data-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>Active Account</span>
        <el-badge
          v-if="accountData"
          :value="accountData.account_type.toUpperCase()"
          :type="accountData.account_type === 'paper' ? 'warning' : 'danger'"
          class="account-badge"
        />
      </div>
    </template>

    <!-- Loading skeleton -->
    <el-skeleton v-if="store.accountDataLoading" animated />

    <!-- Account data -->
    <div v-else-if="accountData" class="account-metrics">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6">
          <el-statistic
            title="Balance"
            :value="formatCurrency(accountData.balance)"
            :precision="2"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-statistic
            title="Equity"
            :value="formatCurrency(accountData.equity)"
            :precision="2"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-statistic
            title="Buying Power"
            :value="formatCurrency(accountData.buying_power)"
            :precision="2"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-alert
            v-if="accountData.trading_blocked"
            title="Trading Blocked"
            type="error"
            :closable="false"
          />
        </el-col>
      </el-row>
    </div>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <p>No account connected</p>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAccountStore } from '@/stores/accountStore'

const store = useAccountStore()

const accountData = computed(() => store.accountData)

function formatCurrency(value: string | number): number {
  return parseFloat(String(value))
}
</script>

<style scoped>
.account-data-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.account-badge {
  margin-left: auto;
}

.account-metrics {
  padding: 16px 0;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #909399;
}
</style>
```

### Anti-Patterns to Avoid

- **Polling continuously:** Don't set up intervals to fetch account data every N seconds. Fetch on-demand when credential changes.
- **Storing plaintext credentials in UI:** Never expose API keys or secret keys in component state or logs.
- **Duplicate API calls:** Don't call account data endpoint multiple times without memoization. Store in Pinia.
- **Hardcoding API URLs:** Use the apiClient base URL configured in `services/api.ts`.
- **Ignoring credential validity:** Always validate credential is active before fetching account data.
- **Synchronous blocking:** Use async/await with try-catch; never block UI during API calls.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Currency formatting | Custom formatting functions | `Intl.NumberFormat` or Element Plus `Statistic` component | Locale-aware; handles edge cases |
| Account type badge styling | Custom CSS classes | Element Plus `Badge` with type prop | Built-in color schemes; responsive |
| Account metrics display | DIV + CSS grid | Element Plus `Card` + `Statistic` | Consistent spacing; responsive design; accessibility |
| Error handling for API calls | Custom try/catch everywhere | Axios error interceptors in apiClient | Centralized; consistent error responses |
| Real-time value updates | Manual polling | Vue 3 reactivity + computed properties | Automatic; no memory leaks; efficient |
| Loading indicator | Custom spinner | Element Plus `Skeleton` | Built-in animation; good UX |

**Key insight:** Display components are simple rendering logic. The complexity is in fetching, caching, and updating data correctly. Use established patterns from Phase 4 (credentialService, accountStore) and don't build custom UI components when Element Plus already solves the problem.

## Common Pitfalls

### Pitfall 1: Treating Paper and Live Account Type Detection as API Response Field
**What goes wrong:** Developer expects Alpaca API response to include an explicit "account_type" field; instead it returns the account object from a specific API endpoint base URL.

**Why it happens:** Alpaca SDK abstracts the paper vs. live distinction by using different base URLs (paper-api.alpaca.markets vs api.alpaca.markets). The "account type" must be inferred from which endpoint the credential was validated against.

**How to avoid:** Store the account_type when validating the credential (Phase 4). Return it with account data. Don't try to infer it from the API response.

**Warning signs:** If account data endpoint response is missing an `account_type` field, you're inferring it incorrectly.

### Pitfall 2: Fetching Account Data on Every Render
**What goes wrong:** Component calls `fetchAccountData()` in mounted or every time store changes, causing infinite API requests.

**Why it happens:** Reactive watchers or computed properties can trigger fetches without proper guards.

**How to avoid:** Fetch account data only when active credential *changes*, not on every re-render. Use `watch` with `{ immediate: false }` or call from `setActiveCredential()` only.

**Warning signs:** Network tab shows repeated identical requests; browser console shows repeated "Fetching account data" messages.

### Pitfall 3: Not Handling Stale Credentials
**What goes wrong:** User deletes a credential, but component still tries to fetch account data for it, causing 404 errors.

**Why it happens:** Store still holds reference to deleted credential ID.

**How to avoid:** When credential is deleted, clear the active credential and account data. Check if credential still exists before fetching.

**Warning signs:** Errors like "Credential not found" appearing after deleting a credential.

### Pitfall 4: Displaying Raw Numeric Strings Without Formatting
**What goes wrong:** Balance shows as "100000.25489" instead of "$100,000.25" or "100,000.25 USD".

**Why it happens:** Alpaca API returns values as strings with full precision; need locale-aware formatting.

**How to avoid:** Use Element Plus `Statistic` component (handles formatting) or `Intl.NumberFormat` API. Always specify precision.

**Warning signs:** Metrics look like raw database values; hard to parse at a glance.

### Pitfall 5: Missing Loading States for Account Data
**What goes wrong:** User sees old account data briefly before new data loads after changing credentials.

**Why it happens:** No skeleton loader or loading indicator while fetching.

**How to avoid:** Always show a loading skeleton (Element Plus `Skeleton`) while `accountDataLoading` is true. Clear old data when starting new fetch.

**Warning signs:** UI blinks or shows old values briefly when switching credentials.

## Code Examples

### Backend Account Service Function

**Source:** Alpaca SDK documentation + Phase 4 credential_service pattern

```python
# backend/modules/account_service.py

from typing import Dict, Any, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAccountRequest
from modules.logger import OrchestratorLogger

logger = OrchestratorLogger("account_service")

async def fetch_alpaca_account_data(
    api_key: str,
    secret_key: str,
    account_type: str,  # "paper" or "live"
) -> Dict[str, Any]:
    """
    Fetch real-time account data from Alpaca API.
    
    Uses alpaca-py SDK to get account details including balance, equity, buying power.
    
    Args:
        api_key: Alpaca API key (plaintext, already decrypted)
        secret_key: Alpaca secret key (plaintext, already decrypted)
        account_type: "paper" or "live" to select correct endpoint
        
    Returns:
        Dict with keys: account_type, cash, equity, buying_power, currency, trading_blocked
    """
    try:
        # Create client with credentials
        client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=account_type == "paper"
        )
        
        # Fetch account
        account = client.get_account()
        
        logger.info(f"Fetched account data for {account_type} account")
        
        return {
            "account_type": account_type,
            "cash": str(account.cash),
            "equity": str(account.equity),
            "buying_power": str(account.buying_power),
            "currency": account.currency or "USD",
            "trading_blocked": account.trading_blocked or False,
        }
    except Exception as e:
        logger.error(f"Failed to fetch account data: {e}")
        raise
```

### Response Schema

```python
# backend/schemas/account_schemas.py - add to existing file

from pydantic import BaseModel, Field
from datetime import datetime

class AccountDataResponse(BaseModel):
    """Real-time account data from Alpaca API."""
    
    account_type: str = Field(
        ...,
        description="Account type: 'paper' or 'live'"
    )
    balance: str = Field(
        ...,
        description="Cash balance (currency units as string)"
    )
    equity: str = Field(
        ...,
        description="Total equity: cash + positions"
    )
    buying_power: str = Field(
        ...,
        description="Available buying power"
    )
    currency: str = Field(
        default="USD",
        description="Account currency"
    )
    trading_blocked: bool = Field(
        default=False,
        description="Whether trading is blocked"
    )
    last_updated: str = Field(
        ...,
        description="Timestamp of last fetch (ISO 8601)"
    )
```

### Frontend TypeScript Types

```typescript
// frontend/src/types/account.ts - add to existing file

/**
 * Real-time account data response from backend.
 * Mirrors backend AccountDataResponse schema.
 */
export interface AccountDataResponse {
  /** Account type: "paper" or "live" */
  account_type: string
  /** Cash balance as string (e.g., "100000.25") */
  balance: string
  /** Total equity (cash + positions) as string */
  equity: string
  /** Available buying power as string */
  buying_power: string
  /** Account currency (default: USD) */
  currency: string
  /** Whether trading is blocked */
  trading_blocked: boolean
  /** ISO 8601 timestamp of last update */
  last_updated: string
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fetch all account data on load | Fetch on-demand when credential changes | Vue 3 / 2026 | Reduces unnecessary API calls; improves performance |
| Hardcoded paper/live detection | Store account_type with credential during validation | Phase 4 completion | Eliminates duplicate validation logic; single source of truth |
| Component-level data fetching | Centralized store (Pinia) with service layer | Vue 3 best practices | Data consistent across multiple components; easier testing |
| Custom API response parsing | Use Pydantic + TypeScript types | Type safety standard | Prevents parsing errors; better IDE support |

**Deprecated/outdated:**
- Manual currency formatting: Use `Intl.NumberFormat` or Element Plus `Statistic`
- Custom spinners for loading: Use Element Plus `Skeleton` component
- Polling for real-time updates: Use event-driven updates on credential change

## Open Questions

1. **Refresh Strategy for Account Data**
   - What we know: Account data should update when credential changes; fetched on-demand, not continuously
   - What's unclear: Should component refresh account data on a timer if window remains open? Is account data expected to change while user is viewing?
   - Recommendation: Start with on-demand fetching (changes only). Add optional "Refresh" button if stakeholders request manual refresh. Do NOT implement automatic polling.

2. **Handling Multiple Credentials**
   - What we know: User can have multiple credentials; only one is "active"
   - What's unclear: Should account data display for non-active credentials? Should quick-look cards show all accounts?
   - Recommendation: Display account data only for active credential. If multi-account view needed, defer to Phase 6.

3. **Account Data Caching**
   - What we know: Alpaca API returns latest balance/equity
   - What's unclear: Should we cache account data to reduce API calls? For how long?
   - Recommendation: No caching initially. Each credential change triggers fresh fetch. If performance becomes issue, add 1-minute client-side cache with manual refresh button.

4. **Error Handling for Blocked Accounts**
   - What we know: Alpaca returns `trading_blocked` flag
   - What's unclear: How to display this to user? Blocking trade buttons? Warning banner?
   - Recommendation: Display trading_blocked status in account display. UI components can check this flag before allowing trades (implement in Phase 6+).

## Sources

### Primary (HIGH confidence)
- **Alpaca Trading API Documentation** - https://docs.alpaca.markets/docs/working-with-account (Verified GET /v2/account endpoint returns cash, equity, buying_power fields)
- **Alpaca Get Account Reference** - https://docs.alpaca.markets/reference/getaccount-1 (Verified response schema with all account fields)
- **alpaca-py SDK** - Available in backend dependencies; TradingClient.get_account() method used for fetching
- **Phase 4 Research Document** - `.planning/phases/04-account-management-ui/04-RESEARCH.md` (Established patterns for Vue 3, Pinia, credentialService, Element Plus)
- **Vue 3 Composition API Documentation** - Official docs; confirmed pattern for reactive state and computed properties
- **Element Plus Component Library** - v2.13.1 in package.json; Card, Statistic, Badge, Skeleton components verified

### Secondary (MEDIUM confidence)
- **Real-Time Data Display Patterns in Vue 3** - https://vueschool.io/articles/vuejs-tutorials/5-component-design-patterns-to-boost-your-vue-js-applications/ (Verified on-demand fetching pattern is standard)
- **Alpaca Paper Trading Documentation** - https://docs.alpaca.markets/docs/paper-trading (Verified paper accounts have same API as live accounts, only base URL differs)

### Tertiary (LOW confidence)
- None (all findings verified with official docs or Phase 4 codebase patterns)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - All technologies already in use (Vue 3, Axios, Element Plus, Alpaca SDK); versions confirmed in codebase
- Architecture patterns: **HIGH** - Patterns established in Phase 4 (credentialService, accountStore); Alpaca SDK method verified in official docs
- Pitfalls: **MEDIUM** - Based on common account/real-time data patterns; not all validated against this specific codebase but align with TypeScript + Axios best practices
- Account data fields: **HIGH** - Official Alpaca API documentation confirms cash, equity, buying_power fields available
- Account type (paper/live) detection: **HIGH** - Verified in Phase 4 credential validation logic (stored in database)

**Research date:** 2026-01-31
**Valid until:** 2026-03-02 (30 days; Alpaca API stable, but check for new account fields if extended features added later)
