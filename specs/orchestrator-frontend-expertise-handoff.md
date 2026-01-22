# Handoff: Add Expertise System to Orchestrator Frontend Skill

## Goal

Add a self-improving expertise system to the existing `orchestrator-frontend` skill, combining:
- **Skill** (model-invoked workflows) + **Expertise** (self-improving knowledge)

## Current State

```
.claude/skills/orchestrator-frontend/
└── SKILL.md                    # 710 lines, all knowledge inline
```

## Target State

```
.claude/skills/orchestrator-frontend/
├── SKILL.md                    # ~300 lines (workflows + quick reference)
├── expertise.yaml              # ~600 lines (detailed knowledge, self-improving)
└── self-improve.md             # Validation prompt
```

## File Responsibilities

### SKILL.md (Entry Point)
- **Always in context** when skill activates
- Contains:
  - Frontmatter (name, description)
  - Quick Reference table (critical paths, 80% use cases)
  - Workflow instructions (how to add views, components, WebSocket handlers)
  - References to expertise.yaml for detailed info
- Target: **~300 lines**

### expertise.yaml (Knowledge Base)
- **Loaded on demand** via progressive disclosure
- Contains:
  - Complete component inventory with paths
  - WebSocket event types and handlers
  - Store structure and actions
  - Composables and services
  - File locations with line numbers
- Target: **~600 lines max**
- Format: Structured YAML for easy validation

### self-improve.md (Validation Prompt)
- User-invoked via custom command or manual execution
- Workflow:
  1. Check git diff (optional)
  2. Read expertise.yaml
  3. Validate against actual codebase
  4. Update discrepancies
  5. Enforce line limit
  6. Validate YAML syntax
- Produces structured report

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Context loading | Hybrid (inline + lazy) | Balance context cost vs completeness |
| Line limit | 600 for expertise.yaml | Smaller than experts (1000) since skill has inline too |
| Format | YAML | Parseable, consistent with experts pattern |
| Self-improve trigger | Manual | User invokes when codebase changes significantly |

## Quick Reference Content (Inline in SKILL.md)

Include these critical items inline for zero-latency access:

```markdown
## Quick Reference

### Key Files
| Purpose | Path |
|---------|------|
| Entry | src/main.ts |
| Root | src/App.vue |
| Router | src/router/index.ts |
| Store | src/stores/orchestratorStore.ts |
| Types | src/types.d.ts |
| WebSocket | src/services/chatService.ts |

### View Modes
| Mode | Component | Layout |
|------|-----------|--------|
| logs | EventStream | 3-column |
| adws | AdwSwimlanes | 3-column |
| open-positions | OpenPositions | 1-column |
| calendar | CalendarPage | 1-column |
| trade-stats | TradeStatsGrid | 1-column |

### WebSocket Events (Common)
- chat_stream, agent_log, thinking_block, tool_use_block
- adw_created, adw_updated, adw_step_change
- option_price_update, spot_price_update
```

## Expertise.yaml Structure

```yaml
frontend_expertise:
  meta:
    last_validated: "2026-01-21"
    codebase_path: "apps/orchestrator_3_stream/frontend"

  architecture:
    entry_point: "src/main.ts"
    root_component: "src/App.vue"
    build_tool: "Vite 5.x"
    framework: "Vue 3.4.x"

  components:
    views:
      - name: HomeView
        path: "src/views/HomeView.vue"
        meta: "requiresAuth: true"
      # ...

    core:
      - name: EventStream
        path: "src/components/EventStream.vue"
        purpose: "Event log stream with filtering"
        props: ["filter", "autoScroll"]
      # ...

  websocket:
    connection:
      url_env: "VITE_WEBSOCKET_URL"
      default: "ws://127.0.0.1:9403/ws"
      reconnect_max_attempts: 5

    events:
      chat:
        - type: chat_stream
          handler: "orchestratorStore.ts:handleChatStream"
        # ...
      agent:
        - type: agent_log
          handler: "orchestratorStore.ts:addAgentLogEvent"
        # ...

  store:
    file: "src/stores/orchestratorStore.ts"
    state:
      - name: agents
        type: "Agent[]"
      - name: chatMessages
        type: "ChatMessage[]"
      # ...
    actions:
      - name: sendUserMessage
        params: ["content: string"]
      # ...

  composables:
    - name: useEventStreamFilter
      path: "src/composables/useEventStreamFilter.ts"
      purpose: "Event filtering logic"
    # ...
```

## Self-Improve.md Template

```markdown
---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
description: Self-improve orchestrator-frontend expertise
argument-hint: "[check_git_diff (true/false)] [focus_area (optional)]"
---

# Self-Improve Orchestrator Frontend Expertise

## Variables
- EXPERTISE_FILE: .claude/skills/orchestrator-frontend/expertise.yaml
- MAX_LINES: 600
- CODEBASE_PATH: apps/orchestrator_3_stream/frontend

## Workflow

1. **Check Git Diff** (if CHECK_GIT_DIFF=true)
   - Run: `git diff --name-only HEAD~5 -- $CODEBASE_PATH`

2. **Read Current Expertise**
   - Read entire EXPERTISE_FILE

3. **Validate Against Codebase**
   - Read key files: main.ts, App.vue, orchestratorStore.ts, chatService.ts
   - Compare documented components vs actual src/components/
   - Verify WebSocket event types match chatService.ts switch cases
   - Check store state/actions match orchestratorStore.ts

4. **Identify Discrepancies**
   - List: missing components, outdated paths, wrong line numbers

5. **Update Expertise File**
   - Add missing, update outdated, remove obsolete

6. **Enforce Line Limit**
   - Run: `wc -l $EXPERTISE_FILE`
   - If > MAX_LINES: trim verbose descriptions, redundant examples

7. **Validate YAML**
   - Run: `python3 -c "import yaml; yaml.safe_load(open('$EXPERTISE_FILE'))"`
```

## Implementation Steps

1. [ ] Extract quick reference from current SKILL.md → keep inline
2. [ ] Extract detailed knowledge → create expertise.yaml
3. [ ] Refactor SKILL.md to reference expertise.yaml
4. [ ] Create self-improve.md with validation workflow
5. [ ] Test skill activation and context loading
6. [ ] Run initial self-improve to validate expertise accuracy

## References

- Current SKILL.md: `.claude/skills/orchestrator-frontend/SKILL.md`
- Expert pattern example: `.claude/commands/experts/websocket/`
- Skills documentation: `.claude/skills/meta-skill/docs/claude_code_agent_skills.md`
