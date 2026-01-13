# Plan: Migrate Build Agents from Opus to Sonnet

## Task Description
Update the agentic layer so `/build` agents use Sonnet instead of Opus for cost optimization. This involves changing the model configuration in the build-agent definition and updating the default model parameter in the `run_build_step()` functions across ADW workflow files.

## Objective
Reduce API costs by using Sonnet (a faster, more cost-effective model) for build tasks while preserving Opus for strategic planning, review, and fix steps that require deeper reasoning.

## Problem Statement
Build tasks are primarily execution-focused - they implement code based on detailed specifications from the plan step. These tasks don't require the full reasoning capabilities of Opus and can be effectively handled by Sonnet, resulting in significant cost savings without sacrificing quality.

## Solution Approach
Change the default model for build-related functions from `ModelName.OPUS.value` to `ModelName.SONNET.value` in:
1. The Claude Code agent configuration (`.claude/agents/build-agent.md`)
2. All ADW workflow files that have a `run_build_step()` function

Keep Opus as the default for:
- Plan steps (strategic thinking)
- Review steps (thorough analysis)
- Fix steps (complex remediation)
- Extract path functions (context-dependent)

## Relevant Files
Use these files to complete the task:

- **`.claude/agents/build-agent.md`** (line 5) - Agent configuration with `model: opus` frontmatter that controls which model the build-agent uses when spawned
- **`adws/adw_workflows/adw_plan_build.py`** (line 608) - Contains `run_build_step()` with `model: str = ModelName.OPUS.value` default parameter
- **`adws/adw_workflows/adw_plan_build_review.py`** (line 610) - Contains `run_build_step()` with `model: str = ModelName.OPUS.value` default parameter
- **`adws/adw_workflows/adw_plan_build_review_fix.py`** (line 611) - Contains `run_build_step()` with `model: str = ModelName.OPUS.value` default parameter

### Files NOT to Change
- `run_plan_step()` functions - Keep Opus for strategic planning
- `run_review_step()` functions - Keep Opus for thorough validation
- `run_fix_step()` functions - Keep Opus for complex remediation
- `extract_plan_path()` functions - Keep Opus for context extraction
- `.claude/commands/build_in_parallel.md` - Already uses Sonnet

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Update build-agent.md Model Configuration
- Open `.claude/agents/build-agent.md`
- On line 5, change `model: opus` to `model: sonnet`
- Save the file

### 2. Update adw_plan_build.py Build Step Default
- Open `adws/adw_workflows/adw_plan_build.py`
- Locate `run_build_step()` function (around line 603-609)
- Change the default parameter from:
  ```python
  model: str = ModelName.OPUS.value,
  ```
  to:
  ```python
  model: str = ModelName.SONNET.value,
  ```
- Save the file

### 3. Update adw_plan_build_review.py Build Step Default
- Open `adws/adw_workflows/adw_plan_build_review.py`
- Locate `run_build_step()` function (around line 605-611)
- Change the default parameter from:
  ```python
  model: str = ModelName.OPUS.value,
  ```
  to:
  ```python
  model: str = ModelName.SONNET.value,
  ```
- Save the file

### 4. Update adw_plan_build_review_fix.py Build Step Default
- Open `adws/adw_workflows/adw_plan_build_review_fix.py`
- Locate `run_build_step()` function (around line 606-612)
- Change the default parameter from:
  ```python
  model: str = ModelName.OPUS.value,
  ```
  to:
  ```python
  model: str = ModelName.SONNET.value,
  ```
- Save the file

### 5. Validate Python Syntax
- Run syntax validation on all modified Python files to ensure no errors were introduced

## Acceptance Criteria
- [ ] `.claude/agents/build-agent.md` has `model: sonnet` on line 5
- [ ] `adw_plan_build.py` `run_build_step()` defaults to `ModelName.SONNET.value`
- [ ] `adw_plan_build_review.py` `run_build_step()` defaults to `ModelName.SONNET.value`
- [ ] `adw_plan_build_review_fix.py` `run_build_step()` defaults to `ModelName.SONNET.value`
- [ ] All `run_plan_step()` functions still default to `ModelName.OPUS.value`
- [ ] All `run_review_step()` functions still default to `ModelName.OPUS.value`
- [ ] All `run_fix_step()` functions still default to `ModelName.OPUS.value`
- [ ] All Python files pass syntax validation

## Validation Commands
Execute these commands to validate the task is complete:

```bash
# Validate Python syntax for all modified files
uv run python -m py_compile adws/adw_workflows/adw_plan_build.py
uv run python -m py_compile adws/adw_workflows/adw_plan_build_review.py
uv run python -m py_compile adws/adw_workflows/adw_plan_build_review_fix.py

# Verify build-agent uses sonnet
grep -n "model: sonnet" .claude/agents/build-agent.md

# Verify run_build_step uses SONNET default
grep -A2 "async def run_build_step" adws/adw_workflows/adw_plan_build.py | grep SONNET
grep -A2 "async def run_build_step" adws/adw_workflows/adw_plan_build_review.py | grep SONNET
grep -A2 "async def run_build_step" adws/adw_workflows/adw_plan_build_review_fix.py | grep SONNET

# Verify plan/review/fix steps still use OPUS
grep -A2 "async def run_plan_step" adws/adw_workflows/adw_plan_build.py | grep OPUS
grep -A2 "async def run_review_step" adws/adw_workflows/adw_plan_build_review.py | grep OPUS
grep -A2 "async def run_fix_step" adws/adw_workflows/adw_plan_build_review_fix.py | grep OPUS
```

## Notes
- This change affects the **default** model selection. Workflows can still override the model via `input_data.model` if needed.
- The `ModelName` enum is imported from `adw_modules.adw_agent_sdk` in all workflow files.
- No new dependencies are required for this change.
- Cost savings rationale: Sonnet is approximately 5-10x cheaper than Opus while maintaining high code generation quality for well-specified tasks.

## Summary Table

| File | Function | Current Default | New Default |
|------|----------|-----------------|-------------|
| `.claude/agents/build-agent.md` | frontmatter | `opus` | `sonnet` |
| `adw_plan_build.py` | `run_build_step()` | `OPUS` | `SONNET` |
| `adw_plan_build_review.py` | `run_build_step()` | `OPUS` | `SONNET` |
| `adw_plan_build_review_fix.py` | `run_build_step()` | `OPUS` | `SONNET` |

### Unchanged (Intentionally Kept on Opus)

| File | Function | Reason |
|------|----------|--------|
| All workflow files | `run_plan_step()` | Strategic planning requires deep reasoning |
| `adw_plan_build_review.py` | `run_review_step()` | Thorough code review requires deep analysis |
| `adw_plan_build_review_fix.py` | `run_review_step()` | Thorough code review requires deep analysis |
| `adw_plan_build_review_fix.py` | `run_fix_step()` | Complex remediation requires deep reasoning |
| All workflow files | `extract_plan_path()` | Context extraction benefits from stronger model |
