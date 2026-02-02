# Feature Landscape: Multi-Account Trading Platform

**Domain:** Alpaca trading platform with multi-user, multi-account support
**Research Date:** January 29, 2026
**Context:** Small trusted group (friends), internal tool, not public-facing
**Confidence:** HIGH for table stakes and common patterns; MEDIUM for anti-features in small-group context

## Table Stakes

Features users expect. Missing = product feels incomplete for multi-account trading.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Account Selector/Dropdown | Core UX for switching between multiple accounts. Users expect instant ability to see which account is active and switch quickly. Standard in every multi-account platform (3Commas, Bitsgap, WunderTrading, crypto trading bots). | Low | Top-right dropdown showing current account, other accounts available. Must show account type (paper/live) and balance/status at a glance. Reference: Proven pattern across major trading platforms. |
| API Credential Storage | Users must securely store Alpaca API keys for each account without exposing them. Every multi-account platform requires this. | Medium | Need secure vault; credentials should never appear in UI. Follow Alpaca best practice: IP whitelisting, 2FA-enabled keys, read-only vs trading keys separated. |
| Account Metadata Display | Quick visual distinction between accounts. Minimum: account type (paper/live), account balance/buying power, associated user. | Low | Prevents dangerous accidents (e.g., trading live when expecting paper). |
| Per-Account Balance/Equity Display | Real-time cash, equity, and buying power for the active account. Non-negotiable for trading safety. | Low | Auto-update on trades. Clear visibility of margin usage if applicable. |
| Trade Execution within Account Context | All trades execute against the currently-selected account. The platform must prevent accidental cross-account trades. | Medium | State machine: validate account selection before ANY execution. |
| Order History per Account | See what trades were executed in each account separately. Critical for debugging and reconciliation. | Low | Time-series view, filterable by account. |
| Account-Scoped Market Data | Data (prices, positions, holdings) must always reflect the selected account, not aggregate or cross-account. | Medium | Refresh on account switch. Validate data freshness. |
| Logout/Session Management | Users must be able to log out and switch between different user accounts (multi-tenant concern). | Low | Standard auth, but must clear account context on logout. |
| Credential Rotation/Renewal | Way to update API keys when they expire or need rotation (Alpaca requirement for security). | Medium | Don't delete old keys until new ones are tested. Warning before expiration. |

## Differentiators

Features that set the product apart. Not expected by default, but highly valued in trading platforms.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Account Comparison Dashboard | Side-by-side view of multiple accounts' performance, P&L, positions. Helps friends track collective progress and spot divergences. | High | Shows aggregate stats, individual stats, comparative metrics (returns %, sharpe, max drawdown). |
| Unified Position View with Account Tags | See all open positions across all accounts, tagged by account owner or account type. Helps spot portfolio conflicts (same position in multiple accounts). | High | Could identify hedging opportunities or redundant positions. |
| Paper-to-Live Migration Checklist | Guided workflow to transition a tested paper strategy to live trading. Reduces accidental mistakes. | Medium | Validation that strategy performed well in paper, checklist of pre-flight conditions, staged rollout (e.g., 10% position size first). |
| API Key Rotation Workflow | Automated guide to safely rotate API keys: generate new, test with small trade, deprecate old. | Medium | Prevents the common "API key mismatch" error where old keys are still referenced in jobs or configurations. Reference: Real failure case from 2026 (Lesson #119). |
| Alert Rules per Account | Set up alerts (e.g., "notify me if paper account equity < $5000" or "live account has > 50% allocation to AAPL"). | Medium | Multi-channel: in-app, email, Slack integration. |
| Trading History Export | Export account trades to CSV for tax reporting, journal analysis. | Low | Standard feature, but critical for compliance and personal record-keeping. |
| Account Audit Log | Who accessed which account, when, from where, what actions taken. Useful for small trusted group to track who did what. | Medium | Immutable log. Timestamps, IP addresses, action descriptions. |
| Simulated Trading Reconciliation | Paper account balance must exactly match what the simulator says vs. Alpaca backend. Validation tool to catch stale data. | Medium | Catches bugs early. Show deltas if reconciliation fails. |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain that don't fit a small trusted group.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Role-Based Access Control (RBAC) / Permission Matrix | Tempting but over-engineering for "small trusted group." Creates complexity: admin vs trader vs viewer roles, permission inheritance, role definitions. This is enterprise stuff. For trusted friends, you're either in or out. | Trust all users equally. Either they have full access to your accounts or they don't. If granularity needed later (e.g., "Alice can only view, Bob can trade"), revisit this then. Start simple: login = full access to own accounts and friends' accounts. |
| Copy Trading / Trade Replication | Seems like a feature (automatically replicate Alice's trades to Bob's account) but creates compliance risks, liability questions, and execution complexity. Plus: lag, slippage, different account equity = different position sizes. | If friends want to share strategy, use shared paper account or documented signal channel. Execution stays per-person, per-account. No automatic mirroring. |
| Account Consolidation / Unified P&L Reporting for Compliance | Aggregating P&L across multiple accounts triggers SEC/FINRA reporting requirements depending on account structure. Opens regulatory complexity. | Keep account P&L separate. Each user responsible for their own account reporting. Aggregate views are for informational use only, not compliance documents. |
| Advanced Portfolio Optimization / Rebalancing Across Accounts | Algorithmic rebalancing that moves positions between accounts to optimize for risk, correlation, tax efficiency. Overkill for a small group. | Manual portfolio reviews. Friends decide themselves what to rebalance. Could add a "suggested rebalance" view, but no auto-execution. |
| Institutional Account Types (Broker API, OmniSub) | Alpaca's OmniSub model and Broker API allow managing 100s of sub-accounts under one legal entity. Requires partnership agreement, compliance overhead. Not appropriate here. | Stick with individual Alpaca accounts (paper + live) per person. Each friend owns their own account. No sub-account relationships. |
| Tiered Account Hierarchy / Master-Sub Account Model | Create parent accounts that control child accounts, with wealth aggregation and delegation. Adds legal, tax, compliance complexity. | Simple peer model: each friend has their own account(s). Sharing happens at UI/data level, not account ownership level. |
| Real-Time Trade Propagation / Synchronization Across Accounts | Advanced platforms sync trades in near real-time to multiple accounts. Introduces failure modes: latency, partial execution, reconciliation bugs. See pitfall: copy trading failures. | If synchronization is needed, make it async, logged, and manual approval required. Better: avoid this entirely. Each person trades their own account. |
| Multi-Currency Support | Tempting feature but adds complexity: currency pairs in Alpaca, conversion rates, FX hedging. Alpaca primarily supports USD and crypto. | For crypto: Alpaca handles it natively. For US stocks: USD only. Don't add multi-currency layer. |
| Advanced Compliance Monitoring (Position Limits, PDT Rules, Margin Alerts) | Could auto-enforce trading rules across group (e.g., "no account can hold > 50% in single stock"). Adds complexity and may conflict with Alpaca's own limits. | Educate users on Alpaca's PDT rules, margin requirements, position limits. Let them self-manage. Add simple read-only warnings, not enforcement. |
| Fractional Share / Micro-Account Support | Some platforms support fractional shares to lower barrier to entry. Alpaca has nuances here. | Use Alpaca's native fractional share support if available. Don't build custom fractional share logic on top. |
| Social Features / Leaderboards / Performance Comparison | Tempting for "friends trading together" but creates peer pressure, risk-taking encouragement, liability. | Avoid. This is a small trusted group, not a public trading social network. P&L is private. No gamification. |

## Feature Dependencies

```
Core Dependencies:
┌─────────────────────────────────────────────────┐
│ User Authentication & Login                     │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ Account Selector/Dropdown                       │
│ (must know all user's accounts from auth info)  │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Credential     Account         Order History
   Storage        Metadata        per Account
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Trade Execution Context     │
        │ (validates account before   │
        │  any order execution)       │
        └────────────────────────────┘
                       │
        ┌──────────────▼──────────────────────┐
        │ Per-Account Balance/Equity Display  │
        │ (real-time update after trade)      │
        └────────────────────────────────────┘

Optional Enhancements:
Account Comparison Dashboard → depends on Balance/Equity Display
Unified Position View → depends on Account Metadata Display
Alert Rules → depends on Account Metadata Display
Audit Log → depends on Trade Execution Context
```

**Key Dependency Notes:**
- Account Selector must come first; everything else assumes a selected account context.
- Credential Storage must be in place before any API calls.
- Trade Execution Context is a safety layer; it's not a feature but a requirement.
- Balance/Equity updates must be atomic with order execution to prevent stale data bugs.

## MVP Recommendation

For MVP, prioritize in this order:

1. **User Authentication & Multi-Tenant Setup** - Foundation for everything else. Each friend logs in, sees only their own account(s).
2. **Account Selector Dropdown** - Core UX. Users must be able to switch between paper and live easily.
3. **API Credential Secure Storage** - Non-negotiable for production. Use secure vault (not env vars, not plaintext).
4. **Account Metadata Display** - Show account type, balance, equity, buying power. Prevents dangerous mistakes.
5. **Order History per Account** - Users need to see what they've traded and verify the account executed correctly.

**Phase 2 (Post-MVP):**
- Trade Execution within Account Context with safety validation
- Per-Account Balance/Equity Real-Time Display
- Credential Rotation/Renewal Workflow
- Account Audit Log (who did what when)

**Phase 3 (If Time/Interest):**
- Account Comparison Dashboard (nice-to-have for tracking friends' progress)
- Alert Rules per Account
- Paper-to-Live Migration Checklist

**Explicitly Defer:**
- Copy Trading (too complex, liability risk)
- RBAC / Permission Matrix (overkill for small group)
- Social Features / Leaderboards (wrong fit for small trusted group)
- Compliance Aggregation (each account is independent)

## Sources

**Multi-Account Platform Features:**
- [Forex Multi-Account Manager Software - UpTrader](https://uptrader.io/en/articles/289/forex-multi-account-manager-software-top-6-solutio)
- [Multiple Account Management for Crypto Exchanges - WunderTrading](https://wundertrading.com/en/multiple-account-management)
- [Top 5 Multi-Exchange Crypto Trading Platforms in 2026 - Brave New Coin](https://bravenewcoin.com/sponsored/article/top-5-multi-exchange-crypto-trading-platforms-in-2026)
- [Multi-Account Manager - Tickmill](https://www.tickmill.com/partners/multi-account-manager)

**UI/UX Patterns:**
- [Successful Investment Platform UI/UX Best Practices - Ron Design Lab](https://rondesignlab.com/blog/design-news/most-sucessful-practices-for-investment-platform-ui-ux)
- [Trading Platform UX/UI Latest Trends - Devexperts](https://devexperts.com/blog/trading-platform-ux-ui-latest-trends/)
- [Designing Account Switchers & App Switchers - Jon Moore, UX Power Tools](https://medium.com/ux-power-tools/ways-to-design-account-switchers-app-switchers-743e05372ede)
- [Breaking Down the UX of Switching Accounts in Web Apps - Christian Beck, UX Power Tools](https://medium.com/ux-power-tools/breaking-down-the-ux-of-switching-accounts-in-web-apps-501813a5908b)

**Alpaca-Specific:**
- [Trading Account - Alpaca Docs](https://docs.alpaca.markets/docs/account-plans)
- [Can You Have Multiple Alpaca Accounts - Multilogin](https://multilogin.com/blog/can-you-have-multiple-alpaca-accounts/)
- [Paper Trading vs Live Trading - Alpaca Learn](https://alpaca.markets/learn/paper-trading-vs-live-trading-a-data-backed-guide-on-when-to-start-trading-real-money)

**Credential & Security Management:**
- [API Credential Management Best Practices - API Payments Developer](https://developer.payments.jpmorgan.com/blog/product/api-credential-management)
- [5 Common API Security Mistakes and How to Avoid Them - Cybersecurity News](https://cybersecuritynews.com/5-common-api-security-mistakes-and-how-to-avoid-them/)
- [API Security Trends 2026 - Curity](https://curity.io/blog/api-security-trends-2026/)
- [REST API Security Best Practices 2026 - Levo.ai](https://www.levo.ai/resources/blogs/rest-api-security-best-practices)

**Common Pitfalls & Mistakes:**
- [How to Trade Multiple Accounts Simultaneously - QuantVPS](https://www.quantvps.com/blog/trade-multiple-accounts-simultaneously)
- [Managing Multiple Prop Firm Accounts Without Execution Errors - Tradeify](https://tradeify.co/post/managing-multiple-prop-firm-accounts)
- [AI Trading Lesson #119: Paper Trading API Key Mismatch - DEV Community](https://dev.to/igorganapolsky/ai-trading-lesson-learned-119-paper-trading-api-key-mismatch-after-account-reset-9g1)

**Paper vs Live Trading:**
- [Paper Trading vs Live Trading - Interactive Brokers](https://www.interactivebrokers.com/campus/trading-lessons/paper-trading-vs-live-trading-whats-the-difference/)
- [How to Switch From Paper Trading to Live Trading - Real Trading](https://realtrading.com/trading-blog/from-paper-trading-to-live/)
- [From Paper Trading To Real Trading - IBKR Quant Blog](https://www.interactivebrokers.com/campus/ibkr-quant-news/from-paper-trading-to-real-trading-monitoring-debug-and-go-live/)
