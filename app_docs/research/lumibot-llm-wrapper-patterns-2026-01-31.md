# Building LLM Wrappers for Lumibot - Deep Research Report

**Generated**: 2026-01-31
**Mode**: Standard
**Sources Consulted**: 45+
**Agents Used**: 4 scouts, 4 fetchers

## Executive Summary

Building an LLM wrapper for Lumibot is not only feasible but follows well-established patterns already proven in production systems. Three primary approaches exist: (1) **Tool-Based Agents** using Claude's function calling to expose Lumibot operations as callable tools, (2) **MCP Server Wrappers** that implement the Model Context Protocol for standardized AI-framework integration, and (3) **Multi-Agent Architectures** like TradingAgents that coordinate specialized LLM agents for different trading functions.

No pre-built Lumibot-Claude wrapper exists, but the building blocks are mature: Anthropic's official tool use documentation, the Claude Agent SDK, multiple Python wrapper libraries (claudetools, claudette), and reference implementations from the MCP ecosystem (130+ official servers). The recommended approach is a **Tool-Based MCP Server** that wraps Lumibot's Strategy class methods as discoverable tools Claude can invoke through natural language.

## Introduction

This research addresses the question: *What methods, prompts, or skills are available for building an LLM wrapper around Lumibot's trading framework?*

Lumibot is a Python-based algorithmic trading framework that requires users to write code directly. There is no built-in natural language interface. A "wrapper" in this context means an intermediary layer that:

1. Accepts natural language commands from a user
2. Translates them into Lumibot Python operations
3. Executes the operations safely
4. Returns results in conversational form

The research discovered three viable architectural patterns, multiple existing libraries that reduce implementation effort, and concrete examples from production trading systems.

## Key Findings

### Finding 1: Tool-Based Architecture is the Recommended Pattern

The most effective approach for wrapping Lumibot follows the **Tool-Based Agent** pattern, which is the same architecture used by the Alpaca MCP Server. According to Anthropic's official documentation, this involves defining Lumibot operations as "tools" that Claude can call [1].

The pattern works as follows:

```python
TOOLS = [
    {
        "name": "create_order",
        "description": "Create a buy or sell order for a stock",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "quantity": {"type": "integer", "description": "Number of shares"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "order_type": {"type": "string", "enum": ["market", "limit"]}
            },
            "required": ["symbol", "quantity", "side"]
        }
    }
]
```

Each tool definition maps directly to a Lumibot Strategy method. When Claude decides to use a tool, your wrapper executes the actual Lumibot code [2].

**Pros**: Safe (only predefined operations), flexible, extensible, matches production patterns
**Cons**: Requires upfront design of tool schemas

### Finding 2: MCP (Model Context Protocol) Provides a Standardized Wrapper Framework

Anthropic's Model Context Protocol is an open standard specifically designed for creating AI-accessible wrappers around external systems [3]. The protocol uses a client-server architecture where:

- **MCP Servers** expose tools, resources, and prompts
- **MCP Clients** (like Claude) discover and invoke these capabilities
- Communication happens via JSON-RPC 2.0 over stdio or HTTP

The MCP ecosystem already contains **130+ official server implementations** demonstrating the wrapper pattern [4]. Key design patterns from production MCP servers include:

1. **Service Wrapping**: Wrap external APIs as discoverable tools
2. **Workflow Consolidation**: Combine multi-step operations into atomic tools
3. **Context Filtering**: Process data server-side, return summaries to reduce token usage
4. **Progressive Disclosure**: Expose tool subsets based on context

A Lumibot MCP Server would expose tools like `get_portfolio`, `create_order`, `run_backtest`, and `get_price` that Claude discovers and invokes through natural conversation.

### Finding 3: Existing Python Libraries Reduce Implementation Effort

Several Python libraries already implement Claude wrapper patterns that can be adapted for Lumibot:

**claudetools** [5]: A Python library enabling function calling with Claude 3. Uses Pydantic BaseModel for type-safe tool definitions:

```python
from claudetools import Tool, BaseModel, Field

class CreateOrder(BaseModel):
    symbol: str = Field(description="Stock ticker")
    quantity: int = Field(description="Number of shares")
    side: str = Field(description="buy or sell")

tool = Tool(model=CreateOrder)
```

**claudette** [6]: A high-level wrapper that converts Python functions with docstrings into tools automatically:

```python
def create_order(symbol: str, quantity: int, side: str) -> str:
    """Create a buy or sell order for a stock.

    Args:
        symbol: Stock ticker symbol like AAPL
        quantity: Number of shares to trade
        side: Either 'buy' or 'sell'
    """
    # Lumibot code here
    return f"Order created: {side} {quantity} {symbol}"
```

Both libraries handle the Claude API communication, tool schema generation, and response parsing.

### Finding 4: Multi-Agent Trading Frameworks Provide Architectural Blueprints

The **TradingAgents** framework demonstrates a production-ready multi-agent architecture for LLM-based trading [7]. It uses specialized agents:

- **Fundamental Analyst**: Evaluates company financials
- **Sentiment Analyst**: Processes news and social signals
- **Technical Analyst**: Analyzes price patterns
- **Trader Agent**: Executes decisions
- **Risk Manager**: Validates trades against rules

Key architectural patterns from TradingAgents:

1. **Structured Reports over Unstructured Dialogue**: Agents communicate via structured JSON, not free-form text
2. **Quick vs Deep Thinking Models**: Use fast models (Haiku) for routine decisions, powerful models (Opus) for complex analysis
3. **Debate Mechanisms**: Multiple agents discuss before final decisions
4. **ReAct Framework**: Agents reason, act, and observe in loops

The **FinMem** framework adds a **layered memory system** mimicking human trader cognition [8], with working memory, episodic memory, and semantic memory modules.

### Finding 5: Lumibot's Architecture is Wrapper-Friendly

Lumibot's Strategy class (5,317 lines) follows a React.js-inspired lifecycle pattern that maps naturally to tool definitions [9]:

**Lifecycle Methods (ideal for AI-driven decisions)**:
- `initialize()` - Setup strategy parameters
- `on_trading_iteration()` - Core decision loop
- `before_market_opens()` - Pre-market preparation
- `after_market_closes()` - End-of-day processing
- `trace_stats()` - Logging and audit trails

**Order Methods (direct tool candidates)**:
- `create_order(symbol, quantity, side, order_type)`
- `submit_order(order)`
- `cancel_order(order)`
- `get_position(symbol)`
- `get_last_price(symbol)`

**Data Access Methods**:
- `get_bars(symbol, timeframe, length)` - Historical OHLCV data
- `portfolio_value` - Current portfolio worth
- `cash` - Available cash

Lumibot already includes `CLAUDE.md` and `AGENTS.md` files in its repository, indicating the maintainers have considered AI integration [10].

### Finding 6: Critical Implementation Requirements

Anthropic's documentation emphasizes several critical requirements for effective tool wrappers [11]:

1. **Extremely Detailed Descriptions**: Tool descriptions should be 3-4+ sentences explaining what the tool does, when to use it, and what each parameter means. This is "the most important factor" for reliable tool selection.

2. **Proper Error Handling**: Return errors with `is_error: true` flag. Claude will retry 2-3 times before giving up.

3. **Token Optimization**: Use the Tool Search Tool pattern for large tool sets (95% context savings). Process data server-side and return summaries.

4. **Safety Constraints**: Implement position limits, order size caps, and confirmation prompts for destructive actions.

## Synthesis & Insights

The research reveals a clear implementation path: **build an MCP Server that wraps Lumibot's Strategy methods as tools**.

This approach combines:
- The standardized discovery and invocation patterns of MCP
- The type-safe tool definitions from claudetools/Pydantic
- The multi-agent coordination patterns from TradingAgents
- The lifecycle hooks from Lumibot's Strategy class

The wrapper architecture should follow this layered design:

```
┌─────────────────────────────────────┐
│  User (Natural Language)            │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Claude (LLM with Tool Use)         │
│  - Understands intent               │
│  - Selects appropriate tools        │
│  - Formats parameters               │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Lumibot MCP Server (Wrapper)       │
│  - Exposes tools via MCP protocol   │
│  - Validates inputs                 │
│  - Translates to Lumibot calls      │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Lumibot Strategy (Execution)       │
│  - Creates/submits orders           │
│  - Fetches market data              │
│  - Runs backtests                   │
└─────────────────────────────────────┘
```

The key insight is that **the wrapper layer is thin**. Most complexity lives in:
1. Claude's understanding (already solved by Anthropic)
2. Lumibot's execution (already solved by the framework)

Your wrapper only needs to:
- Define tools with good descriptions
- Validate inputs
- Call Lumibot methods
- Format responses

## Practical Applications

### Immediate Implementation Path

1. **Start with claudetools or claudette** for rapid prototyping
2. **Define 5-10 core tools** covering orders, positions, prices, and backtesting
3. **Add safety constraints** (max position size, paper trading only initially)
4. **Iterate on tool descriptions** based on Claude's behavior

### Example Tool Set for MVP

```python
LUMIBOT_TOOLS = [
    "get_portfolio_value",      # Read current portfolio
    "get_position",             # Check position in symbol
    "get_last_price",           # Get current price
    "create_market_order",      # Simple market buy/sell
    "create_limit_order",       # Limit order with price
    "cancel_order",             # Cancel pending order
    "run_backtest",             # Test strategy historically
    "get_account_summary"       # Cash, positions, P&L
]
```

### Production Evolution

1. **Add MCP Server layer** for standardized discovery
2. **Implement multi-agent pattern** with specialized analysts
3. **Add memory system** for learning from past trades
4. **Integrate with existing Alpaca MCP** for combined capabilities

## Risks & Limitations

1. **No Pre-Built Solution**: You must build the wrapper yourself. Lumibot has no official Claude integration.

2. **Real Money Risk**: AI-driven trading requires extensive testing. Always start with paper trading.

3. **Latency Considerations**: LLM round-trips add latency unsuitable for high-frequency strategies.

4. **Hallucination Risk**: Claude may attempt invalid operations. Robust validation is essential.

5. **Maintenance Burden**: Tool definitions must stay synchronized with Lumibot API changes.

## Recommendations

1. **Start with the Tool-Based pattern** using claudetools for type-safe definitions. This is the fastest path to a working prototype.

2. **Study the Alpaca MCP Server** as a reference implementation. It solves similar problems for a trading API.

3. **Use Pydantic models** for tool input validation. This catches errors before they reach Lumibot.

4. **Implement comprehensive logging** via Lumibot's `trace_stats()` method for AI decision audit trails.

5. **Build incrementally**: Start with read-only tools (get_price, get_position), then add order creation, then backtesting.

6. **Consider the Claude Agent SDK** for production deployments requiring managed execution environments.

## Bibliography

[1] Anthropic Engineering - "Introducing advanced tool use on the Claude Developer Platform" - https://www.anthropic.com/engineering/advanced-tool-use

[2] Claude Platform Documentation - "How to implement tool use" - https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use

[3] Anthropic News - "Introducing the Model Context Protocol" - https://www.anthropic.com/news/model-context-protocol

[4] Model Context Protocol - "Official MCP Servers Repository" - https://github.com/modelcontextprotocol/servers

[5] vatsalsaglani - "claudetools: Python library for Claude function calling" - https://github.com/vatsalsaglani/claudetools

[6] Answer.AI - "Claudette: High-level wrapper for Anthropic SDK" - https://claudette.answer.ai/

[7] Tauric Research - "TradingAgents: Multi-Agent LLM Financial Trading Framework" - https://github.com/TauricResearch/TradingAgents

[8] pipiku915 - "FinMem: Performance-Enhanced LLM Trading Agent with Layered Memory" - https://github.com/pipiku915/FinMem-LLM-StockTrading

[9] Lumiwealth - "Lumibot Official Documentation" - https://lumibot.lumiwealth.com/

[10] Lumiwealth - "Lumibot GitHub Repository" - https://github.com/Lumiwealth/lumibot

[11] Claude Platform Documentation - "Programmatic tool calling" - https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling

[12] Klavis.ai - "Less is More: 4 design patterns for building better MCP servers" - https://www.klavis.ai/blog/less-is-more-mcp-design-patterns-for-ai-agents

[13] Model Context Protocol - "Architecture overview" - https://modelcontextprotocol.io/docs/learn/architecture

[14] Anthropic Engineering - "Code Execution with MCP" - https://www.anthropic.com/engineering/code-execution-with-mcp

[15] Alpaca Markets - "How Traders Are Using AI Agents to Create Trading Bots" - https://alpaca.markets/learn/how-traders-are-using-ai-agents-to-create-trading-bots-with-alpaca

[16] QuantInsti - "LangChain Trading: Stock Analysis and LLM-Based Equity Analysis" - https://blog.quantinsti.com/langchain-trading-stock-analysis-llm-financial-python/

[17] Composio - "Claude 4.5: Function Calling and Tool Use" - https://composio.dev/blog/claude-function-calling-tools

[18] DataCamp - "Claude Agent SDK Tutorial" - https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk

## Methodology

Research conducted using multi-agent workflow:
- **Phase 1**: Query analysis and search planning (Opus orchestrator)
- **Phase 2**: Parallel source discovery (4 Haiku scouts, 16 search queries)
- **Phase 3**: Deep content extraction (4 Sonnet fetchers, 45+ sources)
- **Phase 4**: Critical review and synthesis (Opus)

Total sources evaluated: 108
Sources cited: 18
Extraction artifacts saved to: `.planning/research-extraction/`
