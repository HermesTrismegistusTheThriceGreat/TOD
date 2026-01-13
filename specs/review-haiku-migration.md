# Plan: Review Agent Model Migration to Haiku

## Task Description
Migrate all /review agents from using Opus model to Haiku model across the agentic layer. This includes the Claude Code command configuration and ADW workflow defaults. The change reduces cost for review operations while maintaining sufficient capability for code review tasks.

## Objective
Update all review-related model configurations from `opus` to `haiku` while preserving the model assignments for plan, build, and fix steps.

## Relevant Files
Use these files to complete the task:

- **`.claude/commands/review.md`** - Claude Code command configuration with frontmatter `model: opus` on line 5. This controls the model used when `/review` is invoked directly.

- **`adws/adw_workflows/adw_plan_build_review.py`** - Three-step ADW workflow file containing:
  - `run_review_step()` function with default `model: str = ModelName.OPUS.value` (line 760)
  - `review_model` fallback default `ModelName.OPUS.value` (line 982)

- **`adws/adw_workflows/adw_plan_build_review_fix.py`** - Four-step ADW workflow file containing:
  - `run_review_step()` function with default `model: str = ModelName.OPUS.value` (line 761)
  - `review_model` fallback default `ModelName.OPUS.value` (line 1184)

### Files NOT Changed
- `.claude/agents/` - No `review-agent.md` exists; only contains: docs-scraper.md, meta-agent.md, planner.md, playwright-validator.md, scout-report-suggest-fast.md, scout-report-suggest.md, build-agent.md
- Plan step configurations (keep Opus)
- Build step configurations (keep Sonnet)
- Fix step configurations (keep Opus)

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Update Claude Code Review Command
- Open `.claude/commands/review.md`
- Change line 5 from `model: opus` to `model: haiku`
- Verify the frontmatter block is valid YAML

### 2. Update adw_plan_build_review.py Review Defaults
- Open `adws/adw_workflows/adw_plan_build_review.py`
- Locate `run_review_step()` function (around line 754)
- Change parameter default from `model: str = ModelName.OPUS.value` to `model: str = ModelName.HAIKU.value` (line 760)
- Locate `review_model` fallback assignment (around line 982)
- Change from `ModelName.OPUS.value` to `ModelName.HAIKU.value`
- **DO NOT** modify `run_plan_step()` or `run_build_step()` defaults

### 3. Update adw_plan_build_review_fix.py Review Defaults
- Open `adws/adw_workflows/adw_plan_build_review_fix.py`
- Locate `run_review_step()` function (around line 755)
- Change parameter default from `model: str = ModelName.OPUS.value` to `model: str = ModelName.HAIKU.value` (line 761)
- Locate `review_model` fallback assignment (around line 1184)
- Change from `ModelName.OPUS.value` to `ModelName.HAIKU.value`
- **DO NOT** modify `run_plan_step()`, `run_build_step()`, or `run_fix_step()` defaults

### 4. Validate Changes
- Run Python syntax check on modified workflow files
- Verify no other model defaults were accidentally changed
- Confirm plan steps still use Opus, build steps still use Sonnet, fix steps still use Opus

## Acceptance Criteria
- [ ] `.claude/commands/review.md` has `model: haiku` in frontmatter
- [ ] `adw_plan_build_review.py` `run_review_step()` defaults to `ModelName.HAIKU.value`
- [ ] `adw_plan_build_review.py` `review_model` fallback uses `ModelName.HAIKU.value`
- [ ] `adw_plan_build_review_fix.py` `run_review_step()` defaults to `ModelName.HAIKU.value`
- [ ] `adw_plan_build_review_fix.py` `review_model` fallback uses `ModelName.HAIKU.value`
- [ ] All other step model defaults remain unchanged (plan=Opus, build=Sonnet, fix=Opus)
- [ ] Python files compile without syntax errors

## Validation Commands
Execute these commands to validate the task is complete:

- `grep -n "model:" .claude/commands/review.md | head -5` - Verify haiku model in frontmatter
- `grep -n "ModelName.HAIKU" adws/adw_workflows/adw_plan_build_review.py` - Should show review-related lines
- `grep -n "ModelName.HAIKU" adws/adw_workflows/adw_plan_build_review_fix.py` - Should show review-related lines
- `grep -n "ModelName.OPUS" adws/adw_workflows/adw_plan_build_review.py` - Should only show plan/build/fix steps
- `grep -n "ModelName.OPUS" adws/adw_workflows/adw_plan_build_review_fix.py` - Should only show plan/build/fix steps
- `uv run python -m py_compile adws/adw_workflows/adw_plan_build_review.py` - Verify syntax
- `uv run python -m py_compile adws/adw_workflows/adw_plan_build_review_fix.py` - Verify syntax

## Notes
- The docstring comment in `run_review_step()` that says "defaults to Opus for thorough analysis" should be updated to reflect the change to Haiku
- Haiku is faster and more cost-effective for review tasks while still providing adequate code analysis capability
- Users can still override the model via `input_data.review_model` when creating ADWs
