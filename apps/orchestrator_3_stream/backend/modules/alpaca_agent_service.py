#!/usr/bin/env python3
"""
Alpaca Agent Service

Provides integration with the Alpaca MCP agent via Claude Code subprocess invocation.
This service handles natural language trading commands by spawning a Claude Code
subprocess with the Alpaca MCP configuration enabled.

Key Features:
- Subprocess invocation of Claude Code with Alpaca MCP tools
- Streaming response support via SSE-formatted chunks
- MCP configuration validation
- Comprehensive error handling and logging

Reference: .claude/agents/alpaca-mcp.md
"""

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Optional

from .logger import OrchestratorLogger


def find_claude_executable() -> str:
    """
    Find the claude executable in the system PATH.

    Searches common locations and returns the full path if found.

    Returns:
        Full path to claude executable

    Raises:
        FileNotFoundError: If claude command is not found in PATH
    """
    # First try to find claude in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        return claude_path

    # Try common installation locations
    common_paths = [
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/usr/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ]

    for path in common_paths:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "Claude CLI not found. Please install with: npm install -g @anthropic-ai/claude-cli"
    )


class AlpacaAgentService:
    """
    Service for invoking the Alpaca MCP agent via Claude Code subprocess.

    The agent uses Claude Code with the .mcp.json.alpaca configuration to provide
    access to Alpaca trading tools through natural language commands.

    Usage:
        service = AlpacaAgentService(logger, working_dir="/path/to/project")

        # Verify MCP config exists
        if not service.verify_mcp_config():
            raise RuntimeError("Alpaca MCP config not found")

        # Invoke agent with streaming
        async for chunk in service.invoke_agent_streaming("Check my account balance"):
            print(chunk, end='')
    """

    def __init__(self, logger: OrchestratorLogger, working_dir: str):
        """
        Initialize the Alpaca Agent Service.

        Args:
            logger: Logger instance for logging events and errors
            working_dir: Working directory containing .mcp.json.alpaca file
        """
        self.logger = logger
        self.working_dir = Path(working_dir)
        self.mcp_config_path = self.working_dir / ".mcp.json.alpaca"
        self.claude_path = None

        self.logger.info(f"AlpacaAgentService initialized with working_dir={working_dir}")

        # Find claude executable on initialization
        try:
            self.claude_path = find_claude_executable()
            self.logger.success(f"Claude CLI found at: {self.claude_path}")
        except FileNotFoundError as e:
            self.logger.error(f"Claude CLI not found: {e}")
            self.claude_path = None

    def verify_mcp_config(self) -> bool:
        """
        Verify that the Alpaca MCP configuration file exists.

        Returns:
            True if .mcp.json.alpaca exists in working_dir, False otherwise
        """
        exists = self.mcp_config_path.exists()

        if exists:
            self.logger.success(f"Alpaca MCP config found at {self.mcp_config_path}")
        else:
            self.logger.error(f"Alpaca MCP config not found at {self.mcp_config_path}")

        return exists

    async def invoke_agent(self, message: str) -> str:
        """
        Invoke the Alpaca agent with a message and return the full response.

        This method runs the Claude Code subprocess and collects all output
        into a single string response. For streaming use invoke_agent_streaming().

        Args:
            message: Natural language message/command for the Alpaca agent

        Returns:
            Full response text from the agent

        Raises:
            RuntimeError: If MCP config doesn't exist
            Exception: If subprocess execution fails
        """
        if not self.verify_mcp_config():
            error_msg = f"Cannot invoke agent: MCP config not found at {self.mcp_config_path}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        if not self.claude_path:
            error_msg = "Claude CLI not available. Please install with: npm install -g @anthropic-ai/claude-cli"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.info(f"Invoking Alpaca agent with message: {message[:100]}...")

        try:
            # Build the command using full path to claude
            cmd = [
                self.claude_path,
                "--mcp-config", ".mcp.json.alpaca",
                "--model", "sonnet",
                "--dangerously-skip-permissions",
                "-p", message
            ]

            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir)
            )

            # Wait for completion and capture output
            stdout, stderr = await process.communicate()

            # Check return code
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='replace')
                error_msg = f"Alpaca agent subprocess failed with code {process.returncode}: {stderr_text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            # Decode and return response
            response = stdout.decode('utf-8', errors='replace')
            self.logger.success(f"Alpaca agent invocation completed, response_length={len(response)}")

            return response

        except Exception as e:
            self.logger.error(f"Failed to invoke Alpaca agent: {e}", exc_info=True)
            raise

    async def invoke_agent_streaming(self, message: str) -> AsyncGenerator[str, None]:
        """
        Invoke the Alpaca agent with streaming SSE-formatted responses.

        This method yields Server-Sent Events (SSE) formatted chunks as they arrive
        from the Claude Code subprocess. Each chunk is formatted as:
            data: {"type": "text", "content": "..."}\n\n

        The final chunk is:
            data: [DONE]\n\n

        Args:
            message: Natural language message/command for the Alpaca agent

        Yields:
            SSE-formatted string chunks

        Raises:
            RuntimeError: If MCP config doesn't exist
            Exception: If subprocess execution fails

        Example:
            async for chunk in service.invoke_agent_streaming("Check positions"):
                # chunk = 'data: {"type": "text", "content": "Current positions:"}\n\n'
                await websocket.send(chunk)
        """
        if not self.verify_mcp_config():
            error_msg = f"Cannot invoke agent: MCP config not found at {self.mcp_config_path}"
            self.logger.error(error_msg)

            # Yield error chunk in SSE format
            error_chunk = {
                "type": "error",
                "content": error_msg
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            return

        if not self.claude_path:
            error_msg = "Claude CLI not available. Please install with: npm install -g @anthropic-ai/claude-cli"
            self.logger.error(error_msg)

            # Yield error chunk in SSE format
            error_chunk = {
                "type": "error",
                "content": error_msg
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            return

        self.logger.info(f"[ALPACA AGENT SERVICE] Invoking agent (streaming) with message: {message[:100]}...")

        process = None

        try:
            # Build the command using full path to claude
            cmd = [
                self.claude_path,
                "--mcp-config", ".mcp.json.alpaca",
                "--model", "sonnet",
                "--dangerously-skip-permissions",
                "-p", message
            ]

            self.logger.info(f"[ALPACA AGENT SERVICE] Command: {' '.join(cmd[:6])} -p '<message>'")
            self.logger.info(f"[ALPACA AGENT SERVICE] Working directory: {self.working_dir}")

            # Create subprocess with piped stdout/stderr
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir)
            )

            self.logger.info(f"[ALPACA AGENT SERVICE] Subprocess started (PID: {process.pid})")

            # Stream stdout line by line
            line_count = 0
            async for line_bytes in process.stdout:
                try:
                    line = line_bytes.decode('utf-8', errors='replace').rstrip('\n\r')

                    # Include all lines (even empty ones for proper newline handling)
                    line_count += 1

                    # Format as SSE chunk - preserve newline for markdown rendering
                    chunk_data = {
                        "type": "text",
                        "content": line + "\n"
                    }

                    sse_chunk = f"data: {json.dumps(chunk_data)}\n\n"
                    yield sse_chunk

                    self.logger.debug(f"Streamed line {line_count}: {line[:80]}...")

                except Exception as e:
                    self.logger.warning(f"Error processing line: {e}")
                    continue

            # Wait for process to complete
            await process.wait()

            # Check return code
            if process.returncode != 0:
                stderr_bytes = await process.stderr.read()
                stderr_text = stderr_bytes.decode('utf-8', errors='replace')

                error_msg = f"Alpaca agent subprocess failed with code {process.returncode}: {stderr_text}"
                self.logger.error(f"[ALPACA AGENT SERVICE] {error_msg}")

                # Yield error chunk
                error_chunk = {
                    "type": "error",
                    "content": error_msg
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
            else:
                self.logger.success(f"[ALPACA AGENT SERVICE] Streaming completed, lines={line_count}")

            # Yield final DONE chunk
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            self.logger.warning("Alpaca agent streaming cancelled by client")

            # Kill subprocess if running
            if process and process.returncode is None:
                process.kill()
                await process.wait()

            # Yield cancellation chunk
            cancel_chunk = {
                "type": "error",
                "content": "Stream cancelled"
            }
            yield f"data: {json.dumps(cancel_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            self.logger.error(f"Failed to stream Alpaca agent response: {e}", exc_info=True)

            # Kill subprocess if running
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass

            # Yield error chunk
            error_chunk = {
                "type": "error",
                "content": f"Streaming error: {str(e)}"
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
