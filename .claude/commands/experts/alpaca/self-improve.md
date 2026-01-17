---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, TodoWrite
description: Self-improve Alpaca expertise by validating against codebase implementation
argument-hint: [check_git_diff (true/false)] [focus_area (optional)]
---

# Purpose

You maintain the Alpaca expert system's expertise accuracy by comparing the existing expertise file against the actual Alpaca documentation and any codebase implementation. Follow the `Workflow` section to detect and remedy any differences, missing pieces, or outdated information, ensuring the expertise file remains a powerful **mental model** and accurate memory reference for Alpaca Trading API-related tasks.

## Variables

CHECK_GIT_DIFF: $1 default to false if not specified
FOCUS_AREA: $2 default to empty string
EXPERTISE_FILE: .claude/commands/experts/alpaca/expertise.yaml
DOCS_PATH: alpaca_docs/
MAX_LINES: 1000

## Instructions

- This is a self-improvement workflow to keep Alpaca expertise synchronized with the actual documentation and implementation
- Think of the expertise file as your **mental model** and memory reference for all Alpaca Trading API-related functionality
- Always validate expertise against real documentation, not assumptions
- Focus exclusively on Alpaca Trading API functionality (REST endpoints, WebSocket streaming, order types, account management, options trading, MCP server)
- If FOCUS_AREA is provided, prioritize validation and updates for that specific area
- Maintain the YAML structure of the expertise file
- Enforce strict line limit of 1000 lines maximum
- Prioritize actionable, high-value expertise over verbose documentation
- When trimming, remove least critical information that won't impact expert performance
- Git diff checking is optional and controlled by the CHECK_GIT_DIFF variable
- Be thorough in validation but concise in documentation
- Don't include 'summaries' of work done in your expertise when a git diff is checked. Focus on true, important information that pertains to the key Alpaca API functionality and implementation
- Write as a principal engineer that writes CLEARLY and CONCISELY for future engineers so they can easily understand how to read and update functionality surrounding Alpaca Trading API implementation
- Keep in mind, after your thorough search, there may be nothing to be done - this is perfectly acceptable. If there's nothing to be done, report that and stop

## Workflow

1. **Check Git Diff (Conditional)**
   - If CHECK_GIT_DIFF is "true", run `git diff` to identify recent changes to Alpaca-related files
   - If changes detected, note them for targeted validation in step 3
   - If CHECK_GIT_DIFF is "false", skip this step

2. **Read Current Expertise**
   - Read the entire EXPERTISE_FILE to understand current documented expertise
   - Identify key sections: overview, api_endpoints, order_types, websocket_streaming, options_trading, alpaca_py_sdk, alpaca_mcp_server, etc.
   - Note any areas that seem outdated or incomplete

3. **Validate Against Documentation**
   - Read the EXPERTISE_FILE to identify which documentation files are referenced
   - Read those documentation files to understand current API specification:
     - alpaca_docs/trading-api-overview.md
     - alpaca_docs/post-order.md
     - alpaca_docs/get-account.md
     - alpaca_docs/websocket-streaming.md
     - alpaca_docs/options-trading-overview.md
     - alpaca_docs/alpaca-mcp-server.md
     - alpaca_docs/alpaca-py-github-readme.md
     - Other relevant documentation files
   - Compare documented expertise against actual documentation:
     - API endpoint paths and parameters
     - Order types and their supported assets
     - WebSocket event types and message structures
     - Account field definitions
     - Options trading levels and requirements
     - MCP server capabilities and functions
     - Python SDK client classes and request models
   - If FOCUS_AREA is provided, prioritize validation of that specific area
   - If git diff was checked in step 1, pay special attention to changed areas

4. **Identify Discrepancies**
   - List all differences found:
     - Missing endpoints not documented
     - Outdated parameter definitions
     - Changed order type support or time_in_force values
     - New WebSocket event types
     - Removed features still documented
     - Incorrect account field descriptions
     - Updated MCP server function counts
     - New SDK client classes or methods

5. **Update Expertise File**
   - Remedy all identified discrepancies by updating EXPERTISE_FILE
   - Add missing information
   - Update outdated information
   - Remove obsolete information
   - Maintain YAML structure and formatting
   - Ensure all endpoint paths and parameters are accurate
   - Keep descriptions concise and actionable

6. **Enforce Line Limit**
   - Run: `wc -l .claude/commands/experts/alpaca/expertise.yaml`
   - Check if line count exceeds MAX_LINES (1000)
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
   - Verify all critical Alpaca API information is present
   - Ensure line count is within limit
   - Validate YAML syntax by compiling the file:
     - Run: `python3 -c "import yaml; yaml.safe_load(open('.claude/commands/experts/alpaca/expertise.yaml'))"`
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
  - Where in the documentation the correct information was found
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
- Confirm all critical Alpaca expertise is present
- Confirm line count is within limit
- Note any areas that may need future attention

### Documentation References
- List of documentation files validated against
- Key endpoints and functions verified

**Example Report Format:**

```
Self-Improvement Complete

Summary:
- Git diff checked: No
- Focus area: Options trading
- Discrepancies found: 2
- Discrepancies remedied: 2
- Final line count: 850/1000 lines

Discrepancies Found:
1. Missing MCP server function: 'exercise_options_position' not documented
   - Found in: alpaca_docs/alpaca-mcp-server.md
   - Remedied: Added to alpaca_mcp_server.available_functions section

2. Outdated options levels: Level 3 description incomplete
   - Found: alpaca_docs/options-trading-overview.md shows multi-leg support
   - Remedied: Updated options_trading.trading_levels.level_3 with mleg order class

Updates Made:
- Added: exercise_options_position to MCP server functions
- Updated: Options level 3 description with multi-leg details
- Updated: order_class enum to include mleg

Line Limit Enforcement:
- Initial: 850 lines
- Required trimming: No
- Final: 850 lines

Validation Results:
All API endpoints documented with accurate paths
All order types and TIF values validated
WebSocket event types confirmed
Options trading levels accurate
YAML syntax valid (compiled successfully)

Documentation References:
- alpaca_docs/alpaca-mcp-server.md (validated)
- alpaca_docs/options-trading-overview.md (validated)
- alpaca_docs/post-order.md (validated)
- alpaca_docs/websocket-streaming.md (validated)
```
