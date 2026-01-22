---
name: working-on-orchestrator-backend
description: Orchestrator Backend FastAPI specialist for implementing API endpoints, database operations, WebSocket broadcasting, and service layer logic. Use when implementing features in the backend, adding new endpoints, working with the database layer, managing WebSocket events, integrating with Alpaca trading, or understanding the Claude SDK agent orchestration. Delegates to alpaca-mcp and neon-mcp subagents for trading and database operations.
---

# Working on Orchestrator Backend

A comprehensive skill for implementing features, designing APIs, and understanding the Orchestrator Backend FastAPI application. This skill provides intimate knowledge of the codebase architecture and access to specialized subagents for trading and database operations.

## Quick Reference

### Key Files
| Purpose | Path |
|---------|------|
| Entry | `main.py` |
| Database | `modules/database.py` |
| Models | `modules/orch_database_models.py` |
| WebSocket | `modules/websocket_manager.py` |
| Orchestrator | `modules/orchestrator_service.py` |
| Agent Manager | `modules/agent_manager.py` |
| Config | `modules/config.py` |
| Logger | `modules/logger.py` |

### Core Services
| Service | File | Purpose |
|---------|------|---------|
| OrchestratorService | `orchestrator_service.py` | Claude SDK agent execution |
| AgentManager | `agent_manager.py` | Agent lifecycle management |
| AlpacaService | `alpaca_service.py` | Trading API integration |
| AutocompleteService | `autocomplete_service.py` | Command suggestions |
| SpotPriceService | `spot_price_service.py` | Real-time stock prices |
| GreeksSnapshotService | `greeks_snapshot_service.py` | Options Greeks data |

### API Endpoint Groups
| Group | Path Prefix | Purpose |
|-------|-------------|---------|
| Health | `/health` | Health check |
| Orchestrator | `/get_orchestrator`, `/send_chat`, `/load_chat` | Chat operations |
| Agents | `/list_agents` | Agent management |
| Events | `/get_events` | Event stream |
| ADWs | `/adws` | AI Developer Workflows |
| Positions | `/api/positions` | Trading positions |
| Greeks | `/api/greeks` | Options Greeks |
| Trades | `/api/trades`, `/api/trade-stats` | Trade history |

### Technology Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109.x | Web framework |
| asyncpg | 0.29.x | PostgreSQL driver |
| Pydantic | 2.x | Data validation |
| Claude Agent SDK | latest | Agent orchestration |
| Alpaca-py | 0.21.x | Trading API |
| Rich | 13.x | Console logging |

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | - | PostgreSQL connection |
| `ALPACA_API_KEY` | - | Alpaca trading API key |
| `ALPACA_SECRET_KEY` | - | Alpaca secret |
| `ALPACA_BASE_URL` | paper API | Paper/live trading |
| `ANTHROPIC_API_KEY` | - | Claude API access |
| `CORS_ORIGINS` | localhost | Allowed CORS origins |

## Available Subagents

### Alpaca MCP (`alpaca-mcp`)
**Best for:** Trading operations, account management, order execution

**Capabilities:**
- Check account status and buying power
- View and manage positions
- Place and cancel orders
- Roll options positions
- Get market data

### Neon MCP (`neon-mcp`)
**Best for:** Database operations, migrations, SQL queries

**Capabilities:**
- Create and manage database branches
- Run SQL queries
- Perform migrations
- Monitor database health

## Workflows

### Workflow 1: Understanding the Codebase

When asked about architecture or existing features:

1. **Identify the layer** - API, Service, Database, or Utility?
2. **Read relevant files** directly:
   - API routes: `main.py`
   - Database operations: `modules/database.py`
   - Service logic: `modules/[service_name].py`
   - Models: `modules/orch_database_models.py`
3. **Reference expertise.yaml** for complete inventories if needed

### Workflow 2: Adding a New API Endpoint

1. **Read existing patterns** in `main.py`
2. **Define Pydantic models** in `modules/orch_database_models.py`:
   ```python
   class MyRequest(BaseModel):
       field: str

   class MyResponse(BaseModel):
       result: Any
   ```
3. **Add endpoint** in `main.py`:
   ```python
   @app.post("/api/my-endpoint", response_model=MyResponse)
   async def my_endpoint(request: MyRequest):
       # Implementation
       return MyResponse(result=...)
   ```
4. **Add database operations** if needed in `modules/database.py`
5. **Broadcast via WebSocket** if real-time updates needed

### Workflow 3: Adding a New WebSocket Event

1. **Read** `modules/websocket_manager.py` for broadcast patterns
2. **Add broadcast method**:
   ```python
   async def broadcast_my_event(self, data: dict):
       await self.broadcast({
           "type": "my_event",
           "data": data
       })
   ```
3. **Call from service layer** where event originates
4. **Document** in expertise.yaml websocket.events section

### Workflow 4: Adding Database Operations

1. **Read** `modules/database.py` for existing patterns
2. **Use connection context manager**:
   ```python
   async def my_db_operation(param: str) -> Optional[MyModel]:
       async with get_connection() as conn:
           row = await conn.fetchrow(
               "SELECT * FROM table WHERE col = $1",
               param
           )
           return MyModel(**dict(row)) if row else None
   ```
3. **Add Pydantic model** in `modules/orch_database_models.py`
4. **Handle UUID/Decimal conversions** as needed

### Workflow 5: Adding a New Service

1. **Create service file** in `modules/`:
   ```python
   class MyService:
       def __init__(self, ws_manager: WebSocketManager, logger: OrchestratorLogger):
           self.ws_manager = ws_manager
           self.logger = logger

       async def start(self):
           # Initialization
           pass

       async def stop(self):
           # Cleanup
           pass
   ```
2. **Initialize in lifespan** in `main.py`:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       app.state.my_service = MyService(ws_manager, logger)
       await app.state.my_service.start()
       yield
       await app.state.my_service.stop()
   ```
3. **Add endpoints** that use the service

### Workflow 6: Working with Claude SDK Agents

1. **Read** `modules/orchestrator_service.py` for orchestrator patterns
2. **Read** `modules/agent_manager.py` for managed agent patterns
3. **Understand hook system** in `modules/hooks.py` and `modules/command_agent_hooks.py`
4. **Add new tools** to agent by updating tool definitions
5. **Handle streaming responses** via WebSocket broadcasts

## Architecture Patterns

### Pattern 1: Lifespan Context Manager
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services in order
    await init_pool(DATABASE_URL)
    app.state.orchestrator = await create_orchestrator()
    app.state.agent_manager = AgentManager(...)

    yield  # App runs here

    # Shutdown: Cleanup in reverse order
    await app.state.agent_manager.stop()
    await close_pool()
```

### Pattern 2: Database Connection Pool
```python
# Get connection from pool
async with get_connection() as conn:
    result = await conn.fetch("SELECT ...")

# Pool is managed globally
pool = get_pool()  # Returns asyncpg.Pool
```

### Pattern 3: WebSocket Broadcasting
```python
# Broadcast to all connected clients
await ws_manager.broadcast({
    "type": "event_type",
    "data": {"key": "value"}
})

# Send to specific client
await ws_manager.send_to_client(websocket, data)
```

### Pattern 4: Pydantic Model Parsing
```python
class Agent(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    metadata: Dict[str, Any]

    @model_validator(mode='before')
    @classmethod
    def parse_fields(cls, data):
        # Handle UUID conversion from asyncpg
        if isinstance(data.get('id'), str):
            data['id'] = uuid.UUID(data['id'])
        return data
```

### Pattern 5: Hook System
```python
def create_post_tool_hook(agent_id, ws_manager, logger):
    async def post_tool_hook(tool, result, **kwargs):
        # Log to database
        await insert_hook_event(agent_id, "tool_result", {...})
        # Broadcast to WebSocket
        await ws_manager.broadcast_agent_log(agent_id, {...})
    return post_tool_hook
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `orchestrator_agents` | Main orchestrator instances |
| `agents` | Managed agents |
| `agent_logs` | Agent hook/response events |
| `system_logs` | Infrastructure events |
| `orchestrator_chat` | Three-way conversation logs |
| `ai_developer_workflows` | ADW workflows |
| `options_positions` | Trading positions |
| `trade_orders` | Order history |
| `greeks_snapshots` | Options Greeks data |

## Troubleshooting

### Database Connection Issues
1. Check `DATABASE_URL` environment variable
2. Verify PostgreSQL is running
3. Check pool initialization in logs

### WebSocket Not Broadcasting
1. Verify `ws_manager` is passed to service
2. Check client is connected
3. Review broadcast method signature

### Agent Not Responding
1. Check `ANTHROPIC_API_KEY` is valid
2. Review agent logs in database
3. Check hook configuration

### Alpaca API Errors
1. Verify API keys are not placeholders
2. Check circuit breaker state
3. Review rate limiting

## Detailed Knowledge

For comprehensive details, reference the companion expertise file:

- **API Endpoints**: See `expertise.yaml` → `api_endpoints` section
- **Database Operations**: See `expertise.yaml` → `database` section
- **WebSocket Events**: See `expertise.yaml` → `websocket.events` section
- **Service Classes**: See `expertise.yaml` → `services` section
- **Pydantic Models**: See `expertise.yaml` → `models` section

The expertise file contains complete inventories with method signatures, parameters, and detailed specifications.
