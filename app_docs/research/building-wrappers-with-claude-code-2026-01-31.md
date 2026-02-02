# Building Wrappers with Claude Code - Deep Research Report

**Generated**: 2026-01-31
**Mode**: Standard
**Sources Consulted**: 12
**Agents Used**: 3 scouts, 3 fetchers, 1 analyst (Opus synthesis)

## Executive Summary

Building wrappers with Claude Code encompasses four distinct approaches: (1) the **Agent SDK** for programmatic embedding of Claude Code capabilities in Python/TypeScript applications, (2) **Skills and Commands** for extending Claude Code with custom workflows, (3) **Subagents** for isolated specialized task execution, and (4) **MCP integration** for external tool connectivity. The ecosystem has matured significantly, with the renamed "Claude Agent SDK" providing the same tools, agent loop, and context management that power Claude Code itself. Community wrappers like `anyclaude` and `claude-code-mcp` demonstrate production patterns for multi-provider support and MCP-based delegation.

## Introduction

This research examines the complete landscape for building wrappers and extensions around Claude Code, Anthropic's CLI-based AI coding assistant. The investigation covers official Anthropic documentation, the Agent SDK, community-maintained wrapper projects, and expert guides on configuration patterns.

The term "wrapper" in this context spans multiple implementation patterns:
- **API wrappers**: Libraries that provide alternative interfaces (OpenAI-compatible, multi-provider)
- **Configuration wrappers**: Skills, commands, and plugins that extend Claude Code's behavior
- **Integration wrappers**: MCP servers that expose Claude Code capabilities to other tools
- **Programmatic wrappers**: SDK-based applications that embed Claude Code functionality

## Key Findings

### 1. The Claude Agent SDK: Programmatic Wrapper Foundation

The Claude Code SDK has been officially renamed to the **Claude Agent SDK** [1]. This SDK provides the same tools, agent loop, and context management that power Claude Code, available as a library for Python and TypeScript.

**Built-in Tools** [1]:
- `Read` - Read any file
- `Write` - Create files
- `Edit` - Precise file modifications
- `Bash` - Terminal commands, scripts, git
- `Glob` - Find files by pattern
- `Grep` - Search with regex
- `WebSearch` - Web search
- `WebFetch` - Fetch web pages
- `AskUserQuestion` - Clarifying questions

**SDK Hook System** [1]: Hooks use callback functions to validate, log, block, or transform agent behavior:
- `PreToolUse` - Before tool execution (can block)
- `PostToolUse` - After tool execution
- `Stop` - On completion
- `SessionStart` / `SessionEnd` - Lifecycle events
- `UserPromptSubmit` - Before processing input

**Basic SDK Usage** (Python):
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"])
    ):
        print(message)

asyncio.run(main())
```

**Installation**:
```bash
pip install claude-agent-sdk  # Python
npm install @anthropic-ai/claude-agent-sdk  # TypeScript
```

**Key Branding Restriction** [1]: Third-party applications cannot use "Claude Code" or "Claude Code Agent" in naming. Permitted alternatives: "Claude Agent", "Claude", or "{YourAgentName} Powered by Claude".

### 2. Skills: Automatic Capability Wrappers

Skills extend Claude Code with custom capabilities that activate automatically based on context matching [2]. They follow the **Agent Skills (agentskills.io)** open standard.

**SKILL.md Structure** [2]:
```yaml
---
name: explain-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works.
---

When explaining code, always include:
1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show the flow
3. **Walk through the code**: Explain step-by-step
4. **Highlight a gotcha**: Common mistakes or misconceptions
```

**Skill Storage Locations** [2]:
| Location | Scope | Priority |
|----------|-------|----------|
| `~/.claude/skills/` | Personal | High |
| `.claude/skills/` | Project | Medium |
| `<plugin>/skills/` | Plugin | Low |

**Key Features**:
- **String substitution**: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, `${CLAUDE_SESSION_ID}` [2]
- **Dynamic context injection**: `!`command`` syntax runs shell commands before sending to Claude [2]
- **Subagent execution**: `context: fork` runs skill in isolated context [2]
- **Extended thinking**: Include "ultrathink" anywhere in skill content to enable [2]

**Best Practice** [2]: Keep SKILL.md under 500 lines. Move detailed reference material to separate files.

### 3. Subagents: Isolated Execution Wrappers

Subagents are specialized AI assistants that handle specific tasks in isolated context windows [3].

**Built-in Subagents** [3]:
| Agent | Model | Mode | Purpose |
|-------|-------|------|---------|
| Explore | Haiku | Read-only | Fast code exploration |
| Plan | Inherit | Read-only | Research and planning |
| general-purpose | Inherit | All tools | Full capabilities |

**Custom Subagent Definition** [3]:
```yaml
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze code and provide
specific, actionable feedback on quality, security, and best practices.
```

**Subagent Patterns** [3, 8]:
1. **Read-only subagents**: Limited tools (Read, Grep, Glob, Bash) for safe analysis
2. **Domain-specific subagents**: Specialized prompts for SQL, APIs, debugging
3. **Conditional tool access with hooks**: PreToolUse hooks validate operations
4. **Skill preloading**: Inject skill content at startup with `skills:` field
5. **Background execution**: `Ctrl+B` backgrounds running tasks
6. **Parallel research**: Multiple subagents for independent investigations

**Critical Limitation** [3]: Subagents cannot spawn other subagents (no nesting).

### 4. Community Wrapper Projects

**anyclaude** [4] - Multi-provider LLM wrapper:
```bash
# Installation
pnpm install -g anyclaude

# Usage with different providers
anyclaude --model openai/gpt-5-mini
anyclaude --model google/gemini-pro
anyclaude --model xai/grok-3
```

Architecture: Spawns HTTP server translating between Anthropic's format and AI SDK format, enabling closed Anthropic endpoint specification to work with multiple providers [4].

**claude-code-mcp** [5] - MCP server wrapper:
```json
{
  "claude-code-mcp": {
    "command": "npx",
    "args": ["-y", "@steipete/claude-code-mcp@latest"]
  }
}
```

Use case: Enables LLMs like Cursor to execute Claude Code with permissions automatically bypassed for complex multi-step operations [5].

**claude-code-openai-wrapper** [6] - OpenAI API compatibility:
```python
from claude_code_openai_wrapper import ClaudeAPI

api = ClaudeAPI(api_key='YOUR_API_KEY')
response = api.generate_text(prompt='Hello, world!')
```

### 5. Hooks: Event-Driven Wrapper Automation

Hooks provide event-driven automation that fires on tool usage [7, 8].

**Hook Configuration** (hooks/hooks.json):
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/run-oxlint.sh"
          }
        ]
      }
    ]
  }
}
```

**Hook Types** [8]:
- **Command hooks**: Fast, predictable shell execution
- **Prompt hooks**: Flexible, context-aware LLM decision-making

**Critical Note** [7]: Claude Code v2.1+ auto-loads hooks from `hooks/hooks.json`. Do NOT declare hooks in plugin.json to avoid duplicate detection errors.

### 6. MCP Integration Wrappers

MCP (Model Context Protocol) servers extend Claude Code with external tool access [9].

**Adding MCP Servers**:
```bash
claude mcp add playwright npx @playwright/mcp@latest
claude mcp add my-server -e API_KEY=123 -- /path/to/server arg1 arg2
```

**Context Window Impact** [7]: 200k context window can shrink to 70k with excessive MCP tools. Optimization rule: Under 10 MCPs enabled per project, under 80 tools active.

**MCP Tool Invocation** [9]:
```
/mcp__playwright__create-test [args]
```

## Synthesis & Insights

The Claude Code wrapper ecosystem has evolved into a mature, multi-layered architecture:

**Layer 1 - Core SDK**: The Agent SDK provides programmatic access to Claude Code's full capabilities, enabling embedded AI coding assistants in custom applications.

**Layer 2 - Configuration Extensions**: Skills, commands, and subagents create reusable behavior patterns without modifying Claude Code itself.

**Layer 3 - Protocol Adapters**: MCP servers and API wrappers translate between Claude Code and external systems (other LLMs, IDEs, databases).

**Key Architectural Pattern**: The consistent use of YAML frontmatter for configuration (skills, subagents, commands) enables a declarative approach where Claude Code automatically activates appropriate behaviors based on context matching rather than explicit invocation.

**Context Window Optimization** is critical: All sources emphasize monitoring token consumption with `/context` and limiting MCP tools. The 200k→70k degradation with excessive tools represents a significant operational constraint.

## Practical Applications

### Building an API Wrapper
1. Use Claude Agent SDK as foundation
2. Implement custom hooks for audit logging
3. Define subagents for specialized domains
4. Control permissions with `allowed_tools` option

### Extending Claude Code for Team Use
1. Create project-level skills in `.claude/skills/`
2. Define team conventions in CLAUDE.md hierarchy
3. Add hooks for quality enforcement (linting, testing)
4. Package as plugin for distribution

### Multi-Provider Support
1. Use anyclaude pattern with AI SDK translation layer
2. Configure environment variables per provider
3. Implement reasoning effort controls for different model families

## Risks & Limitations

1. **Branding restrictions**: Cannot use "Claude Code" in third-party product names
2. **Subagent depth**: No nested subagent spawning limits recursive architectures
3. **Context degradation**: MCP tool proliferation significantly reduces effective context
4. **Plugin rules**: Plugin system cannot distribute rules (must install manually)
5. **Permission bypass**: MCP wrappers using `--dangerously-skip-permissions` require careful security review

## Recommendations

1. **Start with Skills**: For simple workflow extensions, skills provide the lowest friction path with automatic activation
2. **Use SDK for embedding**: When building applications that embed Claude capabilities, the Agent SDK provides full control with proper hook support
3. **Monitor context aggressively**: Implement `/context` checks in workflows and limit MCP tools
4. **Leverage existing wrappers**: For multi-provider support or MCP integration, community projects (anyclaude, claude-code-mcp) provide battle-tested patterns
5. **Follow implementation order**: CLAUDE.md → Settings → Skills → Commands → Hooks → Subagents → MCP

## Bibliography

[1] Agent SDK overview - Claude Docs - https://platform.claude.com/docs/en/agent-sdk/overview

[2] Extend Claude with skills - Claude Code Docs - https://code.claude.com/docs/en/skills

[3] Create custom subagents - Claude Code Docs - https://code.claude.com/docs/en/sub-agents

[4] anyclaude - Use Claude Code with any LLM - https://github.com/coder/anyclaude

[5] claude-code-mcp - MCP Server for Claude Code - https://github.com/steipete/claude-code-mcp

[6] claude-code-openai-wrapper - OpenAI API Wrapper - https://github.com/ALTIbaba/claude-code-openai-wrapper

[7] everything-claude-code - Production Plugin - https://github.com/affaan-m/everything-claude-code

[8] Understanding Claude Code Full Stack Architecture - https://alexop.dev/posts/understanding-claude-code-full-stack/

[9] Claude Code CLI Cheatsheet - Shipyard Build - https://shipyard.build/blog/claude-code-cheat-sheet/

[10] Claude Code: Best practices for agentic coding - https://www.anthropic.com/engineering/claude-code-best-practices

[11] Common workflows - Claude Code Docs - https://code.claude.com/docs/en/common-workflows

[12] Connect Claude Code to tools via MCP - https://docs.anthropic.com/en/docs/claude-code/mcp

## Methodology

Research conducted using multi-agent workflow:
- Phase 1: Query analysis and search planning (Opus)
- Phase 2: Parallel source discovery (3 Haiku scouts)
- Phase 3: Deep content extraction (3 Sonnet fetchers)
- Phase 4: Fact triangulation and synthesis (Opus)
- Total sources evaluated: 35+, Sources cited: 12
