#!/usr/bin/env python3
"""
Alpaca Agent Service

Provides integration with the Alpaca trading tools via Claude Agent SDK.
This service handles natural language trading commands by creating a Claude
agent with Alpaca MCP server configuration.

Key Features:
- Uses Claude Agent SDK directly (no CLI subprocess needed)
- Alpaca MCP server for trading operations
- Streaming response support via SSE-formatted chunks
- Comprehensive error handling and logging

Reference: .claude/agents/alpaca-mcp.md
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any

from .logger import OrchestratorLogger
from .credential_service import get_decrypted_alpaca_credential
from .database import get_connection_with_rls

# Claude SDK imports
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ResultMessage,
)


# Alpaca Agent System Prompt
ALPACA_AGENT_SYSTEM_PROMPT = """You are an Alpaca trading account management specialist. You help users interact with their Alpaca trading account through natural language commands.

## Capabilities

You have access to Alpaca MCP tools that allow you to:

### Account & Portfolio Management
- Get account details, balances, buying power, PDT status
- View all current positions or specific position details
- Get portfolio history and P/L over time
- Close positions (individual or all)

### Market Data
- Get stock/crypto bars, quotes, trades, and snapshots
- Get latest prices and market data
- Check market calendar and clock status

### Options Trading
- Search and filter option contracts
- Get option quotes, snapshots, and chains
- Place single-leg and multi-leg option orders
- Exercise options positions

### Order Management
- Place stock orders (market, limit, stop, trailing stop)
- Place crypto orders
- View and manage existing orders
- Cancel orders

### Watchlists
- Create, view, update, and delete watchlists
- Add/remove symbols from watchlists

## Important Notes

- This is a PAPER TRADING account - no real money at risk
- Always confirm order details before executing trades
- For options, use proper OCC symbol format: SYMBOL + YYMMDD + C/P + Strike*1000
  - Example: SPY260221C00600000 = SPY Feb 21, 2026 $600 Call
- Display monetary values with proper formatting ($X,XXX.XX)
- When rolling positions, close the existing position first, then open the new one

## Response Format

Provide clear, well-formatted responses with:
- Status indicators (✅ Success, ❌ Failed)
- Tables for position/account data
- Relevant details and any warnings
"""


class AlpacaAgentService:
    """
    Service for invoking the Alpaca agent using Claude Agent SDK.

    The agent uses Claude SDK with Alpaca MCP server to provide
    access to Alpaca trading tools through natural language commands.

    Usage:
        service = AlpacaAgentService(logger, working_dir="/path/to/project")

        # Invoke agent with streaming
        async for chunk in service.invoke_agent_streaming("Check my account balance"):
            print(chunk, end='')
    """

    def __init__(self, logger: OrchestratorLogger, working_dir: str):
        """
        Initialize the Alpaca Agent Service.

        Args:
            logger: Logger instance for logging events and errors
            working_dir: Working directory containing configuration files
        """
        self.logger = logger
        self.working_dir = Path(working_dir)
        self.mcp_config_path = self.working_dir / ".mcp.json.alpaca"

        # For backwards compatibility with existing endpoint checks
        self.claude_path = "sdk"  # Indicate SDK is available (not CLI)

        self.logger.info(f"AlpacaAgentService initialized with working_dir={working_dir}")
        self.logger.success("Using Claude Agent SDK (no CLI required)")

    def verify_mcp_config(self) -> bool:
        """
        Verify that the Alpaca MCP configuration is available.

        Config can come from either:
        1. .mcp.json.alpaca file in working_dir (local development)
        2. Environment variables ALPACA_API_KEY and ALPACA_SECRET_KEY (production)

        Returns:
            True if config is available from either source, False otherwise
        """
        # Check for config file first
        if self.mcp_config_path.exists():
            self.logger.success(f"Alpaca MCP config found at {self.mcp_config_path}")
            return True

        # Fall back to environment variables
        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")

        if api_key and secret_key:
            self.logger.success("Alpaca credentials found in environment variables")
            return True

        self.logger.error(
            f"Alpaca MCP config not found. Either create {self.mcp_config_path} "
            "or set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
        )
        return False

    def _load_mcp_config(self) -> Optional[Dict[str, Any]]:
        """
        Load the Alpaca MCP configuration from file or create from environment variables.

        The config file (.mcp.json.alpaca) is gitignored since it contains credentials.
        In production (Railway), we create the config dynamically from environment variables.

        Returns:
            Dict containing MCP configuration, or None if load fails
        """
        # First, try to load from file (local development)
        if self.mcp_config_path.exists():
            try:
                with open(self.mcp_config_path, 'r') as f:
                    config = json.load(f)
                self.logger.info(f"Loaded MCP config from {self.mcp_config_path}")
                return config
            except Exception as e:
                self.logger.warning(f"Failed to load MCP config from file: {e}")

        # Fall back to creating config from environment variables (production)
        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        paper_trade = os.environ.get("ALPACA_PAPER", "true")

        if not api_key or not secret_key:
            self.logger.error("Alpaca credentials not found in file or environment variables")
            return None

        self.logger.info("Creating MCP config from environment variables")
        return {
            "mcpServers": {
                "alpaca": {
                    "command": "uvx",
                    "args": ["alpaca-mcp-server", "serve"],
                    "env": {
                        "ALPACA_API_KEY": api_key,
                        "ALPACA_SECRET_KEY": secret_key,
                        "ALPACA_PAPER_TRADE": paper_trade
                    }
                }
            }
        }

    def _create_agent_options(self) -> ClaudeAgentOptions:
        """
        Create Claude Agent SDK options for Alpaca agent.

        Returns:
            ClaudeAgentOptions configured for Alpaca trading
        """
        # Load MCP config
        mcp_config = self._load_mcp_config()

        # Build environment variables - pass through Alpaca keys
        env_vars = {}
        if "ANTHROPIC_API_KEY" in os.environ:
            env_vars["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]

        # Get Alpaca credentials from environment or MCP config
        alpaca_config = mcp_config.get("mcpServers", {}).get("alpaca", {}).get("env", {}) if mcp_config else {}

        # Prioritize environment variables over config file
        env_vars["ALPACA_API_KEY"] = os.environ.get("ALPACA_API_KEY", alpaca_config.get("ALPACA_API_KEY", ""))
        env_vars["ALPACA_SECRET_KEY"] = os.environ.get("ALPACA_SECRET_KEY", alpaca_config.get("ALPACA_SECRET_KEY", ""))
        env_vars["ALPACA_PAPER_TRADE"] = os.environ.get("ALPACA_PAPER", alpaca_config.get("ALPACA_PAPER_TRADE", "true"))

        # Build options dict
        options_dict = {
            "system_prompt": ALPACA_AGENT_SYSTEM_PROMPT,
            "model": "sonnet",
            "cwd": str(self.working_dir),
            "env": env_vars,
        }

        # Configure MCP server - use stdio transport for external MCP server
        # The SDK expects mcp_servers dict with server configs
        if mcp_config and "mcpServers" in mcp_config:
            alpaca_server_config = mcp_config["mcpServers"].get("alpaca", {})
            if alpaca_server_config:
                # Format for Claude SDK external MCP server (stdio transport)
                options_dict["mcp_servers"] = {
                    "alpaca": {
                        "type": "stdio",
                        "command": alpaca_server_config.get("command", "uvx"),
                        "args": alpaca_server_config.get("args", ["alpaca-mcp-server", "serve"]),
                        "env": alpaca_server_config.get("env", {})
                    }
                }

        # Add allowed tools for Alpaca operations
        options_dict["allowed_tools"] = [
            # All Alpaca MCP tools
            "mcp__alpaca__get_account_info",
            "mcp__alpaca__get_all_positions",
            "mcp__alpaca__get_open_position",
            "mcp__alpaca__get_portfolio_history",
            "mcp__alpaca__close_position",
            "mcp__alpaca__close_all_positions",
            "mcp__alpaca__get_asset",
            "mcp__alpaca__get_all_assets",
            "mcp__alpaca__get_calendar",
            "mcp__alpaca__get_clock",
            "mcp__alpaca__get_corporate_actions",
            "mcp__alpaca__get_stock_bars",
            "mcp__alpaca__get_stock_quotes",
            "mcp__alpaca__get_stock_trades",
            "mcp__alpaca__get_stock_latest_bar",
            "mcp__alpaca__get_stock_latest_quote",
            "mcp__alpaca__get_stock_latest_trade",
            "mcp__alpaca__get_stock_snapshot",
            "mcp__alpaca__get_crypto_bars",
            "mcp__alpaca__get_crypto_quotes",
            "mcp__alpaca__get_crypto_trades",
            "mcp__alpaca__get_crypto_latest_bar",
            "mcp__alpaca__get_crypto_latest_quote",
            "mcp__alpaca__get_crypto_latest_trade",
            "mcp__alpaca__get_crypto_snapshot",
            "mcp__alpaca__get_crypto_latest_orderbook",
            "mcp__alpaca__get_option_contracts",
            "mcp__alpaca__get_option_latest_quote",
            "mcp__alpaca__get_option_snapshot",
            "mcp__alpaca__get_option_chain",
            "mcp__alpaca__place_option_market_order",
            "mcp__alpaca__exercise_options_position",
            "mcp__alpaca__place_stock_order",
            "mcp__alpaca__place_crypto_order",
            "mcp__alpaca__get_orders",
            "mcp__alpaca__cancel_order_by_id",
            "mcp__alpaca__cancel_all_orders",
            "mcp__alpaca__get_watchlists",
            "mcp__alpaca__get_watchlist_by_id",
            "mcp__alpaca__create_watchlist",
            "mcp__alpaca__update_watchlist_by_id",
            "mcp__alpaca__add_asset_to_watchlist_by_id",
            "mcp__alpaca__remove_asset_from_watchlist_by_id",
            "mcp__alpaca__delete_watchlist_by_id",
        ]

        return ClaudeAgentOptions(**options_dict)

    async def invoke_agent(self, message: str) -> str:
        """
        Invoke the Alpaca agent with a message and return the full response.

        Args:
            message: Natural language message/command for the Alpaca agent

        Returns:
            Full response text from the agent

        Raises:
            RuntimeError: If configuration doesn't exist
            Exception: If execution fails
        """
        if not self.verify_mcp_config():
            error_msg = f"Cannot invoke agent: MCP config not found at {self.mcp_config_path}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.info(f"Invoking Alpaca agent with message: {message[:100]}...")

        try:
            options = self._create_agent_options()
            response_text = ""

            async with ClaudeSDKClient(options=options) as client:
                await client.query(message)

                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text

            self.logger.success(f"Alpaca agent invocation completed, response_length={len(response_text)}")
            return response_text

        except Exception as e:
            self.logger.error(f"Failed to invoke Alpaca agent: {e}", exc_info=True)
            raise

    async def invoke_agent_streaming(self, message: str) -> AsyncGenerator[str, None]:
        """
        Invoke the Alpaca agent with streaming SSE-formatted responses.

        This method yields Server-Sent Events (SSE) formatted chunks as they arrive
        from the Claude Agent SDK. Each chunk is formatted as:
            data: {"type": "text", "content": "..."}\n\n

        The final chunk is:
            data: [DONE]\n\n

        Args:
            message: Natural language message/command for the Alpaca agent

        Yields:
            SSE-formatted string chunks

        Raises:
            RuntimeError: If MCP config doesn't exist
            Exception: If execution fails
        """
        if not self.verify_mcp_config():
            error_msg = f"Cannot invoke agent: MCP config not found at {self.mcp_config_path}"
            self.logger.error(error_msg)

            error_chunk = {"type": "error", "content": error_msg}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            return

        self.logger.info(f"[ALPACA AGENT SERVICE] Invoking agent (streaming) with message: {message[:100]}...")

        client = None

        try:
            options = self._create_agent_options()
            self.logger.info(f"[ALPACA AGENT SERVICE] Working directory: {self.working_dir}")

            client = ClaudeSDKClient(options=options)
            await client.__aenter__()

            self.logger.info("[ALPACA AGENT SERVICE] Claude SDK client started")

            # Send user's prompt
            await client.query(message)

            # Stream responses
            chunk_count = 0

            async for msg in client.receive_response():
                # Handle SystemMessage (informational)
                if isinstance(msg, SystemMessage):
                    subtype = getattr(msg, "subtype", "unknown")
                    self.logger.debug(f"[ALPACA AGENT SERVICE] SystemMessage: {subtype}")
                    continue

                # Process AssistantMessage blocks
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        # Stream text responses
                        if isinstance(block, TextBlock):
                            chunk_count += 1
                            chunk_data = {
                                "type": "text",
                                "content": block.text
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug(f"Streamed text chunk {chunk_count}")

                        # Stream thinking blocks
                        elif isinstance(block, ThinkingBlock):
                            chunk_data = {
                                "type": "thinking",
                                "content": block.thinking
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug("Streamed thinking block")

                        # Stream tool use blocks
                        elif isinstance(block, ToolUseBlock):
                            chunk_data = {
                                "type": "tool_use",
                                "tool_name": block.name,
                                "tool_input": block.input
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug(f"Streamed tool use: {block.name}")

                # Handle result message
                elif isinstance(msg, ResultMessage):
                    self.logger.info(
                        f"[ALPACA AGENT SERVICE] Completed: "
                        f"turns={getattr(msg, 'num_turns', 'N/A')}, "
                        f"cost=${getattr(msg, 'total_cost_usd', 0.0):.4f}"
                    )

            self.logger.success(f"[ALPACA AGENT SERVICE] Streaming completed, chunks={chunk_count}")
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            self.logger.warning("Alpaca agent streaming cancelled by client")
            cancel_chunk = {"type": "error", "content": "Stream cancelled"}
            yield f"data: {json.dumps(cancel_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            self.logger.error(f"Failed to stream Alpaca agent response: {e}", exc_info=True)
            error_chunk = {"type": "error", "content": f"Streaming error: {str(e)}"}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        finally:
            # Clean up client
            if client:
                try:
                    await client.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.warning(f"Error closing client: {e}")

    async def invoke_agent_streaming_with_credential(
        self,
        message: str,
        api_key: str,
        secret_key: str,
        paper_trade: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Invoke the Alpaca agent with streaming using provided credentials.

        This method is used when credentials come from encrypted storage
        rather than environment variables. Credentials should only exist
        in the calling scope and are passed directly here.

        Args:
            message: Natural language message/command for the agent
            api_key: Decrypted Alpaca API key
            secret_key: Decrypted Alpaca secret key
            paper_trade: Whether to use paper trading (default True)

        Yields:
            SSE-formatted string chunks
        """
        self.logger.info(f"[ALPACA AGENT SERVICE] Invoking agent (streaming) with provided credentials: {message[:100]}...")

        client = None

        try:
            # Build options with provided credentials (NOT from environment)
            env_vars = {}
            if "ANTHROPIC_API_KEY" in os.environ:
                env_vars["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]

            # Use provided credentials
            env_vars["ALPACA_API_KEY"] = api_key
            env_vars["ALPACA_SECRET_KEY"] = secret_key
            env_vars["ALPACA_PAPER_TRADE"] = "true" if paper_trade else "false"

            options_dict = {
                "system_prompt": ALPACA_AGENT_SYSTEM_PROMPT,
                "model": "sonnet",
                "cwd": str(self.working_dir),
                "env": env_vars,
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
            }

            # Add allowed tools (same as existing method)
            options_dict["allowed_tools"] = [
                "mcp__alpaca__get_account_info",
                "mcp__alpaca__get_all_positions",
                "mcp__alpaca__get_open_position",
                "mcp__alpaca__get_portfolio_history",
                "mcp__alpaca__close_position",
                "mcp__alpaca__close_all_positions",
                "mcp__alpaca__get_asset",
                "mcp__alpaca__get_all_assets",
                "mcp__alpaca__get_calendar",
                "mcp__alpaca__get_clock",
                "mcp__alpaca__get_corporate_actions",
                "mcp__alpaca__get_stock_bars",
                "mcp__alpaca__get_stock_quotes",
                "mcp__alpaca__get_stock_trades",
                "mcp__alpaca__get_stock_latest_bar",
                "mcp__alpaca__get_stock_latest_quote",
                "mcp__alpaca__get_stock_latest_trade",
                "mcp__alpaca__get_stock_snapshot",
                "mcp__alpaca__get_crypto_bars",
                "mcp__alpaca__get_crypto_quotes",
                "mcp__alpaca__get_crypto_trades",
                "mcp__alpaca__get_crypto_latest_bar",
                "mcp__alpaca__get_crypto_latest_quote",
                "mcp__alpaca__get_crypto_latest_trade",
                "mcp__alpaca__get_crypto_snapshot",
                "mcp__alpaca__get_crypto_latest_orderbook",
                "mcp__alpaca__get_option_contracts",
                "mcp__alpaca__get_option_latest_quote",
                "mcp__alpaca__get_option_snapshot",
                "mcp__alpaca__get_option_chain",
                "mcp__alpaca__place_option_market_order",
                "mcp__alpaca__exercise_options_position",
                "mcp__alpaca__place_stock_order",
                "mcp__alpaca__place_crypto_order",
                "mcp__alpaca__get_orders",
                "mcp__alpaca__cancel_order_by_id",
                "mcp__alpaca__cancel_all_orders",
                "mcp__alpaca__get_watchlists",
                "mcp__alpaca__get_watchlist_by_id",
                "mcp__alpaca__create_watchlist",
                "mcp__alpaca__update_watchlist_by_id",
                "mcp__alpaca__add_asset_to_watchlist_by_id",
                "mcp__alpaca__remove_asset_from_watchlist_by_id",
                "mcp__alpaca__delete_watchlist_by_id",
            ]

            options = ClaudeAgentOptions(**options_dict)
            self.logger.info(f"[ALPACA AGENT SERVICE] Working directory: {self.working_dir}")

            client = ClaudeSDKClient(options=options)
            await client.__aenter__()

            self.logger.info("[ALPACA AGENT SERVICE] Claude SDK client started with provided credentials")

            # Send user's prompt
            await client.query(message)

            # Stream responses (same logic as invoke_agent_streaming)
            chunk_count = 0

            async for msg in client.receive_response():
                if isinstance(msg, SystemMessage):
                    subtype = getattr(msg, "subtype", "unknown")
                    self.logger.debug(f"[ALPACA AGENT SERVICE] SystemMessage: {subtype}")
                    continue

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            chunk_count += 1
                            chunk_data = {
                                "type": "text",
                                "content": block.text
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug(f"Streamed text chunk {chunk_count}")

                        elif isinstance(block, ThinkingBlock):
                            chunk_data = {
                                "type": "thinking",
                                "content": block.thinking
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug("Streamed thinking block")

                        elif isinstance(block, ToolUseBlock):
                            chunk_data = {
                                "type": "tool_use",
                                "tool_name": block.name,
                                "tool_input": block.input
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            self.logger.debug(f"Streamed tool use: {block.name}")

                elif isinstance(msg, ResultMessage):
                    self.logger.info(
                        f"[ALPACA AGENT SERVICE] Completed: "
                        f"turns={getattr(msg, 'num_turns', 'N/A')}, "
                        f"cost=${getattr(msg, 'total_cost_usd', 0.0):.4f}"
                    )

            self.logger.success(f"[ALPACA AGENT SERVICE] Streaming completed with provided credentials, chunks={chunk_count}")
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            self.logger.warning("Alpaca agent streaming cancelled by client")
            cancel_chunk = {"type": "error", "content": "Stream cancelled"}
            yield f"data: {json.dumps(cancel_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            self.logger.error(f"Failed to stream Alpaca agent response: {e}", exc_info=True)
            error_chunk = {"type": "error", "content": f"Streaming error: {str(e)}"}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        finally:
            if client:
                try:
                    await client.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.warning(f"Error closing client: {e}")

    async def invoke_with_stored_credential(
        self,
        credential_id: str,
        user_id: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Alpaca agent operation using stored encrypted credentials.

        Uses decrypt-on-demand pattern: credentials are decrypted only during
        the operation and plaintext is discarded when context exits.

        Args:
            credential_id: UUID of stored credential in user_credentials table
            user_id: User ID to validate ownership (RLS context)
            operation: Operation name (e.g., "get_account", "get_positions")
            params: Optional parameters for the operation

        Returns:
            Dict containing operation result

        Raises:
            ValueError: If credential not found, unauthorized, or inactive
            RuntimeError: If operation fails

        Example:
            >>> service = AlpacaAgentService(logger, working_dir="/tmp")
            >>> result = await service.invoke_with_stored_credential(
            ...     credential_id="550e8400-e29b-41d4-a716-446655440000",
            ...     user_id="user123",
            ...     operation="get_account",
            ...     params={}
            ... )
            >>> print(result["cash"])

        Security:
            - Credentials decrypted only within context manager scope
            - Plaintext never stored as instance attribute
            - RLS enforces credential ownership validation
            - Plaintext automatically discarded on context exit
        """
        params = params or {}

        self.logger.info(
            f"Invoking Alpaca operation with stored credential: "
            f"operation={operation}, credential_id={credential_id}"
        )

        try:
            # Get RLS-aware database connection
            async with get_connection_with_rls(user_id) as conn:
                # Decrypt credential on-demand (plaintext exists only in this context)
                async with get_decrypted_alpaca_credential(
                    conn, credential_id, user_id
                ) as (api_key, secret_key):
                    # Create MCP config with decrypted credentials
                    # Note: Credentials exist only in this block's scope
                    mcp_config = {
                        "mcpServers": {
                            "alpaca": {
                                "command": "uvx",
                                "args": ["alpaca-mcp-server", "serve"],
                                "env": {
                                    "ALPACA_API_KEY": api_key,
                                    "ALPACA_SECRET_KEY": secret_key,
                                    "ALPACA_PAPER_TRADE": "true",  # Default to paper
                                },
                            }
                        }
                    }

                    # Build agent options with temporary credentials
                    options_dict = {
                        "system_prompt": ALPACA_AGENT_SYSTEM_PROMPT,
                        "model": "sonnet",
                        "cwd": str(self.working_dir),
                        "env": {
                            "ALPACA_API_KEY": api_key,
                            "ALPACA_SECRET_KEY": secret_key,
                            "ALPACA_PAPER_TRADE": "true",
                        },
                        "mcp_servers": {
                            "alpaca": {
                                "type": "stdio",
                                "command": "uvx",
                                "args": ["alpaca-mcp-server", "serve"],
                                "env": {
                                    "ALPACA_API_KEY": api_key,
                                    "ALPACA_SECRET_KEY": secret_key,
                                    "ALPACA_PAPER_TRADE": "true",
                                },
                            }
                        },
                    }

                    # Create Claude Agent SDK client
                    options = ClaudeAgentOptions(**options_dict)

                    # Execute operation via agent
                    async with ClaudeSDKClient(options=options) as client:
                        # Build natural language prompt for operation
                        prompt = f"Execute {operation}"
                        if params:
                            prompt += f" with params: {params}"

                        await client.query(prompt)

                        # Collect response
                        response_text = ""
                        async for msg in client.receive_response():
                            if isinstance(msg, AssistantMessage):
                                for block in msg.content:
                                    if isinstance(block, TextBlock):
                                        response_text += block.text

                        self.logger.success(
                            f"Operation {operation} completed successfully"
                        )

                        return {"result": response_text, "operation": operation}

                # Credentials automatically discarded here when context exits

        except ValueError as e:
            # Credential validation errors (not found, unauthorized, inactive)
            self.logger.error(f"Credential validation failed: {e}")
            raise

        except Exception as e:
            # Other errors (network, API, etc.)
            self.logger.error(
                f"Failed to invoke operation {operation}: {e}", exc_info=True
            )
            raise RuntimeError(f"Operation {operation} failed: {e}") from e
