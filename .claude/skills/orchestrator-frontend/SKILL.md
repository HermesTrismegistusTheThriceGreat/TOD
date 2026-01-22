---
name: working-on-orchestrator-frontend
description: Orchestrator Frontend Vue.js specialist for building and designing pages. Use when implementing features in the Orchestrator UI, creating new Vue components, understanding page interactions, working with WebSockets on the frontend, or when needing guidance on PrimeVue, Vuetify, or shadcn-vue component libraries. Delegates to primevue-mcp, vuetify-mcp, or shadcn-vue-mcp subagents for component library operations. ALL frontend work MUST be validated using the agent-browser skill for visual browser testing.
---

# Working on Orchestrator Frontend

A comprehensive skill for implementing features, designing pages, and understanding the Orchestrator Frontend Vue.js application. This skill provides intimate knowledge of the codebase architecture and access to three specialized Vue component library subagents.

**CRITICAL: All frontend UI work MUST be validated using the `agent-browser` skill.** Standard code-based testing is valuable, but the final and paramount test is always seeing it work in the browser. Never consider frontend work complete until it has been visually validated in a real browser using agent-browser.

## Quick Reference

### Key Files
| Purpose | Path |
|---------|------|
| Entry | `src/main.ts` |
| Root | `src/App.vue` |
| Router | `src/router/index.ts` |
| Store | `src/stores/orchestratorStore.ts` |
| Types | `src/types.d.ts` |
| WebSocket | `src/services/chatService.ts` |

### View Modes
| Mode | Component | Layout |
|------|-----------|--------|
| `logs` | EventStream | 3-column |
| `adws` | AdwSwimlanes | 3-column |
| `open-positions` | OpenPositions | 1-column |
| `calendar` | CalendarPage | 1-column |
| `trade-stats` | TradeStatsGrid | 1-column |

### WebSocket Events (Common)
- **Chat**: `chat_stream`, `chat_typing`, `orchestrator_chat`
- **Agent**: `agent_log`, `agent_created`, `agent_updated`, `agent_status_changed`
- **Claude SDK**: `thinking_block`, `tool_use_block`
- **ADW**: `adw_created`, `adw_updated`, `adw_step_change`
- **Alpaca**: `option_price_update`, `spot_price_update`, `position_update`

### Technology Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Vue | 3.4.x | Core framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Pinia | 2.1.x | State management |
| Vue Router | 4.4.x | Client-side routing |
| Element Plus | 2.13.x | Current UI components |
| Better Auth | 1.4.x | Authentication |

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:9403` | Backend API URL |
| `VITE_WEBSOCKET_URL` | `ws://127.0.0.1:9403/ws` | WebSocket endpoint |
| `VITE_AUTH_URL` | `http://localhost:9404` | Auth service URL |

## Available Subagents

This skill has access to three Vue MCP subagents that can be invoked in parallel or sequentially:

### PrimeVue MCP (`primevue-mcp`)
**Best for:** Data-heavy enterprise applications, dashboards, admin panels

**MCP Tools:**
- `mcp__primevue__search_components` - Search by name, title, or description
- `mcp__primevue__list_components` - List all components with categories
- `mcp__primevue__get_component` - Get props, events, slots, examples
- `mcp__primevue__search_tokens` - Find design tokens for theming

### Vuetify MCP (`vuetify-mcp`)
**Best for:** Material Design compliance, accessibility-critical projects

**MCP Tools:**
- `mcp__vuetify__get_component_api_by_version` - Component specs (props, events, slots)
- `mcp__vuetify__get_directive_api_by_version` - Directives (v-ripple, v-scroll, v-intersect)
- `mcp__vuetify__get_installation_guide` - Setup for Vite, Nuxt, Vue CLI
- `mcp__vuetify__get_available_features` - List all components and composables

### shadcn-vue MCP (`shadcn-vue-mcp`)
**Best for:** Custom-branded applications, design differentiation, full code control

**Key Features:**
- Code ownership, Tailwind CSS utilities, Radix Vue primitives
- Browse, search, and install components from registry
- Handle dependencies automatically

### Agent Browser (`agent-browser` skill) - REQUIRED FOR ALL FRONTEND WORK
**Purpose:** Visual browser validation - the FINAL test for all frontend implementations

**Why This Is Paramount:**
- Code-based tests verify logic, but only browser validation confirms the UI works as users will experience it
- Visual regressions, layout issues, and interaction problems are only caught in real browser testing
- **Every frontend PR should include browser validation evidence**

**Capabilities:**
- Navigate to pages and take screenshots (`agent-browser screenshot`)
- Interact with UI elements via refs (`agent-browser click @e1`, `agent-browser fill @e2 "text"`)
- Validate responsive layouts at different viewport sizes (`agent-browser set viewport 1920 1080`)
- Verify WebSocket-driven UI updates in real-time
- Record video demos of features (`agent-browser record start ./demo.webm`)
- Extract element text, values, and state for assertions
- Full page accessibility tree analysis (`agent-browser snapshot -i`)

## Workflows

### Workflow 1: Understanding the Codebase

When asked about architecture or existing features:

1. **Identify the area** - Routing, state, layout, components, services?
2. **Read relevant files** directly:
   - Routing: `src/router/index.ts`
   - State: `src/stores/orchestratorStore.ts`
   - Layout: `src/App.vue`
   - Components: `src/components/[ComponentName].vue`
   - Services: `src/services/[serviceName].ts`
3. **Reference expertise.yaml** for complete inventories if needed

### Workflow 2: Adding a New View Mode

1. **Read existing patterns**
   - `src/App.vue` - View mode switching logic
   - `src/stores/orchestratorStore.ts` - ViewMode type
2. **Create new component** at `src/components/[ViewName].vue`
3. **Update types** - Add to ViewMode union in `src/types.d.ts`
4. **Update layout** - Add conditional rendering in `src/App.vue`
5. **Add toggle** - Add button in `src/components/AppHeader.vue`

### Workflow 3: Creating a New Vue Component

1. **Determine component type** - View, core UI, or specialized?
2. **Read similar components** for patterns
3. **Follow codebase conventions**:
   - Use `<script setup>` with TypeScript
   - Props via `defineProps<{ ... }>()`
   - Events via `defineEmits<{ ... }>()`
   - Access store via `const store = useOrchestratorStore()`
4. **Connect to state** - Read from store, call actions
5. **Test integration** - Verify in dev server

### Workflow 4: Adding WebSocket Event Handler

1. **Read** `src/services/chatService.ts` to understand message routing
2. **Add new case** to switch statement:
   ```typescript
   case 'your_event_type':
     callbacks.onYourEvent?.(message.data)
     break
   ```
3. **Add callback interface** - Update `WebSocketCallbacks` interface
4. **Add handler** in `src/stores/orchestratorStore.ts`:
   ```typescript
   onYourEvent: (data) => {
     // Update relevant state
   }
   ```
5. **Test with backend** - Verify event handling works end-to-end

### Workflow 5: Delegating to Component Library Subagents

When user needs component library guidance:

1. **Identify library need**:
   - Data-heavy tables/grids → PrimeVue
   - Material Design → Vuetify
   - Custom branded UI → shadcn-vue
2. **Use Task tool** to delegate:
   ```
   Task(
     subagent_type="primevue-mcp",
     prompt="Search for data table components with virtual scrolling support. Return component names, key props, and usage examples."
   )
   ```
3. **Parse subagent results**
4. **Adapt to codebase** - Apply component guidance following existing patterns
5. **Provide implementation code** - Complete, production-ready examples

### Workflow 6: Comparing Component Libraries

For open-ended component selection:

1. **Run subagents in parallel**:
   ```
   Task(subagent_type="primevue-mcp", prompt="Find [feature] components...")
   Task(subagent_type="vuetify-mcp", prompt="Find [feature] components...")
   Task(subagent_type="shadcn-vue-mcp", prompt="Find [feature] components...")
   ```
2. **Compare results** - Features, customization, consistency with codebase
3. **Recommend** based on requirements

### Workflow 7: Browser Validation - THE FINAL TEST (REQUIRED)

**This workflow is MANDATORY for all frontend implementations.** Code-based testing validates logic, but browser validation is the paramount final test that confirms the UI works as users will experience it.

After implementing UI changes, validate using the `agent-browser` skill:

1. **Ensure the app is running**:
   - Backend: `cd apps/orchestrator_3_stream/backend && uv run uvicorn main:app --port 9403`
   - Frontend: `cd apps/orchestrator_3_stream/frontend && npm run dev`
   - Or use the `start-orchestrator` skill to launch both

2. **Use the agent-browser skill** for visual validation:
   ```bash
   # Navigate to the page
   agent-browser open http://localhost:5175/[page-path]

   # Get interactive elements with refs
   agent-browser snapshot -i

   # Take a screenshot as evidence
   agent-browser screenshot ./playwright-reports/feature-validation.png

   # Interact with elements using refs from snapshot
   agent-browser click @e1
   agent-browser fill @e2 "test input"

   # Verify state after interaction
   agent-browser snapshot -i
   agent-browser screenshot ./playwright-reports/feature-after-interaction.png
   ```

3. **Common validation scenarios**:
   - **New view mode**: Navigate to page, verify layout renders, check responsive behavior
   - **New component**: Locate component on page, verify props display correctly
   - **WebSocket feature**: Connect, trigger event, verify UI updates in real-time
   - **Form/interaction**: Fill inputs, submit, verify response handling

4. **Example validation workflows**:
   ```bash
   # Validate new AlpacaAgent page
   agent-browser open http://localhost:5175/alpaca-agent
   agent-browser snapshot -i
   agent-browser screenshot ./playwright-reports/alpaca-agent-initial.png
   # Find chat input ref from snapshot, e.g., @e5
   agent-browser fill @e5 "test message"
   agent-browser click @e6  # Submit button ref
   agent-browser wait 2000
   agent-browser screenshot ./playwright-reports/alpaca-agent-response.png

   # Validate responsive layout
   agent-browser open http://localhost:5175
   agent-browser set viewport 1920 1080
   agent-browser screenshot ./playwright-reports/desktop.png
   agent-browser set viewport 768 1024
   agent-browser screenshot ./playwright-reports/tablet.png
   agent-browser set viewport 375 667
   agent-browser screenshot ./playwright-reports/mobile.png

   # Record a feature demo video
   agent-browser open http://localhost:5175/feature
   agent-browser record start ./playwright-reports/feature-demo.webm
   agent-browser snapshot -i
   agent-browser click @e1
   agent-browser fill @e2 "demo data"
   agent-browser click @e3
   agent-browser wait 2000
   agent-browser record stop
   ```

5. **Review screenshots/videos** and fix any issues found before considering the work complete

**Remember: Frontend work is NOT complete until browser validation confirms it works visually.**

## Component Communication Patterns

### Pattern 1: Props Down, Events Up
```vue
<!-- Parent: App.vue -->
<AgentList
  :agents="store.agents"
  :selected-agent-id="store.selectedAgentId"
  @select-agent="handleSelectAgent"
/>

<script setup>
const handleSelectAgent = (id: string) => {
  store.selectAgent(id)
}
</script>
```

### Pattern 2: Store-Based Communication
```typescript
// All components access shared state via Pinia
const store = useOrchestratorStore()

// Read state
store.agents
store.chatMessages
store.viewMode

// Call actions
store.selectAgent(id)
store.sendUserMessage(text)
store.setViewMode('logs')
```

### Pattern 3: Composable Injection
```typescript
// composables/useKeyboardShortcuts.ts
export function useKeyboardShortcuts() {
  const store = useOrchestratorStore()

  const handleKeyDown = (event: KeyboardEvent) => {
    if (isModifierPressed && event.key === 'k') {
      store.toggleCommandInput()
    }
  }

  onMounted(() => window.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))
}
```

### Pattern 4: Ref-Based Component Access
```typescript
// App.vue holds ref to child component
const eventStreamRef = ref<InstanceType<typeof EventStream> | null>(null)

// Call child methods directly
if (eventStreamRef.value) {
  eventStreamRef.value.toggleAgentFilter(agent.name)
}
```

## Layout & Routing

### Grid System
```css
/* 3-column layout (App.vue) */
.app-main {
  display: grid;
  grid-template-columns: 280px 1fr 418px; /* AgentList | Center | Chat */
}

/* Chat width variations */
.app-main.chat-md { grid-template-columns: 280px 1fr 518px; }
.app-main.chat-lg { grid-template-columns: 280px 1fr 618px; }

/* Sidebar collapsed */
.app-main.sidebar-collapsed { grid-template-columns: 48px 1fr 418px; }

/* Mobile responsive (<768px) */
@media (max-width: 768px) {
  .app-main { display: flex; flex-direction: column; }
}
```

### Authentication Guards
```typescript
// Router beforeEach guard (router/index.ts)
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Wait for session to load (3s timeout)
  if (authStore.isLoading) {
    await waitForSession(authStore, 3000)
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: 'Home' })
  } else {
    next()
  }
})
```

## WebSocket Implementation Patterns

### Connection with Reconnection
```typescript
// orchestratorStore.ts
function connectWebSocket() {
  const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 'ws://127.0.0.1:9403/ws'

  wsConnection = chatService.connectWebSocket(wsUrl, {
    onMessageReceived: () => incrementWebSocketEventCount(),
    onChatStream: handleChatStream,
    onAgentLog: (msg) => addAgentLogEvent(msg.log),
    onThinkingBlock: (msg) => addThinkingBlockEvent(msg.data),
    // ... 30+ more handlers
    onConnected: () => { isConnected.value = true },
    onDisconnected: () => { isConnected.value = false }
  }, () => {
    // Reconnection callback
    window.dispatchEvent(new CustomEvent('alpaca-reconnect'))
  })
}
```

### RAF Batching for High-Frequency Updates
```typescript
// orchestratorStore.ts - Prevent UI freeze from 1000+ price updates/second
const optionPriceBatcher = new RafBatcher<OptionPriceUpdate>((batch) => {
  batch.forEach(update => {
    alpacaPriceCache.value.set(update.symbol, update)
  })
  triggerRef(alpacaPriceCache) // Notify Vue of changes
})

// Usage
function queueAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
  optionPriceBatcher.add(update)
}
```

## Troubleshooting

### WebSocket Not Connecting
1. Check backend is running on port 9403
2. Verify `VITE_WEBSOCKET_URL` in `.env`
3. Check browser console for connection errors

### Type Errors After Adding New Feature
1. Update `src/types.d.ts` with new interfaces
2. Run `npm run type-check` to verify
3. Check store state matches interface definitions

### Component Not Rendering
1. Verify import statement is correct
2. Check component is registered (if not using `<script setup>`)
3. Verify conditional rendering logic (`v-if`, `v-show`)
4. Check browser DevTools Vue extension

### MCP Config Not Found
Ensure MCP configuration files exist at project root:
```bash
ls -la .mcp.json.primevue .mcp.json.vuetify .mcp.json.shadcn-vue
```

## Detailed Knowledge

For comprehensive details, reference the companion expertise file:

- **Component Inventory**: See `expertise.yaml` → `components` section
- **Complete WebSocket Events**: See `expertise.yaml` → `websocket.events` section
- **Store Structure**: See `expertise.yaml` → `store` section
- **File Locations**: See `expertise.yaml` → `file_locations` section
- **Composables & Services**: See `expertise.yaml` → `composables` and `services` sections

The expertise file contains complete inventories with paths, line numbers, and detailed specifications. Reference it when you need exhaustive details beyond the quick reference provided here.
