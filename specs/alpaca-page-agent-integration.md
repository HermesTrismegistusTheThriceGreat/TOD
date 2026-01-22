# Plan: Connect Alpaca Page to alpaca-mcp Agent

## Task Description
Connect the new Alpaca Page (AlpacaAgentView.vue and AlpacaAgentChat.vue) to the `.claude/agents/alpaca-mcp.md` agent for answering user questions about trading accounts, positions, orders, and market data through natural language.

## Objective
Enable the Alpaca Agent page to communicate with the alpaca-mcp agent via the backend, allowing users to interact with their Alpaca trading account using natural language commands. Messages should be processed through a dedicated backend endpoint that spawns the alpaca-mcp agent, with responses streamed back to the frontend.

## Problem Statement
The current AlpacaAgentChat.vue component makes requests to `/api/alpaca-agent/chat` which doesn't exist. The frontend is ready to send messages and handle responses (including SSE streaming), but the backend lacks:
1. An endpoint to receive chat requests
2. Logic to spawn/invoke the alpaca-mcp agent
3. Streaming response delivery back to the frontend

## Solution Approach
1. Create a new backend service (`alpaca_agent_service.py`) that invokes the alpaca-mcp agent using Claude Code subprocess
2. Add a new FastAPI endpoint (`/api/alpaca-agent/chat`) with SSE streaming support
3. Connect the frontend to use the new endpoint with proper error handling
4. Leverage the existing alpaca-mcp.md agent configuration for Claude Code invocation

## Relevant Files
Use these files to complete the task:

**Backend Files:**
- `apps/orchestrator_3_stream/backend/main.py` - Add new endpoint registration
- `apps/orchestrator_3_stream/backend/modules/config.py` - Add configuration for alpaca agent
- `.claude/agents/alpaca-mcp.md` - Reference for alpaca agent capabilities and invocation pattern

**Frontend Files:**
- `apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue` - Already implemented, needs endpoint URL verification
- `apps/orchestrator_3_stream/frontend/src/views/AlpacaAgentView.vue` - View wrapper, no changes needed

### New Files
- `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py` - New service to handle alpaca-mcp agent invocation
- `apps/orchestrator_3_stream/backend/modules/alpaca_agent_models.py` - Request/response Pydantic models

## Implementation Phases

### Phase 1: Foundation
Create the service layer that can invoke the alpaca-mcp agent:
- Add Pydantic models for request/response
- Create AlpacaAgentService class with subprocess management
- Handle MCP configuration verification

### Phase 2: Core Implementation
Build the API endpoint with streaming:
- Add POST `/api/alpaca-agent/chat` endpoint
- Implement SSE streaming for real-time responses
- Handle errors and edge cases

### Phase 3: Integration & Polish
Connect frontend and test:
- Verify frontend endpoint URL matches backend
- Test full round-trip communication
- Add WebSocket broadcast for agent activity (optional enhancement)

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Create Pydantic Models for Alpaca Agent Chat
- Create `apps/orchestrator_3_stream/backend/modules/alpaca_agent_models.py`
- Define `AlpacaAgentChatRequest` with `message: str` field
- Define `AlpacaAgentChatResponse` with `response: str`, `status: str`, `error: Optional[str]` fields
- Define `AlpacaAgentStreamChunk` for SSE streaming with `type: str`, `content: str` fields

### 2. Create Alpaca Agent Service
- Create `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py`
- Add `AlpacaAgentService` class with:
  - `__init__` method to store logger and working directory
  - `verify_mcp_config()` method to check `.mcp.json.alpaca` exists
  - `invoke_agent(message: str)` async method that spawns Claude Code subprocess
  - `invoke_agent_streaming(message: str)` async generator for SSE streaming
- Use subprocess pattern from alpaca-mcp.md: `claude --mcp-config .mcp.json.alpaca --model sonnet --dangerously-skip-permissions -p "PROMPT"`
- Parse subprocess output and yield chunks for streaming

### 3. Add Configuration Constants
- Open `apps/orchestrator_3_stream/backend/modules/config.py`
- Add `ALPACA_MCP_CONFIG_PATH = ".mcp.json.alpaca"` constant
- Add `ALPACA_AGENT_MODEL = "sonnet"` constant

### 4. Register Service in Lifespan
- Open `apps/orchestrator_3_stream/backend/main.py`
- Import `AlpacaAgentService` from `modules.alpaca_agent_service`
- Add initialization in lifespan after other services:
  ```python
  alpaca_agent_service = AlpacaAgentService(logger=logger, working_dir=config.get_working_dir())
  app.state.alpaca_agent_service = alpaca_agent_service
  ```

### 5. Create Chat Endpoint with SSE Streaming
- Open `apps/orchestrator_3_stream/backend/main.py`
- Import `StreamingResponse` from `fastapi.responses`
- Import models from `modules.alpaca_agent_models`
- Add `POST /api/alpaca-agent/chat` endpoint:
  - Accept `AlpacaAgentChatRequest` body
  - Verify MCP config exists via service
  - Return `StreamingResponse` with `media_type="text/event-stream"`
  - Use async generator to stream SSE chunks: `data: {json}\n\n`
  - Handle errors with proper SSE error events

### 6. Verify Frontend Endpoint URL
- Open `apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue`
- Confirm API endpoint URL matches backend: `/api/alpaca-agent/chat`
- Verify SSE stream handling in `sendMessage()` function
- Ensure proper error handling for connection failures

### 7. Add API Route Proxy in Vite Config (if needed)
- Open `apps/orchestrator_3_stream/frontend/vite.config.ts`
- Verify proxy configuration includes `/api` routes to backend
- Add proxy rule if missing:
  ```typescript
  '/api': {
    target: 'http://localhost:8002',
    changeOrigin: true
  }
  ```

### 8. Validate the Implementation
- Start backend: `cd apps/orchestrator_3_stream && ./start_be.sh`
- Start frontend: `cd apps/orchestrator_3_stream && ./start_fe.sh`
- Navigate to Alpaca Agent page in browser
- Test quick commands and custom messages
- Verify streaming responses appear correctly

## Testing Strategy
1. **Unit Tests:**
   - Test `AlpacaAgentService.verify_mcp_config()` with valid/missing config
   - Test subprocess invocation with mock responses

2. **Integration Tests:**
   - Test `/api/alpaca-agent/chat` endpoint with sample messages
   - Verify SSE streaming format is correct
   - Test error handling when MCP config is missing

3. **E2E Tests:**
   - Use Playwright to test the full user flow:
     - Navigate to Alpaca Agent page
     - Click quick command button
     - Verify response appears in chat
     - Test custom message input

## Acceptance Criteria
- [ ] Backend endpoint `/api/alpaca-agent/chat` accepts POST requests
- [ ] Messages are processed through alpaca-mcp agent via Claude Code subprocess
- [ ] Responses stream back to frontend via SSE
- [ ] Frontend displays responses with proper formatting (markdown tables, code blocks)
- [ ] Error states are handled gracefully (connection errors, agent failures)
- [ ] Quick command buttons trigger correct messages
- [ ] Paper trading notice is displayed prominently

## Validation Commands
Execute these commands to validate the task is complete:

- `uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py` - Verify service compiles
- `uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_agent_models.py` - Verify models compile
- `curl -X POST http://localhost:8002/api/alpaca-agent/chat -H "Content-Type: application/json" -d '{"message": "Check account status"}' -N` - Test endpoint with streaming
- `cd apps/orchestrator_3_stream/frontend && npm run build` - Verify frontend builds successfully

## Notes
- The alpaca-mcp agent uses `--dangerously-skip-permissions` flag for autonomous operation
- This is a PAPER TRADING environment - no real money at risk
- The `.mcp.json.alpaca` config file must exist in project root with Alpaca MCP server configuration
- Consider adding conversation history persistence for multi-turn interactions in future enhancement
- WebSocket integration could be added later for bi-directional streaming
