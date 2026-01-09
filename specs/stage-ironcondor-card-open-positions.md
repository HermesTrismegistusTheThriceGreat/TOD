# Plan: Stage IronCondorCard Components on Open Positions Page

## Task Description
Render 2-3 IronCondorCard components on the existing Open Positions page using hardcoded placeholder data. The IronCondorCard.vue component uses Element Plus and Vue 3 composition API. This is frontend-only work with no backend integration.

## Objective
Display multiple option position cards (iron condor, iron butterfly, etc.) on the Open Positions page with mock data, creating a visual staging area for future trading position management.

## Problem Statement
The Open Positions page currently shows only a "Coming Soon" placeholder. We need to:
1. Install Element Plus (not currently in the project)
2. Move/integrate the IronCondorCard component into the frontend
3. Create mock position data for different strategy types
4. Render multiple cards in a responsive grid layout

## Solution Approach
1. Install Element Plus and configure it in main.ts
2. Move IronCondorCard.vue from project root to the components directory
3. Update OpenPositions.vue to import and render multiple cards with mock data
4. Use CSS Grid for responsive card layout

## Relevant Files
Use these files to complete the task:

- **`IronCondorCard.vue`** (project root) - Source component to move (uses Element Plus el-card, el-table, el-tag, el-icon, Timer icon)
- **`apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`** - Target page to update (currently placeholder)
- **`apps/orchestrator_3_stream/frontend/src/main.ts`** - Need to register Element Plus globally
- **`apps/orchestrator_3_stream/frontend/package.json`** - Need to add Element Plus dependency
- **`apps/orchestrator_3_stream/frontend/src/types.d.ts`** - Reference for TypeScript patterns
- **`apps/orchestrator_3_stream/frontend/src/App.vue`** - Reference only (already imports OpenPositions correctly)

### New Files
- **`apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`** - Moved component

## Implementation Phases

### Phase 1: Foundation
Install Element Plus and configure the application to use it.

### Phase 2: Core Implementation
Move IronCondorCard component and update OpenPositions page with mock data and grid layout.

### Phase 3: Integration & Polish
Verify rendering, test responsiveness, and ensure visual consistency with existing app theme.

## Step by Step Tasks

### 1. Install Element Plus
- Run `npm install element-plus @element-plus/icons-vue` in the frontend directory

### 2. Configure Element Plus in main.ts
- Import Element Plus and its CSS
- Register it globally with the Vue app:
```typescript
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
app.use(ElementPlus)
```

### 3. Move IronCondorCard.vue to Components Directory
- Copy `IronCondorCard.vue` from project root to `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`

### 4. Create Mock Position Data in OpenPositions.vue
- Define an array of 3 different position objects:
  1. **Iron Condor** on SPY
  2. **Iron Butterfly** on QQQ
  3. **Iron Condor** on IWM

### 5. Update OpenPositions.vue Template
- Import IronCondorCard component
- Replace placeholder with grid of cards
- Use v-for to render each position

### 6. Style the Grid Layout
```css
.positions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(700px, 1fr));
  gap: 24px;
  padding: 24px;
}
```

### 7. Validate the Implementation
- Run `npm run dev` and verify cards render correctly

## Acceptance Criteria
- [] Element Plus is installed and configured
- [ ] IronCondorCard.vue is in the components directory
- [ ] OpenPositions.vue renders 3 position cards
- [ ] Cards display in a responsive grid layout
- [ ] No console errors

## Validation Commands
- `cd apps/orchestrator_3_stream/frontend && npm install`
- `cd apps/orchestrator_3_stream/frontend && npm run build`
- `cd apps/orchestrator_3_stream/frontend && npm run dev`

## Notes
- Element Plus dark mode: IronCondorCard has its own scoped dark theme CSS variables
- Future enhancement: Add a `position` prop to IronCondorCard for flexibility
