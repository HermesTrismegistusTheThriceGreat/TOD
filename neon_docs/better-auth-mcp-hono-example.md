# 🪿 HONC Mcp Server

This project extends the `create-honc-app` template to function as an MCP (Model Context Protocol) server with GitHub user authentication via `better-auth`.

## Overview

The repository combines several technologies: Cloudflare Workers, better-auth, Hono, Neon database, and Drizzle ORM. It's designed as a remote MCP server accessible through various MCP clients.

## Remote Server Access

The MCP server is available at `https://better-auth-mcp.cjjdxhdjd.workers.dev/sse`. Clients supporting remote MCP servers can connect directly. For clients lacking native support, use `mcp-remote` via this configuration:

```json
{
  "mcpServers": {
    "cloudflare": {
      "command": "npx",
      "args": ["mcp-remote", "https://better-auth-mcp.cjjdxhdjd.workers.dev/sse"]
    }
  }
}
```

## Setup Requirements

**Prerequisites:**
- Node.js with npm/yarn/pnpm
- Neon PostgreSQL database
- GitHub OAuth Application credentials
- Cloudflare account with wrangler CLI

**Environment Setup:**
Create `.dev.vars` and `.env` files from `.env.example` for local development and Cloudflare Worker deployment.

## Getting Started

1. Clone: `git clone https://github.com/dead8309/better-auth-mcp-hono/`
2. Install: `pnpm install`
3. Configure environment variables
4. Run: `pnpm dev`

## Deployment

Set secrets: `pnpm wrangler secret bulk .dev.vars`

Deploy: `pnpm deploy`
