# TODO: Alpaca MCP Server Not Connecting in Chat

**Created:** 2026-02-01
**Priority:** HIGH (blocks Phase 6 goal)
**Phase:** 6 - Trading Context

## Problem

The Alpaca Agent chat UI is working (credentials passed, account data displayed), but **the MCP server tools are not accessible** to the agent. When a user asks "What is the account status?", the agent:

1. Tries to run `mcp list-prompts` as a **Bash command** (wrong)
2. Says: "It appears I don't have direct access to the Alpaca MCP tools in this environment"
3. Cannot call `mcp__alpaca__get_account_info` or any other Alpaca MCP tools

## Evidence

Screenshot shows:
- Active Account panel works (Balance: $547,910.40, Equity: $950,242.40, Buying Power: $1,313,270.80)
- PAPER badge displays correctly
- Credential selector works
- BUT agent cannot access MCP tools

## Suspected Issue

The `invoke_agent_streaming_with_credential` method in `alpaca_agent_service.py` configures MCP like this:

```python
"mcp_servers": {
    "alpaca": {
        "type": "stdio",
        "command": "uvx",
        "args": ["alpaca-mcp-server", "serve"],
        "env": {
            "ALPACA_API_KEY": api_key,
            "ALPACA_SECRET_KEY": secret_key,
            "ALPACA_PAPER_TRADE": "true" if paper_trade else "false",
        }
    }
},
```

Possible causes:
1. MCP server not starting/connecting properly
2. Claude SDK not recognizing MCP tools with this config
3. `uvx alpaca-mcp-server serve` command may be wrong
4. Environment variable passing issue

## Files to Investigate

- `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py` - `invoke_agent_streaming_with_credential` method (lines 458-638)
- `apps/orchestrator_3_stream/backend/main.py` - chat endpoint (line 1603+)
- Compare with working `invoke_agent_streaming` method that uses env vars

## Recommended Approach

1. **Quick test**: Run `uvx alpaca-mcp-server serve` manually to verify it works
2. **Consult Alpaca Expert**: `/experts:alpaca:question` - ask about correct MCP server configuration
3. **Compare methods**: Check if `invoke_agent_streaming` (env-based) works vs `invoke_agent_streaming_with_credential` (param-based)
4. **Check backend logs**: See what happens during chat request

## Expert to Consult

`/Users/muzz/Desktop/tac/TOD/.claude/commands/experts/alpaca/question.md`

Questions for expert:
- What's the correct way to configure alpaca-mcp-server with Claude SDK?
- How should credentials be passed to MCP servers dynamically?
- Is `uvx alpaca-mcp-server serve` the correct command?

## Success Criteria

- [ ] Agent can call `mcp__alpaca__get_account_info` successfully
- [ ] Agent responds with actual account data from Alpaca API
- [ ] User can ask about positions, orders via chat and get real data

## Related

- Phase 6 VERIFICATION.md marked as passed but this is a functional gap
- TRADE-01, TRADE-02 requirements not fully working
