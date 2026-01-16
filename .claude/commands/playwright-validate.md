---
allowed-tools: Bash, Read
description: Launch a Playwright-enabled Claude Code instance to validate UI behavior
argument-hint: [validation instructions]
model: haiku
---

# Purpose

This prompt launches a new Claude Code instance with Playwright MCP tools enabled to perform browser automation and UI validation tasks. It keeps Playwright context isolated from the main session by spawning a subprocess with the dedicated `.mcp.json.playwright` configuration.

## Variables

VALIDATION_INSTRUCTIONS: $1
MCP_CONFIG_PATH: .mcp.json.playwright
PROJECT_ROOT: /Users/muzz/Desktop/tac/TOD

## Instructions

- This prompt executes a Claude Code subprocess with Playwright MCP tools enabled
- The subprocess uses the `.mcp.json.playwright` configuration file which provides browser automation tools
- The Haiku model is used for the subprocess to minimize cost while providing adequate capability
- The subprocess runs in print mode (-p) for non-interactive execution
- Results are captured and returned to the user
- The validation instructions should describe what UI elements or behaviors to check

## Workflow

1. Verify the MCP configuration file exists at `PROJECT_ROOT/.mcp.json.playwright`
2. Construct the Claude Code command with:
   - `--mcp-config .mcp.json.playwright` pointing to the Playwright MCP configuration
   - `--model haiku` for cost-effective execution
   - `--dangerously-skip-permissions` to allow non-interactive browser automation
   - `-p` for print mode (non-interactive)
   - The validation instructions as the prompt
3. Execute the command: `claude --mcp-config .mcp.json.playwright --model haiku --dangerously-skip-permissions -p "VALIDATION_INSTRUCTIONS"`
4. Capture and return the validation results to the user

## Report

Return the full output from the Playwright validation subprocess, including:
- Screenshots taken (if any paths are mentioned)
- Elements found or not found
- Any errors encountered during browser automation
- Overall validation pass/fail status based on the instructions provided
