# Solving the MCP Authentication Headache with Vercel & Better Auth

## Overview
This Neon blog post by Ryan Vogel demonstrates how to implement OAuth authentication for Model Context Protocol (MCP) servers using Vercel's MCP adapter and Better Auth.

## The Core Problem
MCP authentication has historically been challenging. Developers initially considered approaches like bearer tokens or auth UUIDs in configuration files, but these expose credentials in plaintext—a significant security risk. The solution: OAuth integration.

## The Solution Architecture
The implementation leverages three key components:

**1. Better Auth Plugin Configuration**
Add the MCP plugin to your auth.ts file with a login page reference.

**2. OAuth Discovery Metadata Route**
Set up a `.well-known/oauth-authorization-server` endpoint providing authorization metadata per MCP specifications.

**3. MCP Handler with Session Validation**
Wrap your MCP server handler with session authentication that retrieves user context from request headers.

## Key Implementation Details
- Uses `@vercel/mcp-adapter` for Next.js MCP routing
- Integrates with `better-auth/plugins` for OAuth support
- Supports optional Redis configuration for Server-Sent Event (SSE) transport resilience
- Enables user-scoped resource access (verifying users only access their own data)

## Practical Example
The demonstration uses an agenda.dev project where users access todos through their MCP client. Upon connection, unauthenticated users receive a login popup; authenticated sessions enable tool access immediately.

## Status & Future
MCP remains early-stage, with authentication, payments, and transport mechanisms still under active development. OAuth adoption by infrastructure providers suggests promising standardization ahead.
