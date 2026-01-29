# Alpaca Trading Chat

## What This Is

A mobile-friendly webapp where users log in, connect their own Alpaca trading accounts (paper or real money), and interact with the Alpaca MCP server through natural language chat. Users can have multiple accounts and switch between them via dropdown. Built for personal use with a small trusted group of friends.

## Core Value

Friends can log in, add their own Alpaca accounts, and trade via chat — each person controls their own money.

## Requirements

### Validated

- ✓ User authentication with email/password — existing (Neon/Better-Auth)
- ✓ Single-account Alpaca MCP chat — existing
- ✓ Real-time WebSocket streaming — existing
- ✓ Claude Agent SDK orchestration — existing
- ✓ Positions page with mobile responsiveness — existing

### Active

- [ ] Multi-user Alpaca account storage (users add their own API key + secret)
- [ ] Encrypted credential storage in database
- [ ] Account switching via dropdown (select active account)
- [ ] Per-user account isolation (users only see their own accounts)
- [ ] Chat executes against user's selected Alpaca account
- [ ] Mobile responsiveness audit and fixes across all pages

### Out of Scope

- OAuth login (Google/GitHub) — v2, email/password sufficient for friends
- AI model choice (Claude vs Kimi) — v2, Claude works for now
- Public signup/onboarding — friends only, manual invite acceptable
- Trade confirmations or safety gates — users own their decisions

## Context

**Brownfield project.** The core Alpaca chat already works for a single hardcoded paper account. This project extends it to support multiple users with their own accounts.

**Existing architecture:**
- FastAPI backend with WebSocket streaming
- Vue 3 frontend with Pinia state management
- PostgreSQL on NeonDB with Better-Auth
- Claude Agent SDK for agent orchestration
- Alpaca MCP server for trading operations

**What works today:**
- Login/logout flow
- Chat interface sends messages to Claude agent
- Agent calls Alpaca MCP tools
- Results stream back via WebSocket
- Positions page displays account data

**What's hardcoded:**
- Alpaca API credentials (single account in env vars or config)
- No user-to-account relationship in database

## Constraints

- **Security**: Alpaca credentials must be encrypted at rest — these control real money
- **Database**: Continue using NeonDB PostgreSQL — auth and schema already there
- **Frontend**: Vue 3 + existing component library — no framework switch
- **Backend**: FastAPI — no framework switch
- **Users**: Small trusted group — no need for elaborate abuse prevention

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Same UX for paper and live accounts | User trust, simpler interface | — Pending |
| Server-side credential storage | Users can access from any device | — Pending |
| Multiple accounts per user with dropdown | Flexibility for testing vs live | — Pending |
| Claude-only for v1 | Simplicity, works today | — Pending |

---
*Last updated: 2026-01-29 after initialization*
