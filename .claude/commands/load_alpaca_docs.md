---
description: Load Alpaca Markets documentation from their websites into local markdown files our agents can use as context.
allowed-tools: Task, WebFetch, Write, Edit, Bash(ls*), mcp__firecrawl-mcp__firecrawl_scrape
---

# Load Alpaca Docs

Load Alpaca Markets documentation from their respective websites into local markdown files our agents can use as context.

## Variables

DELETE_OLD_DOCS_AFTER_HOURS: 24
OUTPUT_DIRECTORY: alpaca_docs/

## Key Information

This command uses the **docs-scraper** agent (`.claude/agents/docs-scraper.md`) as the subagent for scraping documentation. The docs-scraper agent:
- Launches a Firecrawl-enabled Claude Code subprocess
- Uses the `.mcp.json.firecrawl` configuration for web scraping tools
- Saves scraped content as properly formatted markdown files

## Workflow

1. Read the `alpaca_docs/README.md` file (note: currently named `REAME.md`)
2. See if any `alpaca_docs/<some-filename>.md` file already exists
   1. If it does, see if it was created within the last `DELETE_OLD_DOCS_AFTER_HOURS` hours
   2. If it was, skip it - take a note that it was skipped
   3. If it was not, delete it - take a note that it was deleted
3. For each url in the README that was not skipped, use the Task tool in parallel and follow the `scrape_loop_prompt` as the exact prompt for each Task
   <scrape_loop_prompt>
   Use @agent-docs-scraper agent - pass it the url as the prompt. IMPORTANT: Tell the agent to save the output to the `alpaca_docs/` directory instead of the default `ai_docs/` directory.
   </scrape_loop_prompt>
4. After all Tasks are complete, respond in the `Report Format`

## Report Format

```
Alpaca Docs Report:
- <✅ Success or ❌ Failure>: <url> - <markdown file path>
- ...
```
