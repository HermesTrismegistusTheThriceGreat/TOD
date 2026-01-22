---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
description: Self-improve orchestrator-backend expertise
argument-hint: "[check_git_diff (true/false)] [focus_area (optional)]"
---

# Self-Improve Orchestrator Backend Expertise

Validate and update the expertise.yaml file to ensure it accurately reflects the current state of the Orchestrator Backend codebase.

## Variables

```bash
EXPERTISE_FILE=".claude/skills/orchestrator-backend/expertise.yaml"
MAX_LINES=600
CODEBASE_PATH="apps/orchestrator_3_stream/backend"
SKILL_FILE=".claude/skills/orchestrator-backend/SKILL.md"
```

## Workflow

### 1. Check Git Diff (Optional)

If CHECK_GIT_DIFF is true, identify recently changed files:

```bash
cd /Users/muzz/Desktop/tac/TOD
git diff --name-only HEAD~5 -- apps/orchestrator_3_stream/backend
```

This helps prioritize validation efforts on recently modified areas.

### 2. Read Current Expertise

Read the entire expertise.yaml file to understand what's documented:

```bash
Read: .claude/skills/orchestrator-backend/expertise.yaml
```

### 3. Validate Against Codebase

Systematically verify expertise.yaml against actual codebase:

#### 3.1 Validate Key Files
```bash
# Entry point
Read: apps/orchestrator_3_stream/backend/main.py

# Database module
Read: apps/orchestrator_3_stream/backend/modules/database.py

# Pydantic models
Read: apps/orchestrator_3_stream/backend/modules/orch_database_models.py

# WebSocket manager
Read: apps/orchestrator_3_stream/backend/modules/websocket_manager.py

# Orchestrator service
Read: apps/orchestrator_3_stream/backend/modules/orchestrator_service.py

# Agent manager
Read: apps/orchestrator_3_stream/backend/modules/agent_manager.py
```

#### 3.2 Validate API Endpoints
```bash
# Extract all route definitions from main.py
Grep:
  pattern: "@app\\.(get|post|put|delete|websocket)"
  path: apps/orchestrator_3_stream/backend/main.py
  output_mode: content

# Compare against expertise.yaml api_endpoints section
# Identify: missing endpoints, removed endpoints, changed paths
```

#### 3.3 Validate Database Operations
```bash
# Extract all async functions from database.py
Grep:
  pattern: "async def [a-z_]+"
  path: apps/orchestrator_3_stream/backend/modules/database.py
  output_mode: content

# Compare against expertise.yaml database.operations section
```

#### 3.4 Validate WebSocket Events
```bash
# Extract broadcast methods from websocket_manager.py
Grep:
  pattern: "async def broadcast_[a-z_]+"
  path: apps/orchestrator_3_stream/backend/modules/websocket_manager.py
  output_mode: content

# Compare against expertise.yaml websocket.events section
```

#### 3.5 Validate Services
```bash
# List all module files
Glob: apps/orchestrator_3_stream/backend/modules/*.py

# For each service file, extract class definitions
Grep:
  pattern: "class [A-Z][a-zA-Z]+:"
  path: apps/orchestrator_3_stream/backend/modules
  output_mode: content

# Compare against expertise.yaml services section
```

#### 3.6 Validate Pydantic Models
```bash
# Extract model definitions
Grep:
  pattern: "class [A-Z][a-zA-Z]+\\(BaseModel\\)"
  path: apps/orchestrator_3_stream/backend/modules
  output_mode: content

# Compare against expertise.yaml models section
```

#### 3.7 Validate Hooks
```bash
# Read hook files
Read: apps/orchestrator_3_stream/backend/modules/command_agent_hooks.py
Read: apps/orchestrator_3_stream/backend/modules/orchestrator_hooks.py

# Extract hook factory functions
Grep:
  pattern: "def create_[a-z_]+_hook"
  path: apps/orchestrator_3_stream/backend/modules
  output_mode: content

# Compare against expertise.yaml hooks section
```

#### 3.8 Validate Utilities
```bash
# List all utility modules
Glob: apps/orchestrator_3_stream/backend/modules/*.py

# Compare against expertise.yaml utilities section
# Identify: missing utilities, removed utilities
```

#### 3.9 Validate Environment Variables
```bash
# Read config.py
Read: apps/orchestrator_3_stream/backend/modules/config.py

# Extract environment variable references
Grep:
  pattern: "os\\.getenv|os\\.environ"
  path: apps/orchestrator_3_stream/backend/modules/config.py
  output_mode: content

# Compare against expertise.yaml environment section
```

#### 3.10 Validate Tests
```bash
# List test files
Glob: apps/orchestrator_3_stream/backend/tests/*.py

# Compare against expertise.yaml testing section
```

### 4. Identify Discrepancies

Create a structured list of findings:

**Missing from expertise.yaml:**
- [ ] New endpoint: [method] [path]
- [ ] New database operation: [function]
- [ ] New WebSocket event: [type]
- [ ] New service: [class]
- [ ] New model: [name]
- [ ] New utility: [module]

**Outdated in expertise.yaml:**
- [ ] Endpoint path changed: [old] → [new]
- [ ] Function renamed: [old] → [new]
- [ ] Service method added/removed: [class].[method]

**Removed from codebase:**
- [ ] Endpoint removed: [path]
- [ ] Function deleted: [name]
- [ ] Service removed: [class]

### 5. Update Expertise File

Apply corrections using Edit or Write:

```bash
# For small changes
Edit:
  file_path: .claude/skills/orchestrator-backend/expertise.yaml
  old_string: "[incorrect content]"
  new_string: "[corrected content]"

# For major restructuring
Write: .claude/skills/orchestrator-backend/expertise.yaml
```

**Update Principles:**
- Add missing entries to appropriate sections
- Remove obsolete entries
- Update method signatures, paths, and descriptions
- Preserve YAML structure and formatting
- Update `meta.last_validated` to current date

### 6. Enforce Line Limit

After updates, verify line count:

```bash
wc -l .claude/skills/orchestrator-backend/expertise.yaml
```

If exceeding MAX_LINES (600):
- Trim verbose descriptions
- Remove redundant examples
- Consolidate similar entries
- Keep focus on high-value information

**Prioritization for trimming:**
1. Keep: Architecture, key files, API endpoints, database operations
2. Keep: WebSocket events, service methods
3. Reduce: Verbose descriptions, detailed parameter lists
4. Remove: Low-value entries, duplicated information

### 7. Validate YAML Syntax

Ensure valid YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('.claude/skills/orchestrator-backend/expertise.yaml'))"
```

If syntax errors occur, fix and re-validate.

### 8. Update SKILL.md if Needed

If major structural changes occurred, check if SKILL.md quick reference needs updates:

```bash
Read: .claude/skills/orchestrator-backend/SKILL.md
```

Update quick reference tables if:
- Key files changed
- API endpoint groups changed
- Core services added/removed
- Technology stack versions updated

### 9. Generate Validation Report

Produce structured output:

```markdown
# Backend Expertise Validation Report

**Date:** [current date]
**Focus Area:** [if specified, otherwise "Full validation"]
**Files Checked:** [count]

## Summary
- API endpoints validated: [count]
- Database operations validated: [count]
- WebSocket events validated: [count]
- Services validated: [count]
- Models validated: [count]
- Utilities validated: [count]

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
# User: "Self-improve focusing on API endpoints"
# Only validates api_endpoints section
```

### Example 4: Service-Focused Validation

```bash
# User: "Self-improve focusing on Alpaca service"
# Only validates alpaca-related services and endpoints
```

## Success Criteria

- All API endpoints in main.py are documented
- All database operations match database.py
- All WebSocket broadcast methods are documented
- Service classes and methods are accurate
- Pydantic models are complete
- File paths are accurate
- YAML is valid and parseable
- Line count ≤ 600
- meta.last_validated is current date
