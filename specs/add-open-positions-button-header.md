# Plan: Add Open Positions Button to Header

## Task Description
Add an "Open Positions" button to the header of the orchestrator_3_stream Vue frontend application. This button will navigate to a new placeholder page component when clicked. The implementation will follow the existing component composition pattern used in the app (not Vue Router).

## Objective
When this plan is complete:
1. A new "POSITIONS" button will appear in the header alongside the existing "LOGS/ADWS" toggle and "PROMPT" button
2. Clicking the button will display a new OpenPositions page component
3. The new page will show placeholder text: "Open Positions Page Coming Soon!"
4. The button styling will match the existing header button styles

## Problem Statement
The application needs a new navigation option to access an "Open Positions" page. Currently, the header supports switching between "logs" and "adws" views via the `viewMode` state. This task extends that pattern to include a third view mode for "Open Positions" content.

## Solution Approach
Extend the existing `viewMode` state management pattern:
1. Add 'open-positions' to the `ViewMode` type union
2. Create a new `OpenPositions.vue` component
3. Add a new button to `AppHeader.vue` that sets the view mode to 'open-positions'
4. Update `App.vue` to conditionally render the `OpenPositions` component when the view mode is 'open-positions'

This approach maintains consistency with the existing architecture and requires minimal changes to the codebase.

## Relevant Files
Use these files to complete the task:

- **`/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/types.d.ts`** (line ~452) - Contains the `ViewMode` type definition that needs to be extended
- **`/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/AppHeader.vue`** - Header component where the new button will be added
- **`/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/App.vue`** - Main app component that handles view switching
- **`/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`** - Pinia store with `viewMode` state and `setViewMode()` action (no changes needed - already supports any ViewMode)

### New Files
- **`/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`** - New placeholder page component

## Implementation Phases

### Phase 1: Foundation
Extend the type system to support the new view mode.

### Phase 2: Core Implementation
Create the new component and add the header button.

### Phase 3: Integration & Polish
Update App.vue to render the new component and verify styling consistency.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Extend ViewMode Type
- Open `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/types.d.ts`
- Find line ~452 with `export type ViewMode = 'logs' | 'adws'`
- Update to: `export type ViewMode = 'logs' | 'adws' | 'open-positions'`

### 2. Create OpenPositions Component
- Create new file: `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`
- Use Vue 3 `<script setup lang="ts">` syntax
- Include a centered placeholder message: "Open Positions Page Coming Soon!"
- Style with CSS variables from the design system (`var(--bg-secondary)`, `var(--text-primary)`, etc.)
- Match the styling pattern of other center column components (full height, proper background)

**Component Template:**
```vue
<template>
  <div class="open-positions">
    <div class="open-positions-content">
      <h2>Open Positions Page Coming Soon!</h2>
    </div>
  </div>
</template>

<script setup lang="ts">
// Placeholder component - no logic needed yet
</script>

<style scoped>
.open-positions {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.open-positions-content {
  text-align: center;
  color: var(--text-primary);
}

.open-positions-content h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-muted);
}
</style>
```

### 3. Add Button to AppHeader
- Open `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/AppHeader.vue`
- Add a new button after the "PROMPT" button (around line 73)
- Use the existing `btn-prompt` styling class for consistency
- Add click handler: `@click="store.setViewMode('open-positions')"`
- Add active state: `:class="{ active: store.viewMode === 'open-positions' }"`

**Button to add (after the PROMPT button):**
```vue
<button
  class="btn-prompt"
  :class="{ active: store.viewMode === 'open-positions' }"
  @click="store.setViewMode('open-positions')"
  title="View open positions"
>
  POSITIONS
</button>
```

### 4. Update App.vue to Render OpenPositions
- Open `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/App.vue`
- Import the new component at the top of `<script setup>`
- Update the center column conditional rendering (around lines 21-33)
- Add `v-else-if` condition for `open-positions` view mode

**Import to add:**
```typescript
import OpenPositions from './components/OpenPositions.vue'
```

**Updated template section (center column):**
```vue
<!-- Center Column: EventStream, AdwSwimlanes, or OpenPositions based on view mode -->
<EventStream
  v-if="store.viewMode === 'logs'"
  ref="eventStreamRef"
  class="app-content center"
  :events="store.filteredEventStream"
  :current-filter="store.eventStreamFilter"
  :auto-scroll="true"
  @set-filter="handleSetFilter"
/>
<AdwSwimlanes
  v-else-if="store.viewMode === 'adws'"
  class="app-content center"
/>
<OpenPositions
  v-else-if="store.viewMode === 'open-positions'"
  class="app-content center"
/>
```

### 5. Validate the Implementation
- Run the development server to verify:
  - The "POSITIONS" button appears in the header
  - Clicking the button shows the OpenPositions placeholder page
  - The button highlights when active (matching PROMPT button behavior)
  - Clicking "LOGS" or "ADWS" buttons returns to their respective views
  - No TypeScript errors in the console

## Testing Strategy
Since this is a UI feature with minimal logic:
1. **Manual Testing**: Verify button click navigation and visual styling
2. **TypeScript Validation**: Ensure no type errors with the extended ViewMode
3. **Visual Verification**: Confirm button styling matches existing header buttons

## Acceptance Criteria
- [ ] A "POSITIONS" button is visible in the header next to the "PROMPT" button
- [ ] Clicking "POSITIONS" displays the OpenPositions component in the center column
- [ ] The placeholder text "Open Positions Page Coming Soon!" is centered and visible
- [ ] The button shows an active state when the open-positions view is displayed
- [ ] Navigation between all three views (logs, adws, open-positions) works correctly
- [ ] No TypeScript compilation errors
- [ ] Button styling is consistent with existing header buttons

## Validation Commands
Execute these commands to validate the task is complete:

- `cd /Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend && npm run type-check` - Verify TypeScript types are valid
- `cd /Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend && npm run dev` - Start dev server and manually test navigation

## Notes
- The store's `setViewMode()` function already accepts any `ViewMode` type, so no store changes are needed
- The `toggleViewMode()` function in the store only toggles between 'logs' and 'adws' - this is intentional behavior and should not be modified (Cmd+J keyboard shortcut behavior is separate from button navigation)
- Future enhancements to OpenPositions can build on this foundation without architectural changes
