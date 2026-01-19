# Neon MCP Server Overview - Complete Documentation

## Introduction

The **Neon MCP Server** functions as a bridge enabling users to manage Neon Postgres databases using natural language commands. As stated in the documentation, it "lets you interact with your Neon Postgres databases in natural language."

## Getting Started

### Quick Setup
The fastest initialization path uses a single command:
```bash
npx neonctl@latest init
```

This process handles OAuth authentication, creates an API key automatically, and configures your editor. Currently supported editors include Cursor, VS Code with GitHub Copilot, and Claude Code.

### Alternative Setup Approaches
The documentation provides step-by-step manual configuration instructions for additional editors like Windsurf, ChatGPT, and Zed.

## How It Works

The Neon MCP Server operates within the Model Context Protocol (MCP) framework, which "standardizes communication between LLMs and external tools." It translates natural language requests into Neon API calls, enabling project creation, branch management, query execution, and database migrations.

## Setup Options

### Remote Hosted Server
Located at `https://mcp.neon.tech`, this preview-phase option streamlines setup through OAuth authentication without requiring direct API key management in client configurations.

### Local Installation
Users can install the server locally using npm with Node.js (v18.0.0 or higher) and a Neon API key obtained from the Neon Console.

## Key Features

- **Natural language database management** for intuitive command execution
- **Search functionality** enabling resource discovery across organizations
- **Read-only mode** for safe production database access
- **Guided onboarding** through the `load_resource` tool
- **API key-based authentication** as an alternative to OAuth

## Security Considerations

The documentation emphasizes that the server "is intended for local development and IDE integrations only." Critical recommendations include:

- Always reviewing and authorizing LLM-requested actions before execution
- Restricting access to authorized users only
- Avoiding production environment usage
- Monitoring access and auditing API key distribution

## Usage Examples

Common natural language interactions include:
- Searching resources by keyword
- Listing projects and database contents
- Creating new projects and databases
- Modifying database schemas
- Executing SQL queries

## Resources Referenced

The documentation links to the MCP Protocol specification, Neon API documentation, API key management guides, and the official GitHub repository.
