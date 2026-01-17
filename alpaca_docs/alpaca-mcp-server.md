# Alpaca's MCP Server

Alpaca's MCP Server allows traders to research markets, analyze data, and place orders using natural language across AI chat applications, coding tools, and Command Line Interfaces.

**Alpaca's MCP Server GitHub URL:** https://github.com/alpacahq/alpaca-mcp-server

**For more information, visit:** [Alpaca's MCP Server Homepage](https://alpaca.markets/mcp-server)

_All data and instructions are current as of November 20, 2025._

## MCP Server Overview

An MCP server is a component of the [Model Context Protocol](https://docs.anthropic.com/en/docs/agents-and-tools/mcp) (MCP) architecture developed by Anthropic. MCP is an open standard that provides a consistent way for AI applications, code editors, or Command Line Interface to interact with external tools, data sources, and services through a structured protocol.

As AI interfaces improve, connecting them to trading workflows often requires multiple APIs, custom integrations, and authentication steps. MCP architecture streamlines this by providing a standard method for accessing data and performing actions.

An MCP server itself acts as a bridge between the MCP client (AI interfaces) and the capabilities. It presents these capabilities in a predictable and secure format so an AI model can request market data, retrieve information, or carry out defined operations without additional SDKs or complex setup.

## Alpaca's MCP Server Overview

Alpaca's MCP Server brings this same bridge-like concept to trading by exposing capabilities powered by Alpaca's Trading API, including:

- Market data, both historical and live
- Order actions such as entry, change, and cancel
- Portfolio details like positions, buying power, and unrealized P/L
- Optional automation like alerts or risk checks

This helps users accelerate their research, streamline decision making, and support efficient trade execution, helping users capitalize on potential market opportunities more efficiently. For more information about the available functions, please see the Available Endpoints section below.

## Main Benefits

### Reinforced Decisions, Transparent Execution

Alpaca's MCP Server gives your AI model structured access to real time market data, news context, portfolio details, and order actions powered by Alpaca's Trading API. Instead of acting on its own, the AI assistants help surface relevant insights, organize information, and prepare the actions you ask for.

### One Interface for Many Markets

Alpaca's MCP Server brings equities, ETFs, crypto, and multi-leg options into one workflow and interface. This allows an AI agent to research, analyze, and help execute trading ideas without switching between platforms or juggling APIs.

### Code-Optional, Extensible by Design

Alpaca's MCP Server lets traders begin with natural language prompts and move into vibe coding or full code whenever they want to optimize strategies.

## Supported MCP Clients and Connection Types

Alpaca's MCP Server can be configured on the following MCP clients. Each client has its own setup requirements. For more details, visit [Alpaca's MCP Server GitHub](https://github.com/alpacahq/alpaca-mcp-server). The connection type indicates how you can set up Alpaca's MCP Server.

**Note:** Remote hosting for Alpaca's MCP Server is not yet available. Traders who wish to use it remotely will need to self host for now. We may consider additional options for remote MCP Server use over time, depending on feasibility and demand.

For instructions on self hosting Alpaca's remote MCP Server, visit our learn article "[How to Deploy Alpaca's MCP Server Remotely on Claude Mobile App](https://alpaca.markets/learn/how-to-deploy-alpaca-mcp-server-remotely-on-claude-mobile-app)".

| MCP client name | Connection type |
| --- | --- |
| Cloud Desktop | Local or Remote |
| Claude Web | Remote only |
| Claude Mobile App | Remote only |
| ChatGPT Web | Remote only |
| ChatGPT Desktop | Remote only |
| ChatGPT Mobile App | Remote only |
| VS Code | Local or Remote |
| Cursor | Local or Remote |
| PyCharm | Local or Remote |
| Claude Code (CLI) | Local or Remote |
| Gemini CLI | Local or Remote |

## Prerequisites for Connections

You will need the following prerequisites to configure and run Alpaca's MCP Server. The requirements may vary depending on which MCP client you connect it with remotely or locally.

- Terminal (macOS/Linux) | Command Prompt or PowerShell (Windows)
- Python 3.10+ (Check the [official installation guide](https://www.python.org/downloads/) and confirm the version by typing the following command: `python3 --version` in Terminal)
- uv (Install using the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/)) for local setup
  - Tip: uv can be installed either through a package manager (like Homebrew) or directly using `curl | sh`.
- Alpaca Trading API keys (free paper trading account available)
  - To find your Alpaca API keys, please check our "[How to Get Alpaca's Trading API Key and Start Connect](https://alpaca.markets/learn/connect-to-alpaca-api)" or "[How to Start Paper Trading with Alpaca](https://alpaca.markets/learn/start-paper-trading)"
- MCP client (Claude Desktop, Cursor, VS Code, etc.)
  - Some MCP clients may require a paid subscription if you use the MCP server frequently

## Available Endpoints

Alpaca's MCP Server offers 43 functions (endpoints) of Trading API. We are optimizing and expanding the capabilities of our MCP server.

| Category | Function name | Description |
| --- | --- | --- |
| Account | get_account_info | Retrieves current account information including balances, buying power, and account status. |
| Positions | get_all_positions | Retrieves all current positions in the portfolio with details like quantity, market value, and P&L. |
| Positions | get_open_position | Retrieves detailed information for a specific open position. |
| Portfolio History | get_portfolio_history | Retrieves account portfolio history with equity and P&L over a requested time window. |
| Assets | get_asset | Retrieves detailed information about a specific asset including trading status and attributes. |
| Assets | get_all_assets | Retrieves all available assets with optional filtering by status, class, and exchange. |
| Watchlist | create_watchlist | Creates a new watchlist with specified symbols for tracking assets. |
| Watchlist | get_watchlists | Retrieves all watchlists for the account with their symbols. |
| Watchlist | update_watchlist_by_id | Updates an existing watchlist by modifying names or symbols. |
| Watchlist | get_watchlist_by_id | Get a specific watchlist by its ID. |
| Watchlist | add_asset_to_watchlist_by_id | Add an asset by symbol to a specific watchlist by ID. |
| Watchlist | remove_asset_from_watchlist_by_id | Remove an asset by symbol from a specific watchlist by ID. |
| Watchlist | delete_watchlist_by_id | Delete a specific watchlist by its ID. |
| Corporate Actions | get_corporate_actions | Retrieves corporate action announcements like earnings, dividends, and stock splits. |
| Calendar | get_calendar | Retrieves market calendar for specified date range showing trading days and holidays. |
| Clock | get_market_clock | Retrieves current market status and next open or close times. |
| Market Data (Stock) | get_stock_bars | Retrieves historical stock price bars with OHLCV data using flexible timeframes. |
| Market Data (Stock) | get_stock_quote | Retrieves the historical quote for a stock including bid or ask prices and volumes. |
| Market Data (Stock) | get_stock_trades | Retrieves historical trade data for a stock with individual trade details. |
| Market Data (Stock) | get_stock_latest_bar | Retrieves the most recent minute bar for a stock. |
| Market Data (Stock) | get_stock_latest_quote | Retrieves the latest quote for a stock including bid or ask prices and volumes. |
| Market Data (Stock) | get_stock_latest_trade | Retrieves the latest trade information for a stock. |
| Market Data (Stock) | get_stock_snapshot | Retrieves comprehensive snapshot with latest quote, trade, minute bar, daily bar, and previous daily bar. |
| Market Data (Crypto) | get_crypto_bars | Retrieves historical cryptocurrency price bars with OHLCV data. |
| Market Data (Crypto) | get_crypto_quotes | Retrieves historical cryptocurrency quote data with bid or ask information. |
| Market Data (Crypto) | get_crypto_trades | Retrieves historical trade prints for one or more cryptocurrencies. |
| Market Data (Crypto) | get_crypto_latest_quote | Returns the latest quote for one or more crypto symbols. |
| Market Data (Crypto) | get_crypto_latest_bar | Returns the latest minute bar for one or more crypto symbols. |
| Market Data (Crypto) | get_crypto_latest_trade | Returns the latest trade for one or more crypto symbols. |
| Market Data (Crypto) | get_crypto_snapshot | Returns snapshots including latest trade, quote, minute bar, daily and previous daily bars for crypto symbols. |
| Market Data (Crypto) | get_crypto_latest_orderbook | Returns the latest orderbook for one or more crypto symbols. |
| Market Data (Options) | get_option_contracts | Searches for option contracts with flexible filtering by expiration, strike price, and type. |
| Market Data (Options) | get_option_latest_quote | Retrieves the latest quote for an option contract with bid or ask prices and Greeks. |
| Market Data (Options) | get_option_snapshot | Retrieves comprehensive snapshots of option contracts including latest trade, quote, implied volatility, and Greeks. |
| Trading (Orders) | get_orders | Retrieves order history with filtering options by status, date range, and limits. |
| Trading (Orders) | place_stock_order | Places a stock order with support for market, limit, stop, stop limit, and trailing stop orders. |
| Trading (Orders) | place_crypto_order | Places a cryptocurrency order with support for market, limit, and stop limit orders. |
| Trading (Orders) | place_option_market_order | Places option orders including single leg and multi leg strategies like spreads and straddles. |
| Trading (Orders) | cancel_all_orders | Cancels all open orders and returns the status of each cancellation. |
| Trading (Orders) | cancel_order_by_id | Cancels a specific order by its ID. |
| Trading (Positions) | close_position | Closes a specific position for a single symbol, either partially or completely. |
| Trading (Positions) | close_all_positions | Closes all open positions in the portfolio. |
| Trading (Positions) | exercise_options_position | Exercises a held option contract, converting it into the underlying asset. |

## Important Considerations When Trading with Alpaca's MCP Server

Using Alpaca's MCP Server introduces a few important considerations:

1. Make sure your Alpaca API keys are linked to the correct account type such as live or paper.
2. Some AI tools (MCP clients) may require a paid subscription if you use the MCP Server frequently.
3. Review and confirm orders directly on your Alpaca dashboard. You can do this in real time to ensure accuracy before or after submitting trades.

## Security Considerations for Remote MCP Server Deployment

Running an MCP server remotely introduces a few important security considerations. Many early stage examples such as FastMCP are designed for local testing and may not include authentication or encrypted communication by default.

When a server is publicly accessible, it is possible for external requests to reach it. If the server handles sensitive information such as Alpaca Trading API keys, this can create a risk of unauthorized access or unintended tool execution.

To reduce these risks, a secure deployment should include HTTPS or TLS for encrypted communication and a reliable token based authentication method. Taking these steps helps protect your credentials and ensures that only trusted clients can interact with your MCP server.

## Disclosure

_Insights generated by our MCP server and connected AI agents are for educational and informational purposes only and should not be taken as investment advice. Past performance from models does not guarantee future results. Please conduct your own due diligence before making any decisions._
