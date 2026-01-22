---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
description: Self-improve orchestrator-frontend expertise
argument-hint: "[check_git_diff (true/false)] [focus_area (optional)]"
---

# Self-Improve Orchestrator Frontend Expertise

Validate and update the expertise.yaml file to ensure it accurately reflects the current state of the Orchestrator Frontend codebase.

## Variables

```bash
EXPERTISE_FILE=".claude/skills/orchestrator-frontend/expertise.yaml"
MAX_LINES=600
CODEBASE_PATH="apps/orchestrator_3_stream/frontend"
SKILL_FILE=".claude/skills/orchestrator-frontend/SKILL.md"
```

## Workflow

### 1. Check Git Diff (Optional)

If CHECK_GIT_DIFF is true, identify recently changed files:

```bash
cd /Users/muzz/Desktop/tac/TOD
git diff --name-only HEAD~5 -- apps/orchestrator_3_stream/frontend
```

This helps prioritize validation efforts on recently modified areas.

### 2. Read Current Expertise

Read the entire expertise.yaml file to understand what's documented:

```bash
Read: .claude/skills/orchestrator-frontend/expertise.yaml
```

### 3. Validate Against Codebase

Systematically verify expertise.yaml against actual codebase:

#### 3.1 Validate Key Files
```bash
# Entry point
Read: apps/orchestrator_3_stream/frontend/src/main.ts

# Root component
Read: apps/orchestrator_3_stream/frontend/src/App.vue

# Store structure
Read: apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts

# WebSocket service
Read: apps/orchestrator_3_stream/frontend/src/services/chatService.ts

# Router
Read: apps/orchestrator_3_stream/frontend/src/router/index.ts

# Types
Read: apps/orchestrator_3_stream/frontend/src/types.d.ts
```

#### 3.2 Validate Component Inventory
```bash
# List all components
Glob: apps/orchestrator_3_stream/frontend/src/components/**/*.vue
Glob: apps/orchestrator_3_stream/frontend/src/views/**/*.vue

# Compare against expertise.yaml components section
# Identify: missing components, removed components, renamed components
```

#### 3.3 Validate WebSocket Events
```bash
# Extract all WebSocket event types from chatService.ts
Grep:
  pattern: "case '[a-z_]+'"
  path: apps/orchestrator_3_stream/frontend/src/services/chatService.ts
  output_mode: content

# Compare against expertise.yaml websocket.events section
# Identify: missing event types, removed event types, incorrect handlers
```

#### 3.4 Validate Store Structure
```bash
# Check orchestratorStore.ts for state properties
Grep:
  pattern: "const [a-zA-Z]+ = ref"
  path: apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts
  output_mode: content

# Check for actions/functions
Grep:
  pattern: "(async )?function [a-zA-Z]+"
  path: apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts
  output_mode: content

# Compare against expertise.yaml store section
```

#### 3.5 Validate Composables
```bash
# List all composables
Glob: apps/orchestrator_3_stream/frontend/src/composables/**/*.ts

# Compare against expertise.yaml composables section
```

#### 3.6 Validate Services
```bash
# List all services
Glob: apps/orchestrator_3_stream/frontend/src/services/**/*.ts

# Compare against expertise.yaml services section
```

#### 3.7 Validate Routes
```bash
# Read router configuration
Read: apps/orchestrator_3_stream/frontend/src/router/index.ts

# Verify route definitions match expertise.yaml routing section
```

#### 3.8 Validate Environment Variables
```bash
# Read .env file if exists
Read: apps/orchestrator_3_stream/frontend/.env

# Or check vite.config.ts for defaults
Grep:
  pattern: "VITE_[A-Z_]+"
  path: apps/orchestrator_3_stream/frontend
  output_mode: content
```

#### 3.9 Validate Package Versions
```bash
# Read package.json
Read: apps/orchestrator_3_stream/frontend/package.json

# Verify technology_stack versions in expertise.yaml
```

### 4. Identify Discrepancies

Create a structured list of findings:

**Missing from expertise.yaml:**
- [ ] New component: [path]
- [ ] New WebSocket event: [type]
- [ ] New store state: [name]
- [ ] New composable: [name]
- [ ] New service: [name]

**Outdated in expertise.yaml:**
- [ ] Component path changed: [old] → [new]
- [ ] Event handler renamed: [old] → [new]
- [ ] Version mismatch: [package] [documented] → [actual]

**Removed from codebase:**
- [ ] Component no longer exists: [name]
- [ ] Event type removed: [type]
- [ ] Service deleted: [name]

### 5. Update Expertise File

Apply corrections using Edit or Write:

```bash
# For small changes
Edit:
  file_path: .claude/skills/orchestrator-frontend/expertise.yaml
  old_string: "[incorrect content]"
  new_string: "[corrected content]"

# For major restructuring
Write: .claude/skills/orchestrator-frontend/expertise.yaml
```

**Update Principles:**
- Add missing components to appropriate sections
- Remove obsolete entries
- Update paths, versions, and descriptions
- Preserve YAML structure and formatting
- Update `meta.last_validated` to current date

### 6. Enforce Line Limit

After updates, verify line count:

```bash
wc -l .claude/skills/orchestrator-frontend/expertise.yaml
```

If exceeding MAX_LINES (600):
- Trim verbose descriptions
- Remove redundant examples
- Consolidate similar entries
- Keep focus on high-value information

**Prioritization for trimming:**
1. Keep: Architecture, key files, WebSocket events, store structure
2. Keep: Component inventory (names + paths only)
3. Reduce: Verbose descriptions, detailed prop lists
4. Remove: Low-value entries, duplicated information

### 7. Validate YAML Syntax

Ensure valid YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('.claude/skills/orchestrator-frontend/expertise.yaml'))"
```

If syntax errors occur, fix and re-validate.

### 8. Update SKILL.md if Needed

If major structural changes occurred, check if SKILL.md quick reference needs updates:

```bash
Read: .claude/skills/orchestrator-frontend/SKILL.md
```

Update quick reference tables if:
- Key files changed
- View modes added/removed
- Common WebSocket events changed
- Technology stack versions updated

### 9. Generate Validation Report

Produce structured output:

```markdown
# Expertise Validation Report

**Date:** [current date]
**Focus Area:** [if specified, otherwise "Full validation"]
**Files Checked:** [count]

## Summary
- Components validated: [count]
- WebSocket events validated: [count]
- Store properties validated: [count]
- Composables validated: [count]
- Services validated: [count]

## Changes Made
### Added
- [list new entries]

### Updated
- [list corrected entries]

### Removed
- [list obsolete entries]

## Current Status
- Total lines: [count] / 600
- YAML syntax: Valid ✓
- Last validated: [date]

## Recommendations
- [any follow-up actions needed]
```

## Usage Examples

### Example 1: Full Validation

```bash
# User invokes self-improve without arguments
# Performs complete validation of all sections
```

### Example 2: Git-Aware Validation

```bash
# User: "Self-improve with git diff check"
# Focuses on files changed in last 5 commits
```

### Example 3: Focused Validation

```bash
# User: "Self-improve focusing on WebSocket events"
# Only validates websocket.events section
```

## Success Criteria

- All components in codebase are documented
- All WebSocket event types match chatService.ts
- Store state/actions match orchestratorStore.ts
- File paths are accurate
- YAML is valid and parseable
- Line count ≤ 600
- meta.last_validated is current date
