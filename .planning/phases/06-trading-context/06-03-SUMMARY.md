---
phase: 06-trading-context
plan: 03
subsystem: ui
tags: [vue, typescript, pinia, credential-context, fetch-api]

# Dependency graph
requires:
  - phase: 06-01
    provides: Chat endpoint requires credential_id
  - phase: 06-02
    provides: Positions endpoint requires credential_id
  - phase: 04-02
    provides: accountStore with activeCredentialId
provides:
  - Frontend passes credential_id to chat endpoint
  - Frontend passes credential_id to positions endpoint
  - Chat disabled when no credential selected
  - 403 error handling clears stale credentials
  - Visual indicator for missing credential
affects: [07-trading-execution, 08-mobile-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [credential-context-injection, 403-stale-credential-clearing]

key-files:
  created:
    - apps/orchestrator_3_stream/frontend/src/services/positionsService.ts
  modified:
    - apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue
    - apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts
    - apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts

key-decisions:
  - "Pass credential_id in request body for chat (POST) and query params for positions (GET)"
  - "Disable send button AND show warning when no credential selected (defense in depth)"
  - "403 response clears credential from both store and localStorage to handle stale credentials"
  - "Positions composable watches activeCredentialId and reloads automatically on change"

patterns-established:
  - "Credential context injection: All trading API calls include credential_id"
  - "Stale credential handling: 403 errors trigger credential clearing"
  - "Credential-aware components: Guard actions when no credential selected"

# Metrics
duration: 3min
completed: 2026-02-01
---

# Phase 6 Plan 03: Frontend Credential Wiring Summary

**Frontend chat and positions now require credential context via accountStore.activeCredentialId with visual feedback and 403 stale credential handling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-01T12:37:50Z
- **Completed:** 2026-02-01T12:40:53Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Chat component passes credential_id from accountStore in request body
- Send button disabled with visual warning when no credential selected
- 403 errors clear stale credentials from store and localStorage
- positionsService created with credential_id in all requests
- useAlpacaPositions composable updated to use accountStore credential context
- Positions automatically reload when active credential changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Modify AlpacaAgentChat to pass credential_id** - `5dfdc20` (feat)
2. **Task 2: Create positionsService with credential_id support** - `dadf64e` (feat)
3. **Task 3: Update positions display to use credential context** - `574c524` (feat)

## Files Created/Modified
- `apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue` - Added accountStore import, credential_id in request, 403 handling, visual warning
- `apps/orchestrator_3_stream/frontend/src/services/positionsService.ts` - New service with credential_id in all position/order requests
- `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts` - Added optional credential_id param to getPositions/getPositionById
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts` - Uses accountStore, guards fetching, watches credential changes

## Decisions Made
- **Credential in body vs query:** Chat uses POST body, positions use query params (RESTful convention)
- **Defense in depth:** Both button disabled state AND error message guard against missing credential
- **Stale credential pattern:** 403 errors clear both store state and localStorage to prevent persistent bad state
- **Reactive positions:** Watch activeCredentialId and reload positions automatically for seamless account switching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - implementation proceeded smoothly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 complete: Full credential context chain from database to frontend
- Chat requests include credential_id, validated via RLS
- Positions requests include credential_id, fetch user-specific data
- Visual feedback guides users to select credential before trading
- Ready for Phase 7 (Trading Execution) to build on credential-aware API calls

---
*Phase: 06-trading-context*
*Completed: 2026-02-01*
