---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, TodoWrite
description: Self-improve Options Skew expertise by validating against codebase implementation
argument-hint: [check_git_diff (true/false)] [focus_area (optional)]
---

# Purpose

You maintain the Options Skew expert system's expertise accuracy by comparing the existing expertise file against the actual codebase implementation. Follow the `Workflow` section to detect and remedy any differences, missing pieces, or outdated information, ensuring the expertise file remains a powerful **mental model** and accurate memory reference for options skew analysis tasks.

## Variables

CHECK_GIT_DIFF: $1 default to false if not specified
FOCUS_AREA: $2 default to empty string
EXPERTISE_FILE: .claude/commands/experts/options-skew/expertise.yaml
MAX_LINES: 500

## Instructions

- This is a self-improvement workflow to keep options skew expertise synchronized with the actual codebase
- Think of the expertise file as your **mental model** and memory reference for all options skew analysis functionality
- Always validate expertise against real implementation, not assumptions
- Focus exclusively on options skew-related functionality (pattern recognition, decision logic, strategies, scoring, risk management)
- If FOCUS_AREA is provided, prioritize validation and updates for that specific area
- Maintain the YAML structure of the expertise file
- Enforce strict line limit of 500 lines maximum
- Prioritize actionable, high-value expertise over verbose documentation
- When trimming, remove least critical information that won't impact expert performance
- Git diff checking is optional and controlled by the CHECK_GIT_DIFF variable
- Be thorough in validation but concise in documentation
- Write as a principal engineer that writes CLEARLY and CONCISELY for future engineers so they can easily understand the options skew analysis framework
- Keep in mind, after your thorough search, there may be nothing to be done - this is perfectly acceptable. If there's nothing to be done, report that and stop.

## Workflow

1. **Check Git Diff (Conditional)**
   - If CHECK_GIT_DIFF is "true", run `git diff` to identify recent changes to options skew-related files
   - If changes detected, note them for targeted validation in step 3
   - If CHECK_GIT_DIFF is "false", skip this step

2. **Read Current Expertise**
   - Read the entire EXPERTISE_FILE to understand current documented expertise
   - Identify key sections: overview, core_concepts, data_structures, pattern_recognition, decision_logic, strategies, scoring_algorithm, liquidity_requirements, risk_management, best_practices, thresholds
   - Note any areas that seem outdated or incomplete

3. **Validate Against Codebase**
   - Search for any options skew analysis implementations in the codebase
   - Use Grep to find files containing skew analysis logic:
     - Pattern recognition algorithms
     - Strategy selection functions
     - Confidence scoring implementations
     - Liquidity calculations
   - Compare documented expertise against actual code:
     - Threshold values
     - Decision logic flow
     - Strategy mappings
     - Scoring algorithm weights
   - If FOCUS_AREA is provided, prioritize validation of that specific area
   - If git diff was checked in step 1, pay special attention to changed areas

4. **Identify Discrepancies**
   - List all differences found:
     - Missing patterns or strategies not documented
     - Outdated threshold values
     - Changed scoring algorithm weights
     - New risk management rules
     - Removed features still documented
     - Incorrect formula descriptions

5. **Update Expertise File**
   - Remedy all identified discrepancies by updating EXPERTISE_FILE
   - Add missing information
   - Update outdated information
   - Remove obsolete information
   - Maintain YAML structure and formatting
   - Ensure all formulas and thresholds are accurate
   - Keep descriptions concise and actionable

6. **Enforce Line Limit**
   - Run: `wc -l .claude/commands/experts/options-skew/expertise.yaml`
   - Check if line count exceeds MAX_LINES (500)
   - If line count > MAX_LINES:
     - Identify least important expertise sections that won't impact expert performance:
       - Overly verbose descriptions
       - Redundant examples
       - Low-priority edge cases
     - Trim identified sections
     - Run line count check again
     - REPEAT this sub-workflow until line count <= MAX_LINES
   - Document what was trimmed in the report

7. **Validation Check**
   - Read the updated EXPERTISE_FILE
   - Verify all critical options skew information is present:
     - Core concepts and formulas
     - Pattern classification criteria
     - Strategy selection matrix
     - Confidence scoring algorithm
     - Liquidity requirements
     - Abort conditions
   - Ensure line count is within limit
   - Validate YAML syntax by compiling the file:
     - Run: `python3 -c "import yaml; yaml.safe_load(open('.claude/commands/experts/options-skew/expertise.yaml'))"`
     - Confirm no syntax errors are raised
     - If errors occur, fix the YAML structure and re-validate

## Report

Provide a structured report with the following sections:

### Summary
- Brief overview of self-improvement execution
- Whether git diff was checked
- Focus area (if any)
- Total discrepancies found and remedied
- Final line count vs MAX_LINES

### Discrepancies Found
- List each discrepancy identified:
  - What was incorrect/missing/outdated
  - Where in the codebase the correct information was found
  - How it was remedied

### Updates Made
- Concise list of all updates to EXPERTISE_FILE:
  - Added sections/information
  - Updated sections/information
  - Removed sections/information

### Line Limit Enforcement
- Initial line count
- Final line count
- If trimming was needed:
  - Number of trimming iterations
  - What was trimmed and why
  - Confirmation that trimming didn't impact critical expertise

### Validation Results
- Confirm all critical options skew expertise is present:
  - Core concepts (IV Rank, skew_25_delta, liquidity_score)
  - Pattern recognition criteria
  - Strategy selection matrix
  - Scoring algorithm (base score, additions, subtractions)
  - Risk management rules
- Confirm line count is within limit
- Note any areas that may need future attention

### Codebase References
- List of files validated against
- Key functions and implementations verified

**Example Report Format:**

```
Self-Improvement Complete

Summary:
- Git diff checked: No
- Focus area: None
- Discrepancies found: 2
- Discrepancies remedied: 2
- Final line count: 485/500 lines

Discrepancies Found:
1. Missing strategy: 'Jade Lizard' not fully documented
   - Found in: section2-strategies.yaml
   - Remedied: Added to strategies.key_strategies section

2. Outdated threshold: IV Rank zones shifted
   - Found: very_high now 85-100% (was 80-100%)
   - Remedied: Updated thresholds.iv_rank_zones

Updates Made:
- Added: Jade Lizard strategy details
- Updated: IV Rank zone boundaries
- Removed: Redundant examples in risk_management

Line Limit Enforcement:
- Initial: 510 lines
- Required trimming: Yes
- Iterations: 1
- Trimmed: Verbose examples in scoring_algorithm section
- Final: 485 lines

Validation Results:
- Core concepts: All present and accurate
- Pattern recognition: 4 patterns documented with criteria
- Strategy matrix: 10 strategies mapped
- Scoring algorithm: Base 50, 8 additions, 10 subtractions documented
- Risk management: All abort conditions listed
- YAML syntax: Valid (compiled successfully)

Codebase References:
- No implementation files found (expertise-only domain)
- Validated against original section files
```
