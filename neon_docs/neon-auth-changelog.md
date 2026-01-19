# Neon Changelog: Project Recovery, Free Plan Expansion, and AI Integration

## Project Recovery

Users can now restore accidentally deleted projects within a **7-day window**. The restoration process recovers the complete project setup, including branches, endpoints, compute configurations, settings, connection strings, collaborators, and snapshots. This capability is accessible via CLI and API with no associated costs.

## Expanded Free Plan Project Limit

The Neon Free plan has increased its project allocation from 80 to **100 projects**. This enhancement enables users to create and manage numerous separate database instances for prototyping, learning, and side project development without requiring any manual updates.

## Streamlined MCP Server Configuration

Setup for the Neon MCP Server now requires a single command: `npx neonctl@latest init`. This automated process handles OAuth authentication, API key generation, and configuration for Cursor, VS Code, or Claude Code CLI. Existing users benefit from persistent local configuration, eliminating repeated OAuth reconnection prompts.

## Data Masking Improvements

The Neon Console now includes location-specific masking functions for address fields, cities, and postal codes while maintaining geographic patterns. All masking functions are organized by category: Names, Email Addresses, Phone Numbers, and Addresses.

## AI-Powered Authentication Setup

Developers can now request AI assistants to implement complete Neon Auth flows. Supporting resources include AI rules, MCP prompt templates, and a Claude skill that automatically detect frameworks, install dependencies, and scaffold authentication solutions following best practices.

### Additional Updates

- Materialized views auto-refresh following data anonymization operations
- GitHub Actions now support anonymized branch creation via CI/CD workflows
- SQL Editor supports all Postgres 18 features
- Vercel OAuth provider integration now available for Neon Auth
- Enhanced Vercel Marketplace credential rotation support
