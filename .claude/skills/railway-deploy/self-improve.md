---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
description: Self-improve railway-deploy expertise
argument-hint: "[check_git_diff (true/false)] [focus_area (optional)]"
---

# Self-Improve Railway Deploy Expertise

Validate and update the expertise.yaml file to ensure it accurately reflects the current state of the Railway deployment configuration, Dockerfiles, and environment settings.

## Variables

```bash
EXPERTISE_FILE=".claude/skills/railway-deploy/expertise.yaml"
MAX_LINES=600
CODEBASE_PATH="apps/orchestrator_3_stream"
SKILL_FILE=".claude/skills/railway-deploy/SKILL.md"
```

## Workflow

### 1. Check Git Diff (Optional)

If CHECK_GIT_DIFF is true, identify recently changed deployment-related files:

```bash
cd /Users/muzz/Desktop/tac/TOD
git diff --name-only HEAD~5 -- apps/orchestrator_3_stream/*/Dockerfile apps/orchestrator_3_stream/*/.env* .mcp.json.railway
```

This helps prioritize validation efforts on recently modified deployment configurations.

### 2. Read Current Expertise

Read the entire expertise.yaml file to understand what's documented:

```bash
Read: .claude/skills/railway-deploy/expertise.yaml
```

### 3. Validate Against Codebase

Systematically verify expertise.yaml against actual codebase:

#### 3.1 Validate Dockerfiles
```bash
# Backend Dockerfile
Read: apps/orchestrator_3_stream/backend/Dockerfile

# Frontend Dockerfile
Read: apps/orchestrator_3_stream/frontend/Dockerfile

# Auth Service Dockerfile
Read: apps/orchestrator_3_stream/auth-service/Dockerfile

# Compare against expertise.yaml architecture.services section
# Identify: dockerfile stages, build args, startup commands, port configurations
```

#### 3.2 Validate Service Configurations
```bash
# Extract port configurations from backend
Grep:
  pattern: "PORT|port"
  path: apps/orchestrator_3_stream/backend/main.py
  output_mode: content

# Extract port configurations from auth service
Grep:
  pattern: "PORT|port"
  path: apps/orchestrator_3_stream/auth-service/src/index.ts
  output_mode: content

# Compare against expertise.yaml dev_port and prod_port values
```

#### 3.3 Validate Environment Variables
```bash
# Backend environment variables
Read: apps/orchestrator_3_stream/backend/.env
Read: apps/orchestrator_3_stream/backend/modules/config.py

# Frontend environment variables
Grep:
  pattern: "VITE_[A-Z_]+"
  path: apps/orchestrator_3_stream/frontend
  output_mode: content

# Auth service environment variables
Grep:
  pattern: "process\\.env\\.[A-Z_]+"
  path: apps/orchestrator_3_stream/auth-service/src
  output_mode: content

# Compare against expertise.yaml environment_configuration section
```

#### 3.4 Validate Alpaca Configuration
```bash
# Check Alpaca data feed configuration
Grep:
  pattern: "ALPACA_DATA_FEED|OptionsFeed|StockDataStream"
  path: apps/orchestrator_3_stream/backend/modules
  output_mode: content

# Verify Elite subscription constraints in alpaca_service.py
Read: apps/orchestrator_3_stream/backend/modules/alpaca_service.py

# Compare against expertise.yaml critical_alpaca_elite_subscription section
```

#### 3.5 Validate Railway MCP Configuration
```bash
# Check MCP config file
Read: .mcp.json.railway

# Verify railway-mcp agent exists
Read: .claude/agents/railway-mcp.md

# Compare against expertise.yaml railway_mcp_tools section
```

#### 3.6 Validate Docker Build Args
```bash
# Extract frontend build args from Dockerfile
Grep:
  pattern: "ARG VITE_"
  path: apps/orchestrator_3_stream/frontend/Dockerfile
  output_mode: content

# Compare against expertise.yaml frontend.build_args section
```

#### 3.7 Validate Nginx Configuration
```bash
# Check nginx template for frontend
Glob: apps/orchestrator_3_stream/frontend/nginx/**/*

# Read nginx config if exists
Read: apps/orchestrator_3_stream/frontend/nginx/default.conf.template

# Verify PORT substitution pattern matches expertise.yaml
```

#### 3.8 Validate Railway Documentation References
```bash
# List all railway docs
Glob: railway_docs/*.md

# Compare against expertise.yaml documentation_reference section
# Identify: missing docs, removed docs, path changes
```

#### 3.9 Validate Service Dependencies
```bash
# Check database connection patterns
Grep:
  pattern: "DATABASE_URL|asyncpg|NeonDB"
  path: apps/orchestrator_3_stream/backend/modules
  output_mode: content

# Check auth service dependencies
Grep:
  pattern: "better-auth|FRONTEND_URL|AUTH_BASE_URL"
  path: apps/orchestrator_3_stream/auth-service/src
  output_mode: content

# Compare against expertise.yaml service_dependencies section
```

### 4. Identify Discrepancies

Create a structured list of findings:

**Missing from expertise.yaml:**
- [ ] New environment variable: [name]
- [ ] New Dockerfile stage: [service]
- [ ] New build arg: [name]
- [ ] New Railway doc: [filename]
- [ ] New service configuration: [aspect]

**Outdated in expertise.yaml:**
- [ ] Port changed: [service] [old] → [new]
- [ ] Dockerfile command changed: [stage]
- [ ] Environment variable default changed: [var]
- [ ] Documentation path changed: [old] → [new]

**Removed from codebase:**
- [ ] Environment variable removed: [name]
- [ ] Dockerfile stage removed: [stage]
- [ ] Railway doc removed: [filename]

### 5. Update Expertise File

Apply corrections using Edit or Write:

```bash
# For small changes
Edit:
  file_path: .claude/skills/railway-deploy/expertise.yaml
  old_string: "[incorrect content]"
  new_string: "[corrected content]"

# For major restructuring
Write: .claude/skills/railway-deploy/expertise.yaml
```

**Update Principles:**
- Add missing environment variables to appropriate sections
- Remove obsolete configurations
- Update port numbers, paths, and commands
- Preserve YAML structure and formatting
- Update `meta.last_validated` to current date
- Ensure Alpaca Elite constraints are still accurate

### 6. Enforce Line Limit

After updates, verify line count:

```bash
wc -l .claude/skills/railway-deploy/expertise.yaml
```

If exceeding MAX_LINES (600):
- Trim verbose descriptions
- Remove redundant examples
- Consolidate similar entries
- Keep focus on high-value information

**Prioritization for trimming:**
1. Keep: Service configurations, Dockerfiles, Alpaca Elite constraints
2. Keep: Environment variables (dev vs prod), deployment workflow
3. Reduce: Verbose troubleshooting steps, detailed command examples
4. Remove: Low-value entries, duplicated information

### 7. Validate YAML Syntax

Ensure valid YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('.claude/skills/railway-deploy/expertise.yaml'))"
```

If syntax errors occur, fix and re-validate.

### 8. Update SKILL.md if Needed

If major structural changes occurred, check if SKILL.md quick reference needs updates:

```bash
Read: .claude/skills/railway-deploy/SKILL.md
```

Update quick reference tables if:
- Service paths changed
- Port configurations updated
- Docker image locations changed
- Railway MCP tools added/removed
- Alpaca Elite constraints updated

### 9. Generate Validation Report

Produce structured output:

```markdown
# Railway Deploy Expertise Validation Report

**Date:** [current date]
**Focus Area:** [if specified, otherwise "Full validation"]
**Files Checked:** [count]

## Summary
- Services validated: [count] (backend, frontend, auth)
- Dockerfiles validated: [count]
- Environment variables validated: [count]
- Alpaca constraints validated: [yes/no]
- Railway MCP tools validated: [count]
- Documentation refs validated: [count]

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
# User: "Self-improve focusing on Dockerfiles"
# Only validates architecture.services.dockerfile_stages sections
```

### Example 4: Environment Variable Validation

```bash
# User: "Self-improve focusing on environment variables"
# Only validates environment_configuration section
```

### Example 5: Alpaca Constraints Validation

```bash
# User: "Self-improve focusing on Alpaca Elite constraints"
# Only validates critical_alpaca_elite_subscription section
```

## Success Criteria

- All three service Dockerfiles are accurately documented
- All environment variables match actual .env and config files
- Alpaca Elite subscription constraints are current and accurate
- Port configurations (dev and prod) match actual implementations
- Railway MCP tools list matches .mcp.json.railway and agent capabilities
- Documentation references point to existing files
- Build args match Dockerfile ARG declarations
- Nginx configuration matches actual template
- Service dependencies accurately reflect cross-service communication
- File paths are accurate
- YAML is valid and parseable
- Line count ≤ 600
- meta.last_validated is current date
