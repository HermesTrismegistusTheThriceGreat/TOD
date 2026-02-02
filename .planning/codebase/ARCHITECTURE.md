# Architecture

## Pattern
Monorepo with specialized applications sharing PostgreSQL and multi-agent orchestration.

## Layers

### 1. Data Layer - PostgreSQL (NeonDB)
- **Location**: `/apps/orchestrator_db/`
- **Tables**: orchestrator_agents, agents, agent_logs, ai_developer_workflows

### 2. Backend Services - FastAPI
- **Location**: `/apps/orchestrator_3_stream/backend/`
- **Services**: OrchestratorService, AlpacaAgentService, WebSocketManager

### 3. Frontend - Vue 3 + Pinia
- **Location**: `/apps/orchestrator_3_stream/frontend/`
- **Views**: LoginView, HomeView, AlpacaAgentView

### 4. ADW Framework
- **Location**: `/adws/`
- **Workflows**: plan_build, plan_build_review, plan_build_review_fix

## Data Flow
```
User → OrchestratorService → Claude SDK → Subagents → Database → WebSocket → Frontend
```

## Entry Points
- **Backend**: `backend/main.py` (port 8002)
- **Frontend**: `frontend/src/main.ts` (port 5175)
- **ADW**: `adws/adw_workflows/adw_plan_build.py`
