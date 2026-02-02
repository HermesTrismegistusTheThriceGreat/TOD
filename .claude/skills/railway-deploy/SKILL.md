---
name: deploying-to-railway
description: Deploys and manages the Orchestrator 3 Stream application (Vue.js frontend + FastAPI backend) on Railway. Use when user asks to deploy to railway, update deployment, railway deploy, sync deployment, push to railway, update docker images on railway, or manage domains (generate domain, add custom domain, configure domain settings). Delegates to railway-mcp subagent for MCP operations.
---

# Deploying to Railway

Manages Railway deployments for the Orchestrator 3 Stream application stack (Vue.js + FastAPI + Neon DB). This skill orchestrates Docker image builds and deployments through the `railway-mcp` subagent.

## Prerequisites

- Railway CLI installed and authenticated (`railway login`)
- Docker installed for building images
- Git repository synced with latest changes
- The `railway-mcp` subagent available at `.claude/agents/railway-mcp.md`

## Expertise Reference

For detailed configuration, environment variables, and troubleshooting, see the expertise file:
- **Expertise File**: `.claude/skills/railway-deploy/expertise.yaml`

This expertise file contains:
- Complete architecture documentation for all 3 services
- Environment variable mappings (dev vs production)
- **CRITICAL: Alpaca Elite subscription constraints** (see below)
- Dev vs Production environment comparison
- Safe deployment workflow checklists
- Comprehensive troubleshooting guides

## CRITICAL: Alpaca Elite Subscription Warning

**Production uses Alpaca Elite subscription for OPRA WebSocket feed. Only ONE connection is allowed.**

| Environment | Alpaca Feed | Multi-Credential Testing |
|-------------|-------------|-------------------------|
| Development | IEX (safe) | Allowed |
| Production | OPRA (Elite) | **FORBIDDEN** |

**Rules:**
1. **NEVER** change `ALPACA_API_KEY` or `ALPACA_SECRET_KEY` in Railway production environment
2. **NEVER** test Elite credentials in development with `ALPACA_DATA_FEED=opra`
3. **ALWAYS** use `ALPACA_DATA_FEED=iex` in development

**Risk:** Dev testing can SILENTLY BREAK production WebSocket - see `expertise.yaml` for full details.

## Configuration

### Project Structure

| Component | Path | Dev Port | Prod Port |
|-----------|------|----------|-----------|
| Backend (FastAPI) | `apps/orchestrator_3_stream/backend/` | 9403 | 8002 |
| Frontend (Vue.js) | `apps/orchestrator_3_stream/frontend/` | 5175 | 80 |
| Auth Service (Hono) | `apps/orchestrator_3_stream/auth-service/` | 9404 | 9404 |

### Docker Images

| Service | Dockerfile Path |
|---------|-----------------|
| Backend | `apps/orchestrator_3_stream/backend/Dockerfile` |
| Frontend | `apps/orchestrator_3_stream/frontend/Dockerfile` |
| Auth Service | `apps/orchestrator_3_stream/auth-service/Dockerfile` |

### Railway MCP Config

Located at `.mcp.json.railway`:
```json
{
  "mcpServers": {
    "Railway": {
      "command": "npx",
      "args": ["-y", "@railway/mcp-server"]
    }
  }
}
```

## Workflow

### 1. Verify Prerequisites

Before any deployment, confirm:
```bash
# Check Railway CLI authentication
railway whoami

# Verify MCP config exists
cat .mcp.json.railway
```

### 2. Delegate to Railway MCP Subagent

All Railway operations MUST be delegated to the `railway-mcp` subagent using the Task tool:

```
Use the Task tool with:
- subagent_type: "railway-mcp"
- prompt: "<specific railway operation>"
```

The subagent will spawn a Claude subprocess with Railway MCP tools enabled.

### 3. Common Operations

#### Deploy Backend Service
Delegate to railway-mcp with prompt:
```
Deploy the backend service from apps/orchestrator_3_stream/backend/ to Railway.
The Dockerfile is at apps/orchestrator_3_stream/backend/Dockerfile.
Use port 8002 (or Railway's $PORT variable).
```

#### Deploy Frontend Service
Delegate to railway-mcp with prompt:
```
Deploy the frontend service from apps/orchestrator_3_stream/frontend/ to Railway.
The Dockerfile is at apps/orchestrator_3_stream/frontend/Dockerfile.
Configure nginx to use Railway's $PORT variable.
```

#### Deploy Auth Service
Delegate to railway-mcp with prompt:
```
Deploy the auth service from apps/orchestrator_3_stream/auth-service/ to Railway.
The Dockerfile is at apps/orchestrator_3_stream/auth-service/Dockerfile.
Use port 9404 (AUTH_PORT or Railway's $PORT variable).
```

#### Full Stack Deployment
Delegate to railway-mcp with prompt:
```
Deploy all three services to Railway:
1. Backend from apps/orchestrator_3_stream/backend/ (FastAPI, port 8002)
2. Frontend from apps/orchestrator_3_stream/frontend/ (Vue.js/nginx, port 80)
3. Auth from apps/orchestrator_3_stream/auth-service/ (Hono, port 9404)
Link them in the same project and configure domains.
```

#### Check Deployment Status
Delegate to railway-mcp with prompt:
```
List all services in the current Railway project and show their deployment status.
```

#### View Logs
Delegate to railway-mcp with prompt:
```
Get recent logs for the <service-name> service.
```

#### Update Environment Variables
Delegate to railway-mcp with prompt:
```
Set the following environment variables for <service-name>:
- VARIABLE_NAME=value
```

#### Generate Railway Domain
Delegate to railway-mcp with prompt:
```
Generate a Railway domain for the <service-name> service.
```

#### Add Custom Domain
Delegate to railway-mcp with prompt:
```
Add a custom domain "example.com" to the <service-name> service on port <port>.
```

#### Check Domain Configuration
Delegate to railway-mcp with prompt:
```
List the current domain configuration for the <service-name> service.
```

### 4. Post-Deployment Verification

After deployment, verify services are running:
1. Check deployment status via railway-mcp
2. Retrieve and verify service URLs/domains
3. Check logs for any startup errors

## Available Railway MCP Tools

The railway-mcp subagent has access to these MCP tools:
- `check-railway-status` - Verify CLI installation and authentication
- `list-projects` - List all projects
- `create-project-and-link` - Create and link a project
- `list-services` - List project services
- `link-service` - Link service to directory
- `deploy` - Deploy a service
- `deploy-template` - Deploy from template library
- `create-environment` - Create new environment
- `link-environment` - Link environment to directory
- `list-variables` - List environment variables
- `set-variables` - Set environment variables
- `generate-domain` - Generate Railway domain for a service
- `get-logs` - Retrieve service logs

### Domain Management Notes

The `generate-domain` MCP tool creates a Railway-provided domain (e.g., `service-name.up.railway.app`). For custom domains, the railway-mcp subagent can use the Railway CLI's `domain` command which supports:
- Generating Railway domains (default if no domain specified)
- Adding custom domains
- Specifying port with `--port` flag
- Targeting specific services with `--service` flag

Railway automatically sets `RAILWAY_PUBLIC_DOMAIN` and `RAILWAY_PRIVATE_DOMAIN` environment variables after domain configuration.

## Examples

### Example 1: Update Deployment After Code Changes

User request:
```
All features are synced to GitHub, please update the deployment
```

You would:
1. Confirm git status shows clean working tree
2. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Deploy the latest changes. Redeploy both services:
     1. Backend at apps/orchestrator_3_stream/backend/
     2. Frontend at apps/orchestrator_3_stream/frontend/
     Show deployment status when complete."
   )
   ```
3. Report deployment results to user

### Example 2: Deploy Backend Only

User request:
```
Deploy just the backend to Railway
```

You would:
1. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Deploy the backend service from apps/orchestrator_3_stream/backend/
     using the Dockerfile at apps/orchestrator_3_stream/backend/Dockerfile.
     Show logs after deployment."
   )
   ```
2. Report deployment status

### Example 3: Check Deployment Status

User request:
```
What's the status of our Railway deployment?
```

You would:
1. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Check Railway status, list all projects and services,
     and show the current deployment status for each service."
   )
   ```
2. Summarize status for user

### Example 4: Set Environment Variables

User request:
```
Add the DATABASE_URL to the backend service on Railway
```

You would:
1. Read the DATABASE_URL from local .env if needed
2. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Set the DATABASE_URL environment variable for the backend service.
     Value: <database_url_value>"
   )
   ```
3. Confirm variable was set

### Example 5: Generate Domain for Service

User request:
```
Generate a domain for the backend service
```

You would:
1. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Generate a Railway domain for the backend service.
     Return the generated domain URL."
   )
   ```
2. Report the generated domain to user

### Example 6: Add Custom Domain

User request:
```
Add api.myapp.com as a custom domain for the backend
```

You would:
1. Use Task tool to delegate to railway-mcp:
   ```
   Task(
     subagent_type="railway-mcp",
     prompt="Add custom domain 'api.myapp.com' to the backend service.
     Configure it to use port 8002.
     Provide DNS configuration instructions if needed."
   )
   ```
2. Report domain configuration and any required DNS settings to user

## Troubleshooting

### Railway CLI Not Authenticated
Run `railway login` to authenticate before using this skill.

### MCP Config Missing
Ensure `.mcp.json.railway` exists in the project root with the Railway MCP server configuration.

### Deployment Fails
1. Check logs via railway-mcp subagent
2. Verify Dockerfile builds locally: `docker build -t test apps/orchestrator_3_stream/backend/`
3. Check environment variables are set correctly

### Service Not Accessible
1. Verify domain is generated via railway-mcp
2. Check service logs for startup errors
3. Confirm port configuration matches Railway's $PORT variable

### Domain Issues
1. **No domain generated**: Use railway-mcp to generate a domain for the service
2. **Custom domain not working**: Verify DNS records are configured correctly (CNAME to Railway)
3. **Wrong port**: Ensure the domain is configured with the correct port (use `-p` flag in CLI)
4. **Domain variables**: Check `RAILWAY_PUBLIC_DOMAIN` and `RAILWAY_PRIVATE_DOMAIN` environment variables are available

## Documentation Reference

Railway documentation is available at `railway_docs/` for deeper reference when needed:

| Topic | File | Use When |
|-------|------|----------|
| Quick Start | `railway_docs/quick-start.md` | New to Railway, need overview |
| CLI Guide | `railway_docs/cli-guide.md` | CLI workflow questions |
| CLI Reference | `railway_docs/cli-reference.md` | Specific CLI command syntax, **domain command** |
| Deployments | `railway_docs/deployments-guide.md` | Deployment configuration, rollbacks |
| Services | `railway_docs/services-guide.md` | Service configuration, scaling |
| Variables | `railway_docs/variables-guide.md` | Environment variable patterns |
| Variables Reference | `railway_docs/variables-reference.md` | Variable syntax, Railway-provided vars |
| Environments | `railway_docs/environments-guide.md` | Multi-environment setup (staging/prod) |
| Environments Reference | `railway_docs/environments-reference.md` | Environment-specific configuration |
| Config as Code | `railway_docs/config-as-code.md` | railway.toml, infrastructure config |
| Templates | `railway_docs/templates-reference.md` | Using Railway templates |
| Deploy Templates | `railway_docs/deploy-template-guide.md` | Template deployment workflow |
| Public API | `railway_docs/public-api-reference.md` | GraphQL API, programmatic access |
| MCP Server Reference | `railway_docs/mcp-server-reference.md` | MCP tool details, advanced usage |
| MCP Server Blog | `railway_docs/mcp-server-blog.md` | MCP server background, use cases |
| MCP GitHub README | `railway_docs/mcp-server-github-readme.md` | MCP installation, setup |
| Community MCP | `railway_docs/community-mcp-github-readme.md` | Community MCP extensions |

### When to Read Documentation

**Always read relevant docs when:**
- You encounter a Railway-specific error not covered in Troubleshooting
- The user asks about features not covered in this skill (e.g., scaling, PR environments)
- You need exact CLI command syntax or flags (e.g., `railway domain` options)
- Configuring advanced options (healthchecks, restart policies, resource limits)
- Setting up multi-environment workflows (staging → production)
- Custom domain configuration, DNS setup, or domain troubleshooting

**How to use:**
1. Identify the topic from the table above
2. Read the relevant file using the Read tool
3. Apply the information to the current task

**Example:** If deployment fails with a cryptic error, read `railway_docs/deployments-guide.md` and `railway_docs/cli-reference.md` for troubleshooting guidance.
