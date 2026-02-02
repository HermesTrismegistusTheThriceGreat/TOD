# Header Active Account Redesign Plan

**Date**: 2026-02-02
**Author**: Opus 4.5 (Orchestrator Mastermind)
**Status**: Ready for Approval

---

## Problem Statement

The current Active Account box in the header is:
1. **White/light colored** - Creates jarring contrast against the dark theme header (#1a1a1a)
2. **Too large** - Uses Element Plus `el-card` with 320px min-width, consuming excessive header real estate
3. **Missing key metrics at glance** - Account nickname not prominently shown; metrics require scanning the card
4. **Not mobile optimized** - The large card format doesn't adapt well to mobile breakpoints

**Screenshot Analysis**: The current implementation shows a white card with "Active Account" header, Balance/Equity/Buying Power statistics in 3 columns, and a Pattern Day Trader alert - all within an Element Plus card that stands out as inconsistent with the dark-themed header.

---

## Design Goals

1. **Theme Consistency**: Match the dark theme with cyan accents (`--bg-tertiary`, `--accent-primary`)
2. **Compact Display**: Show key metrics (Buying Power + Account Type) inline without a card
3. **Account Identity**: Display nickname clearly so user always knows which account is connected
4. **Responsive**: Progressive collapse at 768px and 650px breakpoints
5. **Awesome Buttons**: Apply design system button standards

---

## Implementation Plan

### Phase 1: Create Compact Header Account Component

**New Component**: `HeaderAccountInfo.vue`

Replace the separate `AccountSelector` + `AccountDataDisplay` components with a unified, compact inline display.

**Desktop Layout (>768px)**:
```
[Account Dropdown ▼] | [Buying Power: $1,318,970] [PAPER Badge] | [Nav Buttons...]
```

**Structure**:
```vue
<template>
  <div class="header-account-info">
    <!-- Account Selector (compact) -->
    <div class="account-selector-compact">
      <el-select v-model="selectedId" size="small" class="compact-select">
        <el-option v-for="cred in credentials" :key="cred.id" :value="cred.id">
          <div class="option-content">
            <span class="option-name">{{ cred.nickname || 'Account' }}</span>
            <span class="option-balance">{{ formatCurrency(balance) }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- Buying Power Metric (inline badge style) -->
    <div class="metric-display">
      <span class="metric-label">BP</span>
      <span class="metric-value">{{ formattedBuyingPower }}</span>
    </div>

    <!-- Account Type Badge -->
    <span class="account-badge" :class="accountType">
      {{ accountType.toUpperCase() }}
    </span>
  </div>
</template>
```

**CSS Design System Compliance**:
```css
.header-account-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0.375rem 0.75rem;
  background: var(--bg-tertiary);      /* #2a2a2a - Dark gray, not white */
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s ease;
}

.header-account-info:hover {
  border-color: var(--border-light);
}

/* Metric Display - Badge Style */
.metric-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0 var(--spacing-sm);
  border-left: 1px solid var(--border-color);
}

.metric-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 0.875rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--status-success);  /* Green for buying power */
  font-variant-numeric: tabular-nums;
}

/* Account Type Badge */
.account-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.account-badge.paper {
  background: rgba(245, 158, 11, 0.15);
  color: var(--status-warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.account-badge.live {
  background: rgba(239, 68, 68, 0.15);
  color: var(--status-error);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
```

---

### Phase 2: Update AppHeader.vue

**Changes Required**:

1. **Remove**: `<AccountDataDisplay>` component from header-actions
2. **Replace**: `<AccountSelector>` with new `<HeaderAccountInfo>`
3. **Update**: Mobile menu to include account info section

**Desktop (>768px)**:
```vue
<div class="header-actions">
  <!-- NEW: Unified compact account info -->
  <HeaderAccountInfo v-if="authStore.isAuthenticated" class="desktop-nav" />

  <!-- Existing nav buttons remain unchanged -->
  <button class="btn-prompt desktop-nav" ...>ACCOUNTS</button>
  <button class="btn-prompt desktop-nav btn-alpaca" ...>ALPACA</button>
  <!-- ... rest of navigation -->
</div>
```

**Mobile Menu (≤768px)**:
```vue
<div v-if="mobileMenuOpen" class="mobile-dropdown">
  <!-- Account section at top of mobile menu -->
  <div v-if="authStore.isAuthenticated" class="mobile-account-section">
    <div class="mobile-account-header">
      <span class="mobile-account-label">Active Account</span>
      <span class="mobile-account-badge" :class="accountType">{{ accountType }}</span>
    </div>
    <AccountSelector class="mobile-account-selector" />
    <div class="mobile-account-metrics">
      <div class="mobile-metric">
        <span class="metric-label">Buying Power</span>
        <span class="metric-value">{{ formattedBuyingPower }}</span>
      </div>
    </div>
  </div>

  <!-- Rest of mobile menu items -->
  <button class="mobile-menu-item" ...>MANAGE ACCOUNTS</button>
  <!-- ... -->
</div>
```

---

### Phase 3: Responsive Breakpoints

**768px Breakpoint** (Desktop nav → Hamburger):
```css
@media (max-width: 768px) {
  .header-account-info.desktop-nav {
    display: none;  /* Hide compact display, moves to mobile menu */
  }

  .mobile-account-section {
    display: block;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-tertiary);
  }
}
```

**650px Breakpoint** (Touch optimization):
```css
@media (max-width: 650px) {
  .mobile-account-section {
    padding: 16px;
  }

  .mobile-account-selector :deep(.el-input__wrapper) {
    min-height: 44px;  /* Touch target */
  }

  .mobile-metric .metric-value {
    font-size: 1rem;  /* Larger for readability */
  }
}
```

---

### Phase 4: Button Styling (Apply Design Standards)

**All navigation buttons follow this pattern**:
```css
.btn-prompt {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-prompt:hover:not(:disabled) {
  background: var(--bg-quaternary);
  color: var(--text-primary);
  border-color: var(--accent-primary);
  transform: translateY(-1px);
}

.btn-prompt.active {
  background: var(--accent-primary);
  color: white;
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
}
```

**Mobile touch targets (≤650px)**:
```css
@media (max-width: 650px) {
  .btn-prompt {
    min-height: 44px;
    min-width: 44px;
    padding: 0.5rem 0.75rem;
  }
}
```

---

## Visual Comparison

### Before (Current State)
```
[CASH-DASH • Connected]                    [Dropdown ▼]  [======== WHITE CARD ========]  [NAV BUTTONS]
                                                         |  Active Account    PAPER   |
                                                         |  Balance  Equity   BP      |
                                                         |  $547K    $953K    $1.3M   |
                                                         ============================
```

### After (Proposed Design)
```
[CASH-DASH • Connected]     [Joe ▼ | BP $1,318,970.80 | PAPER]  [ACCOUNTS] [ALPACA] [POSITIONS] [CALENDAR] [TRADE STATS] [LOGOUT]
                            └─────────────────────────────────┘
                                  Dark themed, compact inline
```

---

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `src/components/HeaderAccountInfo.vue` | **CREATE** | New compact account display component |
| `src/components/AppHeader.vue` | **MODIFY** | Replace AccountDataDisplay with HeaderAccountInfo |
| `src/components/AccountDataDisplay.vue` | **KEEP** | May still be useful on /accounts page |
| `src/styles/global.css` | **MODIFY** | Add CSS custom properties for account badges |

---

## Implementation Checklist

- [ ] Create `HeaderAccountInfo.vue` component
- [ ] Apply dark theme styling (no white backgrounds)
- [ ] Implement buying power metric with tabular-nums
- [ ] Add account type badge (paper/live colors)
- [ ] Integrate into AppHeader.vue
- [ ] Update mobile menu with account section
- [ ] Apply responsive breakpoints (768px, 650px)
- [ ] Ensure 44px touch targets on mobile
- [ ] Test with browser validation (agent-browser)
- [ ] Verify on mobile viewports (375px, 650px, 768px)

---

## Success Criteria

1. **Theme Consistency**: Account info matches dark header theme (no white cards)
2. **Compact**: Occupies ≤200px width on desktop header
3. **Key Metrics Visible**: Buying power and account type badge always visible
4. **Nickname Shows**: Selected account nickname displayed in dropdown trigger
5. **Mobile Friendly**: Clean collapse to mobile menu at 768px
6. **Touch Accessible**: 44×44px minimum touch targets on mobile

---

## Estimated Effort

| Task | Estimate |
|------|----------|
| Create HeaderAccountInfo.vue | 45 min |
| Integrate into AppHeader.vue | 30 min |
| Mobile menu account section | 30 min |
| Responsive CSS | 30 min |
| Browser validation testing | 30 min |
| **Total** | ~2.5 hours |

---

## Browser Validation Plan

After implementation, validate using agent-browser skill:

```bash
# Desktop validation
agent-browser open http://localhost:5175
agent-browser screenshot ./playwright-reports/header-desktop.png

# Tablet validation (768px)
agent-browser set viewport 768 1024
agent-browser screenshot ./playwright-reports/header-tablet.png

# Mobile validation (650px)
agent-browser set viewport 650 844
agent-browser snapshot -i  # Check touch targets
agent-browser click @hamburger
agent-browser screenshot ./playwright-reports/header-mobile-menu.png

# Small mobile (375px)
agent-browser set viewport 375 667
agent-browser screenshot ./playwright-reports/header-mobile-small.png
```
