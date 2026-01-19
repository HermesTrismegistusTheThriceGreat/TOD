# Neon MCP Server

## Overview

The **Neon MCP Server** (version 0.6.4) enables AI agents and development tools like Cursor to interact with Neon by converting natural language into Neon API calls. Users can manage Neon Postgres databases without writing code—simply request actions like "Create a database named 'my-new-database'" or "List all my Neon projects."

Built on the Model Context Protocol (MCP), this server bridges natural language and the Neon API to support project creation, branch management, query execution, and migration handling.

## Quick Setup

Run `npx neonctl@latest init` to authenticate via OAuth, automatically generate a Neon API key, and configure Cursor, VS Code, or Claude Code CLI to connect to the Neon MCP Server. Then ask your AI assistant "Get started with Neon." [Learn more in the docs](https://neon.tech/docs/reference/cli-init)

## Local Setup (STDIO)

For local MCP clients using API key authentication, execute: `npx -y @neondatabase/mcp-server-neon start YOUR_API_KEY`

Retrieve your API key from the [Neon Console](https://console.neon.tech/app/settings/api-keys).

## Read-Only Mode

This mode restricts tools to read-only operations like listing projects, describing schemas, and viewing data. Write operations such as creating projects, branches, or running migrations are disabled.

Enable via OAuth (uncheck "Full access" during authorization) or add the `x-read-only: true` header in your MCP configuration.

## Security Notice

"The Neon MCP Server grants powerful database management capabilities through natural language requests." Review the [MCP security guidance](https://neon.tech/docs/ai/neon-mcp-server#mcp-security-guidance) before using.

## Available Tools

- list_projects
- list_organizations
- list_shared_projects
- create_project
- delete_project
- describe_project
- run_sql
- run_sql_transaction
- describe_table_schema
- get_database_tables
- create_branch
- prepare_database_migration
- complete_database_migration
- describe_branch
- delete_branch
- reset_from_parent
- get_connection_string
- provision_neon_auth
- explain_sql_statement
- prepare_query_tuning
- complete_query_tuning
- list_slow_queries
- list_branch_computes
- compare_database_schema
- search
- fetch
- load_resource

---

**Neon Inc. 2026**
