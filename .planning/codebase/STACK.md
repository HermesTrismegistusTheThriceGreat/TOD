# Technology Stack

## Languages
- Python 3.12+ (backend)
- TypeScript/JavaScript (frontend)
- SQL (PostgreSQL migrations)

## Runtime
- FastAPI + Uvicorn (backend)
- Vue 3 + Vite (frontend)
- Hono (auth service)

## Frameworks
- FastAPI - REST API and WebSocket streaming
- Vue 3 - Reactive UI with Composition API
- Pinia - State management
- Better-Auth - Authentication
- Claude Agent SDK - Multi-agent orchestration

## Key Dependencies

### Backend
- `fastapi`, `uvicorn[standard]`, `websockets`
- `asyncpg` - PostgreSQL async driver
- `claude-agent-sdk` - Anthropic SDK
- `alpaca-py` - Alpaca trading client
- `rich` - Terminal UI
- `pydantic` - Data validation
- `python-dotenv` - Environment config

### Frontend
- `vue@3.4.0`, `vue-router@4.4.0`
- `axios`, `pinia`, `element-plus`
- `marked`, `highlight.js`, `dompurify`
- `better-auth@1.4.6`

## Configuration
- `.env` - Environment variables
- `pyproject.toml` - Python project config
- `package.json` - Node dependencies
- `Dockerfile` - Container config
- `.mcp.json.*` - MCP server configs
