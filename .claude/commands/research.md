---
allowed-tools: WebSearch, WebFetch, Write, Read, Glob, Grep, Bash, Task
description: Conduct comprehensive, citation-backed research on any topic with emphasis on options trading and market analysis
argument-hint: [research query or "in [mode] mode: query"]
model: opus
---

# Purpose

This command orchestrates a multi-agent research workflow to conduct comprehensive, citation-backed research. As the Opus planner, you coordinate a team of specialized agents:

- **Research Scouts** (Haiku): Fast parallel web searches to discover sources
- **Research Fetchers** (Sonnet): Deep content extraction with Firecrawl fallback
- **Research Analysts** (Sonnet): Fact triangulation and section writing

You handle planning, coordination, critical review, and final synthesis.

## Variables

RESEARCH_QUERY: $1
OUTPUT_DIR: app_docs/research
WORKSPACE_DIR: app_docs/research/.workspace
MIN_SOURCES_QUICK: 5
MIN_SOURCES_STANDARD: 8
MIN_SOURCES_DEEP: 12
MIN_SOURCES_ULTRADEEP: 15

## Instructions

- You are the Opus orchestrator - delegate heavy lifting to sub-agents
- Parse RESEARCH_QUERY to extract topic and optional mode
- Supported modes: Quick, Standard, Deep, UltraDeep
- Mode detection: Look for "in quick mode:", "in standard mode:", "in deep mode:", or "in ultradeep mode:" prefix
- Default to Standard mode if not specified
- Use Task tool to launch sub-agents with appropriate models
- Launch scouts in PARALLEL for maximum speed
- Launch fetchers in PARALLEL after scouts complete
- Maintain strict citation discipline - NEVER fabricate sources
- Write final report to OUTPUT_DIR/[topic-slug]-[YYYY-MM-DD].md

## Agent Orchestration

### Model Assignment Strategy

| Agent Role | Model | Task Tool Usage |
|------------|-------|-----------------|
| Planner (You) | opus | N/A - you are the planner |
| Research Scout | haiku | `Task(model: "haiku", subagent_type: "general-purpose")` |
| Research Fetcher | sonnet | `Task(model: "sonnet", subagent_type: "general-purpose")` |
| Research Analyst | sonnet | `Task(model: "sonnet", subagent_type: "general-purpose")` |

### Parallelization Strategy

- **Scouts**: Launch 3-5 scouts in PARALLEL (single message, multiple Task calls)
- **Fetchers**: Launch 2-4 fetchers in PARALLEL after scouts return
- **Analysts**: Launch 1-2 analysts for different section groups

## Workflow

### Phase 1: Planning (Opus - You)

1. **Parse Research Query**
   - Extract the research topic from RESEARCH_QUERY
   - Detect if a specific mode is requested
   - Determine mode based on query complexity if not specified
   - Create workspace directory: `mkdir -p WORKSPACE_DIR`

2. **Generate Search Strategy**
   - Decompose query into 5-10 distinct search angles
   - Group searches for parallel scout assignment
   - Create search plan covering:
     - Academic/institutional sources
     - Industry publications (Bloomberg, WSJ, Investopedia)
     - Recent news and developments
     - Expert analysis and blogs
     - Data and statistics
   - For options topics, include: strategy mechanics, Greeks, risk/reward, IV analysis

### Phase 2: Discovery (Haiku Scouts - Parallel)

3. **Launch Scout Agents in Parallel**

   Use a SINGLE message with MULTIPLE Task tool calls to launch scouts in parallel:

   ```
   Task(
     model: "haiku",
     subagent_type: "general-purpose",
     prompt: "You are a research scout. Execute these WebSearch queries and identify high-value sources:

     QUERIES:
     - [query 1]
     - [query 2]

     For each source found, extract:
     - Title, URL, snippet
     - Credibility score (1-5): 5=academic/.gov, 4=major finance pubs, 3=industry blogs, 2=general news, 1=forums
     - Priority: high/medium/low
     - Flag if site likely needs Firecrawl (paywalls, dynamic content)

     Return results as JSON with sources array. Target: 5-8 sources per scout."
   )
   ```

   Launch 3-5 scouts with different query groups simultaneously.

4. **Collect Scout Results**
   - Wait for all scout tasks to complete
   - Merge discovered sources
   - Deduplicate by URL
   - Sort by credibility and priority
   - Select top sources for fetching (based on mode minimum)

### Phase 3: Extraction (Sonnet Fetchers - Parallel)

5. **Launch Fetcher Agents in Parallel**

   Divide sources among 2-4 fetchers and launch in a SINGLE message:

   ```
   Task(
     model: "sonnet",
     subagent_type: "general-purpose",
     prompt: "You are a research fetcher. Extract detailed content from these sources:

     SOURCES:
     - [url 1] (credibility: X)
     - [url 2] (credibility: X)

     For each source:
     1. Use WebFetch to get content
     2. If WebFetch fails or content is incomplete, use Firecrawl fallback:
        claude --mcp-config .mcp.json.firecrawl --model haiku --dangerously-skip-permissions -p 'Use mcp__firecrawl-mcp__firecrawl_scrape to fetch [URL] in markdown format'
     3. Extract key facts, statistics, and claims
     4. Preserve exact quotes for citation
     5. Note author, date, section context

     Return JSON with source metadata and facts array for each source."
   )
   ```

6. **Collect Fetcher Results**
   - Wait for all fetcher tasks to complete
   - Merge extracted facts
   - Save to WORKSPACE_DIR/facts.json for analyst access

### Phase 4: Analysis (Sonnet Analysts)

7. **Launch Analyst Agents**

   For Deep/UltraDeep modes, launch analysts for different section groups:

   ```
   Task(
     model: "sonnet",
     subagent_type: "general-purpose",
     prompt: "You are a research analyst. Read the extracted facts and write analysis sections.

     FACTS FILE: [workspace path]/facts.json
     TOPIC: [research topic]
     SECTIONS TO WRITE: [assigned sections]

     Guidelines:
     - Triangulate facts across 3+ sources when possible
     - Write in prose (80%+ paragraphs, minimal bullets)
     - Cite every claim with [N] notation
     - 300-500 words per section
     - Flag single-source claims and conflicts

     Return markdown sections with citation mapping."
   )
   ```

8. **Collect Analysis Sections**
   - Merge analyst outputs
   - Review citation consistency
   - Identify gaps needing additional research

### Phase 5: Critical Review & Synthesis (Opus - You)

9. **Critical Review** (Deep, UltraDeep)
   - Verify all citations are traceable
   - Check logical consistency
   - Identify limitations and caveats
   - Ensure balanced perspective
   - Fill any gaps with targeted searches if needed

10. **Final Synthesis** (Opus - You)
    - Write executive summary (50-250 words)
    - Add introduction with methodology overview
    - Write Synthesis & Insights section connecting findings
    - Write Recommendations section
    - For options topics: add Options Strategy Analysis section
    - Compile complete bibliography with working URLs

### Phase 6: Packaging

11. **Generate Final Report**
    - Generate filename slug from topic
    - Compile all sections into final report structure
    - Write to OUTPUT_DIR/[topic-slug]-[YYYY-MM-DD].md
    - Clean up workspace files

## Mode-Specific Execution

| Mode | Scouts | Fetchers | Analysts | Opus Review |
|------|--------|----------|----------|-------------|
| Quick | 2 parallel | 1-2 parallel | Skip (Opus writes) | Light |
| Standard | 3 parallel | 2-3 parallel | 1 | Standard |
| Deep | 4 parallel | 3-4 parallel | 2 parallel | Thorough |
| UltraDeep | 5 parallel | 4 parallel | 2+ parallel | Comprehensive |

## Report Format

Generate the final markdown report with this structure:

```markdown
# [Research Topic] - Deep Research Report

**Generated**: [YYYY-MM-DD]
**Mode**: [Quick/Standard/Deep/UltraDeep]
**Sources Consulted**: [Count]
**Agents Used**: [Scout count] scouts, [Fetcher count] fetchers, [Analyst count] analysts

## Executive Summary

[50-250 word overview - written by Opus]

## Introduction

[Context and methodology - written by Opus]

## Key Findings

### [Finding 1 Title]
[Analyst-written prose with citations]

### [Finding 2 Title]
[Analyst-written prose with citations]

[Continue for 3-8 findings based on mode]

## Synthesis & Insights

[Opus-written cross-cutting analysis]

## Practical Applications

[How to apply findings - Opus synthesis of analyst work]

## Risks & Limitations

[Caveats and limitations - Opus critical review]

## Recommendations

[Actionable next steps - Opus]

## Bibliography

[1] Source Title - URL
[2] Source Title - URL
[Continue for all sources]

## Methodology

Research conducted using multi-agent workflow:
- Phase 1: Query analysis and search planning (Opus)
- Phase 2: Parallel source discovery ([N] Haiku scouts)
- Phase 3: Deep content extraction ([N] Sonnet fetchers)
- Phase 4: Fact triangulation and section writing ([N] Sonnet analysts)
- Phase 5: Critical review and synthesis (Opus)
- Total sources evaluated: [N], Sources cited: [N]
```

### Options Trading Report Addendum

When researching options topics, include after Key Findings:

```markdown
## Options Strategy Analysis

### Strategy Mechanics
[Entry/exit criteria, order structure - from analyst]

### Greeks Profile
- **Delta**: [Directional exposure]
- **Gamma**: [Rate of change]
- **Theta**: [Time decay]
- **Vega**: [Volatility sensitivity]

### Risk/Reward Profile
- **Maximum Loss**: [Amount and conditions]
- **Maximum Gain**: [Amount and conditions]
- **Breakeven Points**: [Price levels]

### Ideal Market Conditions
[IV environment, directional bias, time horizon]

### Position Management
[Sizing, adjustments, exit strategies]
```

## Anti-Hallucination Protocol

- NEVER fabricate sources, statistics, or quotes
- Every factual claim MUST cite a specific source from fetcher output
- Use explicit attribution: "According to [1]..." or "Research from [2] shows..."
- Clearly distinguish between verified facts and analysis/opinion
- If information cannot be verified, state "Unable to verify" or omit
- Cross-verify critical statistics across 3+ sources

## Example Invocations

```
/research iron condor strategies for high IV environment
/research in deep mode: comparing covered calls vs cash-secured puts
/research wheel strategy risk management
/research in ultradeep mode: complete guide to SPY options trading
```
