---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, TodoWrite
description: Self-improve any skill's expertise by validating against codebase implementation
argument-hint: "[skill-name] [check_git_diff (true/false)] [focus_area (optional)]"
---

# Self-Improve Skill Expertise

Validate and update any skill's expertise.yaml file to ensure it accurately reflects the current state of the associated codebase.

## Usage

```bash
/self-improve-skill <skill-name> [check_git_diff] [focus_area]
```

**Arguments:**
- `skill-name` (required) - Name of skill directory under `.claude/skills/`
- `check_git_diff` (optional) - `true` to prioritize recently changed files, defaults to `false`
- `focus_area` (optional) - Specific area to validate (e.g., "websocket", "components", "store")

**Examples:**
```bash
/self-improve-skill orchestrator-frontend
/self-improve-skill orchestrator-frontend true
/self-improve-skill orchestrator-frontend true websocket
/self-improve-skill analyzing-options-greeks false routing
```

## Dynamic Workflow

This command automatically adapts to any skill by reading its configuration from the expertise.yaml file.

### Step 0: Initialize Variables from Skill Config

```bash
SKILL_NAME=$1                                           # e.g., "orchestrator-frontend"
CHECK_GIT_DIFF=${2:-false}                              # true/false, defaults to false
FOCUS_AREA=${3:-""}                                     # Optional focus area

SKILL_DIR=".claude/skills/${SKILL_NAME}"
EXPERTISE_FILE="${SKILL_DIR}/expertise.yaml"
SKILL_FILE="${SKILL_DIR}/SKILL.md"
```

Read the expertise.yaml file to extract configuration:

```bash
Read: ${EXPERTISE_FILE}
```

**Extract from expertise.yaml:**
- `meta.codebase_path` - Path to the codebase to validate against
- `meta.max_lines` - Line limit for expertise file (default: 600)
- `meta.last_validated` - Date of last validation

Set derived variables:

```bash
CODEBASE_PATH=$(extracted from meta.codebase_path)      # e.g., "apps/orchestrator_3_stream/frontend"
MAX_LINES=$(extracted from meta.max_lines or 600)       # Default 600 if not specified
LAST_VALIDATED=$(extracted from meta.last_validated)
```

### Step 1: Check Git Diff (Optional)

If `CHECK_GIT_DIFF` is `true`, identify recently changed files:

```bash
cd /Users/muzz/Desktop/tac/TOD
git diff --name-only HEAD~5 -- ${CODEBASE_PATH}
```

This helps prioritize validation efforts on recently modified areas.

**Note:** Skip this step if `CHECK_GIT_DIFF` is `false` or not provided.

### Step 2: Read Current Expertise

Read the entire expertise.yaml file to understand what's currently documented:

```bash
Read: ${EXPERTISE_FILE}
```

Analyze the structure:
- What sections exist? (components, services, websocket, store, etc.)
- What is the current organization pattern?
- What metadata is tracked?

If `FOCUS_AREA` is specified, note which section to prioritize.

### Step 3: Validate Against Codebase

Systematically verify expertise.yaml against actual codebase. The validation approach depends on the expertise.yaml structure.

#### 3.1 Validate Key Entry Points

Read critical files that define the architecture:

```bash
# Read files listed in expertise.yaml's key_files or architecture section
# Examples (adapt based on expertise.yaml structure):
Read: ${CODEBASE_PATH}/src/main.ts           # Entry point (if it exists)
Read: ${CODEBASE_PATH}/src/App.vue           # Root component (if applicable)
Read: ${CODEBASE_PATH}/README.md             # Project documentation
```

#### 3.2 Validate Component/Module Inventory

If expertise.yaml documents components, modules, or files:

```bash
# List all relevant files based on expertise structure
Glob: ${CODEBASE_PATH}/**/*.vue              # For Vue.js projects
Glob: ${CODEBASE_PATH}/**/*.ts               # TypeScript files
Glob: ${CODEBASE_PATH}/**/*.py               # Python files
# Adapt patterns based on the project type

# Compare against expertise.yaml inventory
# Identify: missing items, removed items, renamed items
```

#### 3.3 Validate Specific Sections

Based on the expertise.yaml structure, validate relevant sections:

**For Frontend Projects:**
- **WebSocket Events**: Search for event definitions in service files
  ```bash
  Grep:
    pattern: "case '[a-z_]+'"
    path: ${CODEBASE_PATH}/src/services/
    output_mode: content
  ```
- **Store Structure**: Check state management files
  ```bash
  Grep:
    pattern: "const [a-zA-Z]+ = ref"
    path: ${CODEBASE_PATH}/src/stores/
    output_mode: content
  ```
- **Routes**: Validate routing configuration
  ```bash
  Read: ${CODEBASE_PATH}/src/router/index.ts
  ```

**For Backend Projects:**
- **API Endpoints**: Search for route definitions
  ```bash
  Grep:
    pattern: "@(app|router)\\.(get|post|put|delete)"
    path: ${CODEBASE_PATH}
    output_mode: content
  ```
- **Database Models**: Check model definitions
  ```bash
  Glob: ${CODEBASE_PATH}/**/models.py
  ```

**For Any Project Type:**
- **Dependencies**: Validate package versions
  ```bash
  Read: ${CODEBASE_PATH}/package.json         # For Node.js
  Read: ${CODEBASE_PATH}/pyproject.toml       # For Python
  Read: ${CODEBASE_PATH}/Cargo.toml           # For Rust
  ```
- **Configuration**: Check environment variables
  ```bash
  Read: ${CODEBASE_PATH}/.env.example
  Grep:
    pattern: "(VITE_|REACT_|NEXT_PUBLIC_)[A-Z_]+"
    path: ${CODEBASE_PATH}
    output_mode: content
  ```

**Adapt validation based on expertise.yaml structure.** If the expertise file has a `websocket.events` section, validate WebSocket events. If it has a `components` section, validate components. Let the existing structure guide your validation.

### Step 4: Identify Discrepancies

Create a structured list of findings organized by category:

**Missing from expertise.yaml:**
- [ ] New file/component: [path]
- [ ] New event/endpoint: [type]
- [ ] New module/service: [name]
- [ ] New configuration: [name]

**Outdated in expertise.yaml:**
- [ ] Path changed: [old] → [new]
- [ ] Name renamed: [old] → [new]
- [ ] Version mismatch: [package] [documented] → [actual]
- [ ] Description outdated: [item]

**Removed from codebase:**
- [ ] File no longer exists: [name]
- [ ] Feature removed: [type]
- [ ] Module deleted: [name]

**Focus Area Findings (if specified):**
- [ ] Specific findings related to `FOCUS_AREA`

### Step 5: Update Expertise File

Apply corrections using Edit or Write tool.

**For Small, Targeted Changes:**

```bash
Edit:
  file_path: ${EXPERTISE_FILE}
  old_string: "[exact content to replace]"
  new_string: "[corrected content]"
```

**For Major Restructuring:**

```bash
Write: ${EXPERTISE_FILE}
```

**Update Principles:**
- Add missing items to appropriate sections
- Remove obsolete entries completely
- Update paths, versions, and descriptions for accuracy
- Preserve YAML structure and formatting conventions
- Maintain consistency with existing patterns
- Update `meta.last_validated` to current date (YYYY-MM-DD format)

**Preserve Existing Structure:**
- Keep the same section organization (don't restructure unless necessary)
- Maintain existing naming conventions
- Follow existing indentation style (spaces, not tabs, typically 2-space indent)
- Preserve comments if they exist

### Step 6: Enforce Line Limit

After updates, verify line count against the configured maximum:

```bash
wc -l ${EXPERTISE_FILE}
```

Compare result to `MAX_LINES` (from meta.max_lines or default 600).

**If exceeding MAX_LINES:**

Apply trimming in priority order:

1. **Keep (High Priority)**:
   - Architecture and key file paths
   - Critical integration points (APIs, events, routes)
   - Core data structures (store state, models, types)

2. **Keep (Medium Priority)**:
   - Component/module inventory (names + paths only)
   - Common patterns and conventions
   - Technology stack with versions

3. **Reduce (Low Priority)**:
   - Verbose descriptions → Make concise
   - Detailed prop/parameter lists → Keep only essential
   - Long examples → Shorten or remove

4. **Remove (Lowest Priority)**:
   - Redundant information
   - Low-value entries (rarely used utilities)
   - Duplicated content
   - Overly detailed implementation notes

**Trimming Strategies:**
- Combine similar entries into single items
- Convert prose descriptions to bullet points
- Remove obvious information (e.g., "Button component for buttons")
- Use YAML references to avoid duplication
- Keep only the most recent versions in version history

### Step 7: Validate YAML Syntax

Ensure the file is valid YAML and can be parsed:

```bash
python3 -c "import yaml; yaml.safe_load(open('${EXPERTISE_FILE}'))"
```

**If syntax errors occur:**
- Identify the line number from error message
- Common issues:
  - Incorrect indentation (use 2 spaces, not tabs)
  - Unescaped special characters in strings
  - Missing quotes around strings with colons
  - Inconsistent list formatting
- Fix errors and re-validate until clean

**Alternative validation (if Python not available):**

```bash
# Use Bash to run type check if available
cd ${CODEBASE_PATH}
npm run type-check                                     # For Node.js projects
uv run python -m yaml ${EXPERTISE_FILE}                # For Python projects with yaml module
```

### Step 8: Update SKILL.md if Needed

Check if the companion SKILL.md file needs updates:

```bash
Read: ${SKILL_FILE}
```

**Update SKILL.md if:**
- Key files changed (update quick reference table)
- Major features added/removed (update workflow descriptions)
- Technology stack versions updated (update technology table)
- Common patterns changed (update pattern examples)
- Configuration variables changed (update environment table)

**Keep SKILL.md and expertise.yaml synchronized:**
- SKILL.md provides human-readable overview and workflows
- expertise.yaml provides structured, detailed specifications
- Both should reference the same file paths and features
- Cross-reference between them should remain valid

### Step 9: Generate Validation Report

Produce a structured output summarizing the validation:

```markdown
# Expertise Validation Report: ${SKILL_NAME}

**Date:** [current date YYYY-MM-DD]
**Skill Path:** `.claude/skills/${SKILL_NAME}/`
**Codebase Path:** `${CODEBASE_PATH}`
**Focus Area:** [if specified, otherwise "Full validation"]
**Git Diff Check:** [enabled/disabled]

## Validation Summary

- **Files Examined:** [count]
- **Sections Validated:** [list of sections checked]
- **Discrepancies Found:** [count]
- **Updates Applied:** [count]

## Changes Made

### Added
- [New component X at path/to/file.vue]
- [New event type Y with handler]
- [New service Z for purpose]

### Updated
- [Component path: old/path.vue → new/path.vue]
- [Version: package@1.0.0 → package@2.0.0]
- [Description improved for accuracy]

### Removed
- [Obsolete component that no longer exists]
- [Deprecated event type]
- [Unused configuration variable]

## Current Status

- **Total Lines:** [count] / [MAX_LINES]
- **YAML Syntax:** [Valid ✓ / Invalid ✗]
- **Last Validated:** [date from meta.last_validated]
- **Codebase Path:** `${CODEBASE_PATH}`

## Focus Area Results (if specified)

[Detailed findings for the specified focus area]

## Recommendations

- [Suggest follow-up actions if needed]
- [Flag areas requiring manual review]
- [Note any assumptions made during validation]
- [Suggest improvements to skill organization]

## Validation Quality

- **Completeness:** [All sections checked / Partial validation]
- **Accuracy:** [High confidence / Needs review]
- **Codebase Coverage:** [X% of files documented]
```

## Success Criteria

A successful validation ensures:

- ✓ All files/components in codebase are accurately documented
- ✓ All paths are correct and point to existing files
- ✓ All versions match actual package manifests
- ✓ All event types/endpoints match implementation
- ✓ Structure and patterns match actual code
- ✓ YAML is valid and parseable
- ✓ Line count ≤ configured MAX_LINES
- ✓ `meta.last_validated` updated to current date
- ✓ No false positives (documented items actually exist)
- ✓ No false negatives (existing items are documented)

## Advanced Usage Patterns

### Pattern 1: Incremental Validation with Git

Focus on recently changed areas to speed up validation:

```bash
/self-improve-skill my-skill true
```

This runs `git diff --name-only HEAD~5` to identify changes, then prioritizes validation of those files.

### Pattern 2: Targeted Section Validation

Validate only a specific section to save time:

```bash
/self-improve-skill my-skill false websocket
```

Skips git diff check, validates only the WebSocket section.

### Pattern 3: Full Deep Validation

Perform comprehensive validation of all sections:

```bash
/self-improve-skill my-skill false
```

No git filtering, no focus area - validates everything.

### Pattern 4: Post-Feature Validation

After implementing a new feature, validate the affected area:

```bash
# Just added new components
/self-improve-skill my-skill true components

# Just refactored routing
/self-improve-skill my-skill true routing
```

## Troubleshooting

### Issue: Skill Not Found

**Error:** Cannot find `.claude/skills/${SKILL_NAME}/`

**Solution:**
- Verify skill name is correct (case-sensitive)
- Check skill directory exists: `ls -la .claude/skills/`
- Ensure you're in the project root directory

### Issue: Missing expertise.yaml

**Error:** Cannot read expertise.yaml file

**Solution:**
- Verify file exists: `ls -la ${SKILL_DIR}/expertise.yaml`
- Check file permissions are readable
- If file doesn't exist, create a minimal template:
  ```yaml
  meta:
    last_validated: "2026-01-21"
    codebase_path: "path/to/codebase"
    max_lines: 600
  ```

### Issue: Invalid YAML Syntax

**Error:** YAML parsing fails

**Solution:**
- Check indentation (use spaces, not tabs)
- Quote strings containing special characters
- Validate structure with online YAML validator
- Look for common mistakes:
  - Mixing tabs and spaces
  - Incorrect list item syntax
  - Unescaped colons in values

### Issue: Line Limit Exceeded

**Error:** File exceeds MAX_LINES after updates

**Solution:**
- Run trimming process (Step 6)
- Prioritize high-value information
- Remove verbose descriptions
- Consider increasing max_lines if genuinely needed
- Focus on paths and structure over detailed explanations

### Issue: Codebase Path Not Found

**Error:** Cannot access files at CODEBASE_PATH

**Solution:**
- Verify `meta.codebase_path` in expertise.yaml is correct
- Check path is relative to project root
- Ensure directory exists: `ls -la ${CODEBASE_PATH}`
- Update expertise.yaml if path changed

## Notes

- This command is idempotent - running it multiple times is safe
- Always creates a backup recommendation if major changes detected
- Preserves existing structure and formatting conventions
- Adapts validation strategy based on project type (frontend, backend, library)
- Can validate any type of codebase (Vue, React, Python, Rust, etc.)
- Uses TodoWrite for complex validations requiring multiple steps
- Reads entire files when needed (follows IMPORTANT: Actually read the file rule)
