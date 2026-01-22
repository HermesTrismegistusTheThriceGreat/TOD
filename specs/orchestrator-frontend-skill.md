# Plan: Orchestrator Frontend Vue.js Skill

## Task Description
Build a comprehensive skill for working on the Orchestrator Frontend Vue.js application. The skill will provide deep knowledge of the frontend architecture, page organization, component interactions, WebSocket implementation, and state management patterns. It will have access to three Vue MCP subagents (PrimeVue, Vuetify, and shadcn-vue) that can be invoked in parallel or sequentially depending on the use case.

## Objective
Create a skill that enables Claude to quickly implement new features, design pages, and understand the Orchestrator Frontend codebase with intimate knowledge of how the application is structured and organized. The skill should leverage the appropriate Vue component library subagent based on the user's needs.

## Problem Statement
The Orchestrator Frontend is a complex Vue 3 + TypeScript application with multiple view modes, real-time WebSocket streaming, Pinia state management, and various trading-related features. Without a dedicated skill, implementing new features requires extensive codebase exploration. This skill will:

1. Provide comprehensive documentation of the frontend architecture
2. Enable quick navigation to relevant files and patterns
3. Offer guidance on which Vue component library to use for different scenarios
4. Streamline feature implementation with the right component library MCP tools

## Solution Approach
Create a multi-section skill that documents:
- Frontend directory structure and file organization
- Page/view architecture and routing
- Component communication patterns
- WebSocket integration and real-time data flow
- State management via Pinia store
- API integration patterns
- Subagent selection criteria for PrimeVue, Vuetify, and shadcn-vue

The skill will delegate to the appropriate Vue MCP subagent when the user needs to:
- Search for components
- Get component API documentation
- Explore design tokens and theming
- Install or customize components

## Relevant Files

### Existing MCP Agent Configurations
- `.claude/agents/primevue-mcp.md` - PrimeVue component library specialist (90+ components, data-heavy apps)
- `.claude/agents/vuetify-mcp.md` - Vuetify Material Design specialist (comprehensive API, accessibility)
- `.claude/agents/shadcn-vue-mcp.md` - shadcn-vue specialist (custom-branded apps, Tailwind CSS, code ownership)

### Frontend Core Files
- `apps/orchestrator_3_stream/frontend/src/main.ts` - Vue 3 entry point with Pinia and Element Plus
- `apps/orchestrator_3_stream/frontend/src/App.vue` - Root layout with 3-column grid and view mode switching
- `apps/orchestrator_3_stream/frontend/src/router/index.ts` - Vue Router with authentication guards

### State Management
- `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts` - Central Pinia store (agents, events, chat, WebSocket, ADW, Alpaca)
- `apps/orchestrator_3_stream/frontend/src/stores/authStore.ts` - Better Auth session management

### Views
- `apps/orchestrator_3_stream/frontend/src/views/HomeView.vue` - Main dashboard (protected)
- `apps/orchestrator_3_stream/frontend/src/views/LoginView.vue` - Login page
- `apps/orchestrator_3_stream/frontend/src/views/SignupView.vue` - Signup page

### Main Components
- `apps/orchestrator_3_stream/frontend/src/components/AppHeader.vue` - Header bar with stats
- `apps/orchestrator_3_stream/frontend/src/components/AgentList.vue` - Left sidebar agent cards
- `apps/orchestrator_3_stream/frontend/src/components/EventStream.vue` - Center event log stream
- `apps/orchestrator_3_stream/frontend/src/components/OrchestratorChat.vue` - Right sidebar chat
- `apps/orchestrator_3_stream/frontend/src/components/GlobalCommandInput.vue` - Cmd+K overlay

### Feature Components
- `apps/orchestrator_3_stream/frontend/src/components/AdwSwimlanes.vue` - ADW workflow visualization
- `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue` - Trading positions
- `apps/orchestrator_3_stream/frontend/src/components/TradeStatsGrid.vue` - Trade statistics
- `apps/orchestrator_3_stream/frontend/src/components/CalendarPage.vue` - Calendar view

### Composables
- `apps/orchestrator_3_stream/frontend/src/composables/useEventStreamFilter.ts` - Event filtering logic
- `apps/orchestrator_3_stream/frontend/src/composables/useAgentPulse.ts` - Agent animation state
- `apps/orchestrator_3_stream/frontend/src/composables/useKeyboardShortcuts.ts` - Global keyboard handlers
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts` - Real-time price streaming
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts` - Position management

### Services
- `apps/orchestrator_3_stream/frontend/src/services/api.ts` - Axios HTTP client
- `apps/orchestrator_3_stream/frontend/src/services/chatService.ts` - Chat HTTP + WebSocket (30+ message types)
- `apps/orchestrator_3_stream/frontend/src/services/agentService.ts` - Agent CRUD
- `apps/orchestrator_3_stream/frontend/src/services/eventService.ts` - Event history retrieval
- `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts` - Alpaca trading API

### Types and Config
- `apps/orchestrator_3_stream/frontend/src/types.d.ts` - TypeScript interfaces (mirrors database models)
- `apps/orchestrator_3_stream/frontend/src/types/trades.ts` - Trading types
- `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts` - Alpaca API types
- `apps/orchestrator_3_stream/frontend/src/config/constants.ts` - App constants

### Build Configuration
- `apps/orchestrator_3_stream/frontend/vite.config.ts` - Vite build config
- `apps/orchestrator_3_stream/frontend/tsconfig.json` - TypeScript config
- `apps/orchestrator_3_stream/frontend/.env` - Environment variables

### New Files to Create
- `.claude/skills/orchestrator-frontend/SKILL.md` - Main skill definition

## Implementation Phases

### Phase 1: Foundation
- Create skill directory structure
- Write YAML frontmatter with proper name and description
- Define skill purpose and prerequisites

### Phase 2: Core Implementation
- Document frontend architecture comprehensively
- Create subagent selection guide with decision tree
- Write workflow section with Task tool delegation patterns
- Include detailed file inventory and patterns

### Phase 3: Integration & Polish
- Add practical examples for common use cases
- Include troubleshooting section
- Document WebSocket message types and handlers
- Create quick reference tables

## Step by Step Tasks

### 1. Create Skill Directory
- Create `.claude/skills/orchestrator-frontend/` directory
- This follows the established skill directory pattern

### 2. Write SKILL.md with YAML Frontmatter
- `name`: `working-on-orchestrator-frontend` (gerund form, kebab-case)
- `description`: Third-person voice describing what it does AND when to use it
- Include trigger keywords: orchestrator frontend, vue pages, frontend component, UI implementation

### 3. Write Purpose Section
- Describe the skill's role as a frontend specialist
- List the three available MCP subagents with brief descriptions
- State when to use this skill vs direct exploration

### 4. Document Prerequisites
- Node.js 18+ installed
- MCP config files for each subagent
- Orchestrator Frontend codebase

### 5. Create Subagent Selection Guide
- Write detailed comparison of PrimeVue, Vuetify, and shadcn-vue
- Include decision tree for selecting the right subagent
- Document best use cases for each:
  - **PrimeVue**: Data-heavy enterprise apps, dashboards, 90+ components, DataTable with virtual scrolling
  - **Vuetify**: Material Design compliance, accessibility focus, comprehensive API documentation
  - **shadcn-vue**: Custom-branded apps, full code control, Tailwind CSS, design differentiation

### 6. Document Frontend Architecture
- Directory structure with purpose annotations
- File organization patterns
- Entry point and plugin initialization

### 7. Document Page/View Architecture
- Router configuration and authentication guards
- View modes: logs, adws, open-positions, calendar, trade-stats
- Layout switching mechanism
- Responsive grid system

### 8. Document Component Communication Patterns
- Props down, events up pattern
- Composable injection pattern
- Store-based communication via Pinia
- Ref-based component access pattern

### 9. Document WebSocket Implementation
- Connection establishment flow
- Message type routing (30+ types)
- Reconnection logic with exponential backoff
- RAF batching for high-frequency updates

### 10. Document State Management
- Pinia store architecture
- State sections (agents, events, chat, ADW, Alpaca)
- Getters and computed properties
- Action patterns

### 11. Create Workflow Section
- How to parse user requests
- When to delegate to which subagent
- Task tool invocation patterns for each MCP agent
- Parallel vs sequential subagent usage

### 12. Write Examples Section
- Example 1: Add a new page/view to the dashboard
- Example 2: Create a new component using PrimeVue
- Example 3: Build custom-branded component with shadcn-vue
- Example 4: Implement Material Design feature with Vuetify
- Example 5: Add WebSocket event handler
- Example 6: Create new composable

### 13. Add Quick Reference Tables
- File location table by feature area
- WebSocket message types table
- Component hierarchy diagram
- View mode configuration table

### 14. Add Troubleshooting Section
- Common issues and resolutions
- MCP config verification steps
- Build and type errors

### 15. Validate Skill Structure
- Verify YAML frontmatter is valid
- Check all file paths are correct
- Ensure skill follows meta-skill template

## Testing Strategy
- Verify skill loads correctly in Claude Code
- Test subagent delegation works for each MCP agent
- Validate file paths are accurate
- Test trigger keywords activate the skill

## Acceptance Criteria
- [ ] Skill file created at `.claude/skills/orchestrator-frontend/SKILL.md`
- [ ] YAML frontmatter follows naming conventions (gerund form, kebab-case)
- [ ] Description includes both "what it does" AND "when to use it"
- [ ] All three MCP subagents documented with use cases
- [ ] Decision tree for subagent selection included
- [ ] Frontend architecture comprehensively documented
- [ ] WebSocket implementation documented with message types
- [ ] At least 5 practical examples provided
- [ ] Task tool delegation patterns included for each subagent
- [ ] Quick reference tables included
- [ ] Troubleshooting section added

## Validation Commands
Execute these commands to validate the task is complete:

- `cat .claude/skills/orchestrator-frontend/SKILL.md | head -10` - Verify YAML frontmatter exists
- `ls -la .claude/agents/*vue*.md` - Confirm MCP agent files exist
- `grep -l "orchestrator-frontend" .claude/skills/*/SKILL.md` - Verify skill is discoverable

## Notes

### Subagent Best Use Cases Summary

| Subagent | Best For | Key Features |
|----------|----------|--------------|
| **PrimeVue** | Data-heavy enterprise apps, dashboards, admin panels | 90+ components, DataTable with virtual scrolling, TreeTable, design-agnostic themes |
| **Vuetify** | Material Design apps, accessibility-critical projects | Comprehensive API docs, strong ARIA support, version-specific guidance, directives |
| **shadcn-vue** | Custom-branded apps, design differentiation | Code ownership, Tailwind CSS, Radix Vue primitives, no dependency lock-in |

### Current Frontend Stack
- **Framework**: Vue 3 with TypeScript
- **Build Tool**: Vite 5.x
- **State Management**: Pinia
- **UI Library**: Element Plus (currently used)
- **HTTP Client**: Axios
- **Authentication**: Better Auth
- **Styling**: CSS custom properties + global.css dark theme

### Key Architectural Decisions
1. **Single Pinia Store**: All state centralized in orchestratorStore.ts
2. **WebSocket Callback Pattern**: 30+ message types routed via switch statement
3. **RAF Batching**: High-frequency Alpaca price updates batched per animation frame
4. **View Mode System**: Dynamic center column switching based on store.viewMode
5. **Auth Guards**: Router-level protection with session loading detection
