---
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, TodoWrite
description: Self-improve Orchestrator expertise by validating against codebase implementation
argument-hint: [check_git_diff (true/false)] [focus_area (optional)]
---

# Purpose

You maintain the Orchestrator expert system's expertise accuracy by comparing the existing expertise file against the actual orchestrator codebase implementation, MCP tools, ADW workflows, and agent templates. Follow the `Workflow` section to detect and remedy any differences, missing pieces, or outdated information, ensuring the expertise file remains a powerful **mental model** and accurate memory reference for orchestrator-related tasks.

## Variables

CHECK_GIT_DIFF: $1 default to false if not specified
FOCUS_AREA: $2 default to empty string
EXPERTISE_FILE: .claude/commands/expertise/orchestrator.yaml
ORCHESTRATOR_BACKEND: apps/orchestrator_3_stream/backend/
SYSTEM_PROMPT: apps/orchestrator_3_stream/backend/prompts/orchestrator_agent_system_prompt.md
ADW_WORKFLOWS_DIR: adws/adw_workflows/
AGENT_TEMPLATES_DIR: .claude/agents/
MAX_LINES: 1000

## Instructions

- This is a self-improvement workflow to keep Orchestrator expertise synchronized with the actual implementation
- Think of the expertise file as your **mental model** and memory reference for all Orchestrator-related functionality
- Always validate expertise against real implementation, not assumptions
- Focus exclusively on Orchestrator functionality (MCP management tools, ADW workflows, agent templates, context management, Gemini CLI delegation)
- If FOCUS_AREA is provided, prioritize validation and updates for that specific area
- Maintain the YAML structure of the expertise file
- Enforce strict line limit of 1000 lines maximum
- Prioritize actionable, high-value expertise over verbose documentation
- When trimming, remove least critical information that won't impact expert performance
- Git diff checking is optional and controlled by the CHECK_GIT_DIFF variable
- Be thorough in validation but concise in documentation
- Don't include 'summaries' of work done in your expertise when a git diff is checked. Focus on true, important information that pertains to key Orchestrator functionality and implementation
- Write as a principal engineer that writes CLEARLY and CONCISELY for future engineers so they can easily understand how to read and update functionality surrounding Orchestrator implementation
- Keep in mind, after your thorough search, there may be nothing to be done - this is perfectly acceptable. If there's nothing to be done, report that and stop

## Workflow

1. **Check Git Diff (Conditional)**
   - If CHECK_GIT_DIFF is "true", run `git diff` to identify recent changes to Orchestrator-related files
   - If changes detected, note them for targeted validation in step 3
   - If CHECK_GIT_DIFF is "false", skip this step

2. **Read Current Expertise**
   - Read the entire EXPERTISE_FILE to understand current documented expertise
   - Identify key sections: overview, mcp_management_tools, adw_workflows, agent_templates, context_management, gemini_cli_delegation, orchestration_guidelines, etc.
   - Note any areas that seem outdated or incomplete

3. **Validate Against Implementation**
   - Read the EXPERTISE_FILE to identify which implementation files are referenced
   - Read those implementation files to understand current Orchestrator specification:
     - apps/orchestrator_3_stream/backend/prompts/orchestrator_agent_system_prompt.md
     - apps/orchestrator_3_stream/backend/modules/orchestrator_service.py (get_orchestrator_tools function)
     - apps/orchestrator_3_stream/backend/modules/agent_manager.py
     - apps/orchestrator_3_stream/backend/main.py
     - adws/adw_workflows/adw_plan_build.py
     - adws/adw_workflows/adw_plan_build_review.py
     - adws/adw_workflows/adw_plan_build_review_fix.py
     - All agent templates in .claude/agents/ directory
     - Other relevant implementation files
   - Compare documented expertise against actual implementation:
     - MCP management tool signatures (create_agent, command_agent, check_agent_status, list_agents, delete_agent, interrupt_agent, read_system_logs, report_cost, start_adw, check_adw)
     - Tool parameter types, default values, and optionality
     - ADW workflow types and their file paths
     - Agent template names and their purposes
     - Context window management thresholds (80% compact threshold)
     - Gemini CLI delegation patterns and syntax
     - Model aliases (opus, sonnet, haiku/fast)
     - Working directory handling
     - Session resumption patterns
   - If FOCUS_AREA is provided, prioritize validation of that specific area
   - If git diff was checked in step 1, pay special attention to changed areas

4. **Identify Discrepancies**
   - List all differences found:
     - Missing MCP tools not documented
     - Outdated tool parameter signatures
     - Changed ADW workflow types or file paths
     - New agent templates not documented
     - Removed templates still documented
     - Incorrect context management thresholds
     - Updated Gemini CLI syntax or flags
     - New orchestrator capabilities
     - Changed model aliases or defaults
     - Updated system prompt guidelines

5. **Update Expertise File**
   - Remedy all identified discrepancies by updating EXPERTISE_FILE
   - Add missing information
   - Update outdated information
   - Remove obsolete information
   - Maintain YAML structure and formatting
   - Ensure all tool signatures and parameters are accurate
   - Keep descriptions concise and actionable

6. **Enforce Line Limit**
   - Run: `wc -l .claude/commands/expertise/orchestrator.yaml`
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
   - Verify all critical Orchestrator information is present
   - Ensure line count is within limit
   - Validate YAML syntax by compiling the file:
     - Run: `python3 -c "import yaml; yaml.safe_load(open('.claude/commands/expertise/orchestrator.yaml'))"`
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
  - Where in the implementation the correct information was found
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
- Confirm all critical Orchestrator expertise is present
- Confirm line count is within limit
- Note any areas that may need future attention

### Implementation References
- List of implementation files validated against
- Key tools and workflows verified

## Expertise File Structure

The expertise file should follow this YAML structure:

```yaml
orchestrator:
  overview:
    description: |
      Brief description of the Orchestrator agent and its role in the multi-agent system.
    key_capabilities:
      - Multi-agent coordination and lifecycle management
      - AI Developer Workflow (ADW) execution
      - Context window management and compacting
      - Token-heavy work delegation via Gemini CLI
      - WebSocket streaming for real-time updates
    architecture:
      - Backend: FastAPI + PostgreSQL (NeonDB)
      - Frontend: React + WebSocket
      - Agent SDK: Claude Agent SDK
      - Working directory: Configurable via --cwd or env var

  mcp_management_tools:
    agent_management:
      create_agent:
        signature: "create_agent(name: string, system_prompt?: string, model?: string, subagent_template?: string)"
        description: |
          Create a new Agent with specified configuration. Use subagent_template for pre-configured agents.
        parameters:
          name: "Unique identifier for the agent (required)"
          system_prompt: "Instructions defining role/behavior (optional if using template)"
          model: "Model to use: opus (default), sonnet, haiku/fast, or full name"
          subagent_template: "Name of subagent template to apply (optional)"
        notes:
          - "If no name provided, infer from request or use tech-related two-word name"
          - "Template applies pre-configured system prompt, tools, and model"

      list_agents:
        signature: "list_agents()"
        description: "List all registered agents with status and metadata"

      command_agent:
        signature: "command_agent(agent_name: string, command: string)"
        description: "Send a task/command to an existing agent"
        parameters:
          agent_name: "Name of the agent to command"
          command: "Task description or instruction"
        special_commands:
          - "/compact - Clear conversation history, preserve capabilities"
          - "ultrathink - Trigger thinking mode (if user requests)"

      check_agent_status:
        signature: "check_agent_status(agent_name: string, tail_count = 10, offset = 0, verbose_logs = false)"
        description: "Get detailed agent status with optional activity logs"
        parameters:
          agent_name: "Name of the agent"
          tail_count: "Number of recent events to show (default: 10)"
          offset: "Skip first N records for pagination (default: 0)"
          verbose_logs: "false = AI summaries (default), true = raw event details"
        usage_notes:
          - "Don't be overeager - takes time for agents to complete tasks"
          - "Use offset with tail_count to paginate (e.g., offset=10, tail_count=10 shows records 11-20)"

      delete_agent:
        signature: "delete_agent(agent_name: string)"
        description: "Delete an agent and cleanup its resources"

      interrupt_agent:
        signature: "interrupt_agent(agent_name: string)"
        description: "Interrupt a running agent's execution"

      read_system_logs:
        signature: "read_system_logs(offset = 0, limit = 50, message_contains?: string, level?: string)"
        description: "Read application system logs with filtering. Returns newest logs first."
        parameters:
          offset: "Skip first N records (default: 0)"
          limit: "Max records to return (default: 50)"
          message_contains: "Filter by message text (optional)"
          level: "Filter by level: DEBUG, INFO, WARNING, ERROR (optional)"

      report_cost:
        signature: "report_cost()"
        description: |
          Report orchestrator's costs, context window usage, and session ID.
          Shows token usage, cost, and current session ID.
        usage_notes:
          - "Use this when user asks 'what's your session ID?' or 'what's the orchestrator session ID?'"

    adw_workflow_tools:
      start_adw:
        signature: "start_adw(name_of_adw: string, workflow_type: string, prompt: string, description?: string)"
        description: |
          Start an AI Developer Workflow. Returns adw_id for tracking. Runs asynchronously.
        parameters:
          name_of_adw: "Human-readable name (e.g., 'oauth-feature', 'fix-login-bug')"
          workflow_type: "Type of workflow: plan_build, plan_build_review, plan_build_review_fix"
          prompt: "The actual task/prompt for the ADW to execute"
          description: "Optional detailed description of what ADW should accomplish"
        returns: "adw_id (UUID) for tracking the workflow"
        notes:
          - "Maps to adws/adw_workflows/adw_<workflow_type>.py"

      check_adw:
        signature: "check_adw(adw_id: string, tail_count = 10, event_type?: string, include_step_details = false)"
        description: "Check ADW status and recent activity. Returns consolidated status + logs."
        parameters:
          adw_id: "The UUID of the ADW to check (required)"
          tail_count: "Number of recent events to show (default: 10)"
          event_type: "Filter by: StepStart, StepEnd, PreToolUse, PostToolUse (optional)"
          include_step_details: "Show full payload for each event (default: false)"

  adw_workflows:
    overview: |
      AI Developer Workflows (ADWs) are multi-step, autonomous workflows combining agents and deterministic code.
    available_types:
      plan_build:
        file: "adws/adw_workflows/adw_plan_build.py"
        description: "Plan and build implementation"
      plan_build_review:
        file: "adws/adw_workflows/adw_plan_build_review.py"
        description: "Plan, build, and review implementation"
      plan_build_review_fix:
        file: "adws/adw_workflows/adw_plan_build_review_fix.py"
        description: "Plan, build, review, and fix implementation"

    when_to_use:
      use_adw:
        - "Complex multi-step feature"
        - "Predefined workflow pattern"
        - "User wants hands-off execution"
      use_direct_agents:
        - "Quick one-off task"
        - "Interactive debugging"
        - "User wants step-by-step control"

    guidelines:
      - "DO NOT interfere with running ADWs unless user explicitly asks"
      - "Monitor sparingly - ADWs are designed to run autonomously"
      - "Use check_adw only when: user asks for status, need to report progress, error is suspected"
      - "Let ADWs complete - they handle their own step transitions and error recovery"
      - "Report the adw_id to user so they can reference it later"
      - "Once started, your role is to observe, not control. Only intervene if explicitly requested"

  agent_templates:
    overview: |
      Pre-configured agent templates with specialized system prompts, tools, and models.
      Located in .claude/agents/ directory.
    available_templates:
      build-agent:
        file: ".claude/agents/build-agent.md"
        purpose: "Specialized file implementation engineer for writing ONE specific file"
      docs-scraper:
        file: ".claude/agents/docs-scraper.md"
        purpose: "Documentation scraping specialist for fetching and saving docs as markdown"
      meta-agent:
        file: ".claude/agents/meta-agent.md"
        purpose: "Generates new, complete Claude Code sub-agent configuration files"
      planner:
        file: ".claude/agents/planner.md"
        purpose: "Creates structured plans, breaks down tasks into steps"
      playwright-validator:
        file: ".claude/agents/playwright-validator.md"
        purpose: "Browser automation validator using Playwright MCP tools"
      research-analyst:
        file: ".claude/agents/research-analyst.md"
        purpose: "Research synthesis for triangulating facts and building citations"
      research-fetcher:
        file: ".claude/agents/research-fetcher.md"
        purpose: "Deep content extraction with Firecrawl fallback"
      research-scout:
        file: ".claude/agents/research-scout.md"
        purpose: "Fast parallel web search for research discovery"
      scout-report-suggest-fast:
        file: ".claude/agents/scout-report-suggest-fast.md"
        purpose: "Fast read-only codebase analysis and reporting"
      scout-report-suggest:
        file: ".claude/agents/scout-report-suggest.md"
        purpose: "Thorough read-only codebase analysis and reporting"
      theta-collector:
        file: ".claude/agents/theta-collector.md"
        purpose: "Options theta collection analysis specialist"

  context_management:
    compact_threshold: "80%"
    workflow:
      - "When agent reaches 80% context usage, suggest compacting to user"
      - "Explain that compacting clears old conversation history while preserving capabilities"
      - "Offer to compact by asking if they'd like you to proceed"
      - "To compact: command_agent(agent_name, '/compact')"
      - "After compacting: agent retains system prompt, tools, capabilities; conversation history cleared; context resets to ~0%"
    monitoring:
      - "Check context usage via report_cost or after check_agent_status"
      - "Proactively suggest compacting before hitting 90%+ usage"

  gemini_cli_delegation:
    overview: |
      For tasks requiring analysis of large codebases or many files, use Gemini CLI via Bash.
      Preserves orchestrator context window while leveraging Gemini's massive 2M token context.

    syntax: "gemini \"@path/ Your prompt here\""

    when_to_use:
      - "Analyzing entire directories (>20 files or >100KB total)"
      - "Reviewing codebases for patterns across many files"
      - "Comparing multiple large files simultaneously"
      - "Verifying feature implementations across the project"
      - "Scraping and analyzing large documentation sets"
      - "Processing large API responses or data dumps"
      - "Any read-only analysis consuming >30% of context"

    when_not_to_use:
      - "Writing or editing code (Gemini CLI is read-only)"
      - "Tasks requiring tool use (WebFetch, database, MCP servers)"
      - "Interactive debugging requiring back-and-forth"
      - "Small file analysis (<10 files, <50KB total)"

    examples:
      single_file: "gemini \"@src/main.py Explain this file's purpose and architecture\""
      multiple_files: "gemini \"@package.json @src/index.js Analyze the dependencies used\""
      entire_directory: "gemini \"@src/ Summarize the architecture of this codebase\""
      multiple_directories: "gemini \"@src/ @tests/ Analyze test coverage for the source code\""
      current_directory: "gemini \"@./ Give me an overview of this project structure\""
      all_files_flag: "gemini --all_files \"Analyze the project structure and dependencies\""

    workflow_pattern:
      - "Plan (Orchestrator): Determine what analysis is needed and formulate query"
      - "Delegate (Gemini): Execute gemini via Bash with appropriate @ includes"
      - "Synthesize (Orchestrator): Interpret Gemini's output and decide next steps"
      - "Act (Agents): Command agents to implement changes based on findings"

    notes:
      - "Paths in @ syntax are relative to current working directory"
      - "Gemini CLI is read-only - cannot modify files or use tools"
      - "For very large outputs, ask Gemini to summarize or focus on specific aspects"
      - "If gemini command not available, fall back to scout agents with Read/Glob/Grep"
      - "Always verify critical findings by having an agent read specific files mentioned"

  orchestration_guidelines:
    principles:
      - "Be Strategic: Think about which agent is best suited for each task"
      - "Be Efficient: Don't create redundant agents - reuse existing ones when appropriate"
      - "Be Informative: Explain your decisions and what's happening"
      - "Be Proactive: Check agent status when tasks are dispatched to provide updates"
      - "Be Helpful: If a task fails, investigate using logs and try alternative approaches"

    agent_specialization_examples:
      builder: "For implementing features, writing code"
      reviewer: "For code review, quality checks"
      tester: "For writing and running tests"
      documenter: "For creating documentation"
      debugger: "For troubleshooting issues"

    workflow_pattern:
      - "Analyze the user's request"
      - "Plan which agents are needed"
      - "Create or select appropriate agents"
      - "Dispatch tasks with clear instructions"
      - "Monitor progress using check_agent_status"
      - "Report results back to the user"

    important_notes:
      - "Agents work in their configured working directories"
      - "Each agent maintains its own session and memory"
      - "You can command agents multiple times - they remember previous interactions"
      - "Always provide clear, specific instructions to agents"
      - "Check agent status to provide progress updates to user"
      - "Use system logs to debug issues"
      - "You have Bash tool for gathering information or debugging"
      - "Let command-level agents do the heavy lifting (writing, editing, testing)"
      - "Don't be overeager to check agent status - it takes time for them to complete tasks"

  model_configuration:
    aliases:
      opus: "claude-opus-4-5-20251101 (highest capability, default)"
      sonnet: "claude-sonnet-4-5-20250929 (balanced performance, secondary, do not prefer)"
      haiku: "claude-haiku-4-5-20251001 (faster, lower cost)"
      fast: "claude-haiku-4-5-20251001 (alias for haiku)"
    notes:
      - "Can pass full model name directly instead of alias"
      - "Templates may specify default model, which can be overridden"

  session_management:
    cli_arguments:
      session: "Resume existing orchestrator session (session ID)"
      cwd: "Set working directory for orchestrator and agents"

    behavior:
      new_session: "Run without --session to create fresh orchestrator"
      resume_session: "Run with --session <session_id> to resume existing orchestrator"
      working_directory: "Use --cwd to override, or ORCHESTRATOR_WORKING_DIR env var, or config default"

    notes:
      - "Session ID is set after first interaction with new orchestrator"
      - "Use report_cost to get current orchestrator session ID"
      - "Session ID must exist in database to resume"

  database_backend:
    type: "PostgreSQL (NeonDB)"
    tables:
      - "orchestrator_agents: Main orchestrator state, costs, session"
      - "command_level_agents: Created agents, status, metadata"
      - "chat_messages: Conversation history"
      - "system_logs: Application logs"
      - "orchestrator_events: Activity tracking"

    connection:
      - "Connection pool initialized on startup"
      - "Async operations via asyncpg"

  websocket_streaming:
    overview: |
      Real-time streaming of orchestrator responses via WebSocket.
      Frontend connects to ws://localhost:8000/ws for live updates.

    event_types:
      - "text_delta: Streaming text chunks"
      - "tool_use: Tool execution events"
      - "thinking: Extended thinking blocks"
      - "stop: Response completion"
```

**Example Report Format:**

```
Self-Improvement Complete

Summary:
- Git diff checked: No
- Focus area: MCP management tools
- Discrepancies found: 3
- Discrepancies remedied: 3
- Final line count: 1150/1200 lines

Discrepancies Found:
1. Missing parameter: check_agent_status missing 'offset' parameter
   - Found in: apps/orchestrator_3_stream/backend/modules/orchestrator_service.py
   - Remedied: Added offset parameter to check_agent_status signature

2. Outdated ADW workflow type: Missing 'plan_build_review_fix' workflow
   - Found: adws/adw_workflows/adw_plan_build_review_fix.py exists
   - Remedied: Added plan_build_review_fix to available_types section

3. New agent template: theta-collector not documented
   - Found: .claude/agents/theta-collector.md exists
   - Remedied: Added theta-collector to agent_templates.available_templates section

Updates Made:
- Added: offset parameter to check_agent_status tool
- Added: plan_build_review_fix ADW workflow type
- Added: theta-collector agent template
- Updated: ADW guidelines to emphasize non-interference

Line Limit Enforcement:
- Initial: 1150 lines
- Required trimming: No
- Final: 1150 lines

Validation Results:
All MCP management tools documented with accurate signatures
All ADW workflow types validated
All agent templates from .claude/agents/ documented
Context management thresholds correct (80%)
Gemini CLI syntax validated
YAML syntax valid (compiled successfully)

Implementation References:
- apps/orchestrator_3_stream/backend/modules/orchestrator_service.py (validated)
- apps/orchestrator_3_stream/backend/prompts/orchestrator_agent_system_prompt.md (validated)
- adws/adw_workflows/ (all 3 workflow files validated)
- .claude/agents/ (all 11 agent templates validated)
```
