# External Integrations

## APIs

### Anthropic Claude API
- **Purpose**: Multi-agent orchestration
- **Locations**: `orchestrator_service.py`, `agent_manager.py`, `alpaca_agent_service.py`

### Alpaca Trading API
- **Purpose**: Stock/options trading, real-time data
- **Locations**: `alpaca_service.py`, `alpaca_sync_service.py`, `spot_price_service.py`

## Databases

### PostgreSQL (NeonDB)
- **Driver**: `asyncpg`
- **Location**: `backend/modules/database.py`
- **Migrations**: `apps/orchestrator_db/migrations/`

## Auth Providers

### Better-Auth
- **Location**: `backend/modules/auth_middleware.py`
- **Storage**: PostgreSQL sessions

## WebSockets
- **Endpoint**: `/ws`
- **Manager**: `websocket_manager.py`

## MCP Servers
- `.mcp.json.alpaca` - Trading
- `.mcp.json.neon` - Database
- `.mcp.json.playwright` - Browser automation
