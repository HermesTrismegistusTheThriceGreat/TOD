#!/usr/bin/env python3
"""
Orchestrator 3 Stream Backend
FastAPI server for managing orchestrator agent workflows with PostgreSQL backend
"""

import asyncio
import argparse
import os
import sys
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import time

from rich.table import Table
from rich.console import Console

# Import our custom modules
from modules import config
from modules.logger import get_logger
from modules.websocket_manager import get_websocket_manager
from modules import database
from modules.orchestrator_service import OrchestratorService, get_orchestrator_tools
from modules.agent_manager import AgentManager
from modules.orch_database_models import OrchestratorAgent, AuthUser
from modules.auth_middleware import get_current_user, get_optional_user
from modules.autocomplete_service import AutocompleteService
from modules.autocomplete_models import (
    AutocompleteGenerateRequest,
    AutocompleteUpdateRequest,
    AutocompleteResponse
)
from modules.alpaca_service import init_alpaca_service, get_alpaca_service
from modules.alpaca_sync_service import init_alpaca_sync_service, get_alpaca_sync_service
from modules.spot_price_service import init_spot_price_service, get_spot_price_service
from modules.greeks_snapshot_service import init_greeks_snapshot_service, get_greeks_snapshot_service
from modules.greeks_scheduler import init_greeks_scheduler, shutdown_greeks_scheduler
from modules.alpaca_models import (
    GetPositionsResponse,
    GetPositionResponse,
    SubscribePricesRequest,
    SubscribePricesResponse,
    SubscribeSpotPricesRequest,
    SubscribeSpotPricesResponse,
    CloseStrategyRequest,
    CloseStrategyResponse,
    CloseLegRequest,
    CloseLegResponse,
    TradeListResponse,
    TradeStatsResponse,
    DetailedTradeListResponse,
)
from modules.alpaca_agent_service import AlpacaAgentService
from modules.alpaca_agent_models import AlpacaAgentChatRequest, AlpacaAgentChatResponse
from routers.credentials import router as credentials_router
from routers.accounts import router as accounts_router

logger = get_logger()
ws_manager = get_websocket_manager()
console = Console()  # For startup table display only

# Parse CLI arguments before creating app
parser = argparse.ArgumentParser(description="Orchestrator 3 Stream Backend")
parser.add_argument(
    "--session", type=str, help="Resume existing orchestrator session (session ID)"
)
parser.add_argument(
    "--cwd", type=str, help="Set working directory for orchestrator and agents"
)
args, unknown = parser.parse_known_args()

# Store parsed args for lifespan
CLI_SESSION_ID = args.session
CLI_WORKING_DIR = args.cwd

# Set working directory (use CLI arg or default from config)
if CLI_WORKING_DIR:
    config.set_working_dir(CLI_WORKING_DIR)
else:
    # Use default from ORCHESTRATOR_WORKING_DIR env var or config
    logger.info(f"Using default working directory: {config.get_working_dir()}")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.startup(
        {
            "Service": "Orchestrator 3 Stream Backend",
            "Description": "PostgreSQL-backed multi-agent orchestration",
            "Backend URL": config.BACKEND_URL,
            "WebSocket URL": config.WEBSOCKET_URL,
            "Database": "PostgreSQL (NeonDB)",
            "Logs Directory": str(config.LOG_DIR),
            "Working Directory": config.get_working_dir(),
        }
    )

    # Initialize database connection pool
    logger.info("Initializing database connection pool...")
    await database.init_pool(database_url=config.DATABASE_URL)
    logger.success("Database connection pool initialized")

    # Validate or load orchestrator
    if CLI_SESSION_ID:
        logger.info(f"Looking up orchestrator with session: {CLI_SESSION_ID}")
        orchestrator_data = await database.get_orchestrator_by_session(CLI_SESSION_ID)

        if not orchestrator_data:
            logger.error(f"❌ Session ID not found: {CLI_SESSION_ID}")
            logger.info("Checking if this is a legacy session or orchestrator ID...")

            # Try to find any orchestrator for debugging
            all_orchestrators = await database.get_orchestrator()
            if all_orchestrators:
                logger.info(f"Found orchestrator in database:")
                logger.info(f"  ID: {all_orchestrators.get('id')}")
                logger.info(f"  Session ID: {all_orchestrators.get('session_id')}")
                logger.info(f"\nTo resume, use: --session {all_orchestrators.get('session_id')}")

            raise ValueError(
                f"Session ID '{CLI_SESSION_ID}' not found in orchestrator_agents.session_id.\n\n"
                f"This usually happens when:\n"
                f"  1. The session_id has not been set yet (run without --session first)\n"
                f"  2. Database tables were recreated (data loss)\n"
                f"  3. Session ID was mistyped\n\n"
                f"Solution: Remove the --session argument to start a fresh session."
            )

        # Parse to Pydantic model
        orchestrator = OrchestratorAgent(**orchestrator_data)
        logger.success(f"✅ Resumed orchestrator with session: {CLI_SESSION_ID}")
        logger.info(f"  Orchestrator ID: {orchestrator.id}")
        logger.info(
            f"  Total tokens: {orchestrator.input_tokens + orchestrator.output_tokens}"
        )
        logger.info(f"  Total cost: ${orchestrator.total_cost:.4f}")
    else:
        # No --session provided: Always create new orchestrator
        logger.info("Creating new orchestrator session...")

        # Read system prompt from file
        system_prompt_content = Path(config.ORCHESTRATOR_SYSTEM_PROMPT_PATH).read_text()

        orchestrator_data = await database.create_new_orchestrator(
            system_prompt=system_prompt_content,
            working_dir=config.get_working_dir(),
        )
        # Parse to Pydantic model
        orchestrator = OrchestratorAgent(**orchestrator_data)
        logger.success(f"✅ New orchestrator created: {orchestrator.id}")
        logger.info(f"  Session ID: {orchestrator.session_id or 'Not set yet (will be set after first interaction)'}")
        logger.info(f"  Status: {orchestrator.status}")

    # Initialize agent manager (scoped to this orchestrator)
    logger.info("Initializing agent manager...")
    agent_manager = AgentManager(
        orchestrator_agent_id=orchestrator.id,
        ws_manager=ws_manager,
        logger=logger,
        working_dir=config.get_working_dir()
    )
    logger.success(f"Agent manager initialized for orchestrator {orchestrator.id}")

    # Initialize orchestrator service with agent manager
    logger.info("Initializing orchestrator service...")
    orchestrator_service = OrchestratorService(
        ws_manager=ws_manager,
        logger=logger,
        agent_manager=agent_manager,
        session_id=CLI_SESSION_ID or orchestrator.session_id,
        working_dir=config.get_working_dir(),
    )

    # Store in app state for access in endpoints
    app.state.orchestrator_service = orchestrator_service
    app.state.orchestrator = orchestrator

    # Initialize autocomplete service
    logger.info("Initializing autocomplete service...")
    autocomplete_service = AutocompleteService(
        orchestrator_agent_id=orchestrator.id,
        logger=logger,
        working_dir=config.get_working_dir(),
        ws_manager=ws_manager
    )
    app.state.autocomplete_service = autocomplete_service
    logger.success("Autocomplete service initialized")

    # Initialize Alpaca service
    logger.info("Initializing Alpaca service...")
    alpaca_service = await init_alpaca_service(app)
    alpaca_service.set_websocket_manager(ws_manager)
    logger.success("Alpaca service initialized")

    # Initialize Spot Price service (graceful degradation on failure)
    logger.info("Initializing Spot Price service...")
    try:
        spot_price_service = await init_spot_price_service(app)
        spot_price_service.set_websocket_manager(ws_manager)
        logger.success("Spot Price service initialized")
    except Exception as e:
        logger.warning(f"Spot Price service initialization failed (non-blocking): {e}")
        app.state.spot_price_service = None

    # Initialize Alpaca Sync service
    logger.info("Initializing Alpaca Sync service...")
    alpaca_sync_service = await init_alpaca_sync_service(app, alpaca_service)
    logger.success("Alpaca Sync service initialized")

    # Auto-sync orders on startup if Alpaca is configured
    if alpaca_service.is_configured:
        try:
            logger.info("Auto-syncing Alpaca orders...")
            orders = await alpaca_sync_service.sync_orders()
            logger.success(f"Auto-synced {len(orders)} orders from Alpaca")
        except Exception as e:
            logger.warning(f"Auto-sync failed (non-blocking): {e}")

    # Initialize Greeks Snapshot service
    logger.info("Initializing Greeks Snapshot service...")
    greeks_service = await init_greeks_snapshot_service(app)
    logger.success("Greeks Snapshot service initialized")

    # Initialize Greeks Scheduler
    logger.info("Initializing Greeks Scheduler...")
    greeks_scheduler = init_greeks_scheduler(app)
    logger.success("Greeks Scheduler initialized")

    # Initialize Alpaca Agent service
    logger.info("Initializing Alpaca Agent service...")
    alpaca_agent_service = AlpacaAgentService(logger=logger, working_dir=config.get_working_dir())
    app.state.alpaca_agent_service = alpaca_agent_service
    logger.success("Alpaca Agent service initialized")

    logger.success("Backend initialization complete")

    yield  # Server runs

    # Shutdown
    # Shutdown Greeks Scheduler
    logger.info("Shutting down Greeks Scheduler...")
    shutdown_greeks_scheduler()

    # Shutdown Greeks Snapshot service
    if hasattr(app.state, 'greeks_snapshot_service'):
        logger.info("Shutting down Greeks Snapshot service...")
        await app.state.greeks_snapshot_service.close()

    # Shutdown Alpaca Sync service
    if hasattr(app.state, 'alpaca_sync_service'):
        logger.info("Shutting down Alpaca Sync service...")
        await app.state.alpaca_sync_service.close()

    # Shutdown Spot Price service
    if hasattr(app.state, 'spot_price_service') and app.state.spot_price_service is not None:
        logger.info("Shutting down Spot Price service...")
        await app.state.spot_price_service.shutdown()

    # Shutdown Alpaca service
    if hasattr(app.state, 'alpaca_service'):
        logger.info("Shutting down Alpaca service...")
        await app.state.alpaca_service.shutdown()

    logger.info("Closing database connection pool...")
    await database.close_pool()
    logger.shutdown()


# Create FastAPI app with lifespan
app = FastAPI(title="Orchestrator 3 Stream API", version="1.0.0", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # From .env configuration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(credentials_router)
app.include_router(accounts_router)


# ═══════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════


class LoadChatRequest(BaseModel):
    """Request model for loading chat history"""

    orchestrator_agent_id: str
    limit: Optional[int] = 50


class SendChatRequest(BaseModel):
    """Request model for sending chat message"""

    message: str
    orchestrator_agent_id: str


# ═══════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.http_request("GET", "/health", 200)
    return {
        "status": "healthy",
        "service": "orchestrator-3-stream",
        "websocket_connections": ws_manager.get_connection_count(),
    }


@app.get("/api/me")
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Protected endpoint that requires valid Better Auth session.
    Returns user profile data if authenticated, raises 401 if not.

    Returns:
        User profile data including id, name, email, etc.

    Raises:
        HTTPException: 401 if not authenticated or session invalid

    Example:
        >>> # With valid session cookie:
        >>> GET /api/me
        >>> {
        ...     "user": {
        ...         "id": "user_123",
        ...         "name": "John Doe",
        ...         "email": "john@example.com",
        ...         "email_verified": true,
        ...         "image": null
        ...     }
        ... }
    """
    logger.http_request("GET", "/api/me", 200)
    return {"user": user.model_dump()}


@app.get("/get_orchestrator")
async def get_orchestrator_info():
    """
    Get orchestrator agent information including system metadata.

    Fetches fresh data from database to ensure session_id is always current.
    Returns orchestrator ID, session, costs, metadata, slash commands, and templates.
    """
    try:
        logger.http_request("GET", "/get_orchestrator")

        # Refresh orchestrator from database to get current session_id
        orchestrator_id = app.state.orchestrator.id
        orchestrator_data = await database.get_orchestrator_by_id(orchestrator_id)

        if not orchestrator_data:
            logger.error(f"Orchestrator not found in database: {orchestrator_id}")
            raise HTTPException(status_code=404, detail="Orchestrator not found")

        # Update app.state with fresh data (keeps in-memory cache synchronized)
        orchestrator = OrchestratorAgent(**orchestrator_data)
        app.state.orchestrator = orchestrator

        # Discover slash commands
        slash_commands = discover_slash_commands(config.get_working_dir())

        # Get agent templates from SubagentRegistry
        from modules.subagent_loader import SubagentRegistry
        registry = SubagentRegistry(config.get_working_dir(), logger)
        templates = registry.list_templates()

        # Get orchestrator tools
        orchestrator_tools = get_orchestrator_tools()

        # Get available ADW workflow types
        adw_workflows = discover_adw_workflows(config.get_working_dir())

        # Prepare metadata with fallback for system_message_info
        metadata = orchestrator.metadata or {}

        # If system_message_info doesn't exist, create fallback from current state
        if not metadata.get("system_message_info"):
            metadata["system_message_info"] = {
                "session_id": orchestrator.session_id,
                "cwd": orchestrator.working_dir or config.get_working_dir(),
                "captured_at": None,  # Indicates this is fallback data
                "subtype": "fallback"  # Indicates this wasn't from a SystemMessage
            }

        logger.http_request("GET", "/get_orchestrator", 200)
        return {
            "status": "success",
            "orchestrator": {
                "id": str(orchestrator.id),
                "session_id": orchestrator.session_id,
                "status": orchestrator.status,
                "working_dir": orchestrator.working_dir,
                "input_tokens": orchestrator.input_tokens,
                "output_tokens": orchestrator.output_tokens,
                "total_cost": float(orchestrator.total_cost),
                "metadata": metadata,  # Include metadata with fallback
            },
            "slash_commands": slash_commands,  # List of available commands
            "agent_templates": templates,      # List of available templates
            "orchestrator_tools": orchestrator_tools,  # List of management tools
            "adw_workflows": adw_workflows,    # List of available ADW workflow types
        }
    except Exception as e:
        logger.error(f"Failed to get orchestrator info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_headers")
async def get_headers():
    """
    Get header information for the frontend.

    Returns:
        - cwd: Current working directory for orchestrator and agents
    """
    try:
        logger.http_request("GET", "/get_headers")

        cwd = config.get_working_dir()

        logger.http_request("GET", "/get_headers", 200)
        return {"status": "success", "cwd": cwd}
    except Exception as e:
        logger.error(f"Failed to get headers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# SLASH COMMAND DISCOVERY
# ═══════════════════════════════════════════════════════════

# Import slash command discovery from parser module
from modules.slash_command_parser import discover_slash_commands


# ═══════════════════════════════════════════════════════════
# ADW WORKFLOW DISCOVERY
# ═══════════════════════════════════════════════════════════

def discover_adw_workflows(working_dir: str) -> List[dict]:
    """
    Discover available ADW workflow types from adws/adw_workflows/*.py files.

    Args:
        working_dir: Working directory (project root)

    Returns:
        List of dicts with workflow type name and description
    """
    workflow_dir = Path(working_dir) / "adws" / "adw_workflows"
    if not workflow_dir.exists():
        return []

    workflows = []
    for file in workflow_dir.glob("adw_*.py"):
        # Extract type from filename: adw_plan_build.py -> plan_build
        name = file.stem  # adw_plan_build
        if name.startswith("adw_"):
            workflow_type = name[4:]  # Remove "adw_" prefix

            # Try to extract description from docstring
            description = f"ADW workflow: {workflow_type.replace('_', ' ')}"
            try:
                content = file.read_text(encoding='utf-8')
                # Look for module docstring
                if '"""' in content:
                    start = content.index('"""') + 3
                    end = content.index('"""', start)
                    doc = content[start:end].strip()
                    # Get first line of docstring
                    first_line = doc.split('\n')[0].strip()
                    if first_line and len(first_line) < 200:
                        description = first_line
            except Exception:
                pass

            workflows.append({
                "type": workflow_type,
                "display_name": workflow_type.replace("_", "-"),
                "description": description,
            })

    return sorted(workflows, key=lambda x: x["type"])


class OpenFileRequest(BaseModel):
    """Request model for opening a file in IDE"""
    file_path: str


@app.post("/api/open-file")
async def open_file_in_ide(request: OpenFileRequest):
    """
    Open a file in the configured IDE (Cursor or VS Code).

    Opens the file using the IDE command specified in config.IDE_COMMAND.
    """
    try:
        import subprocess

        logger.http_request("POST", "/api/open-file")

        if not config.IDE_ENABLED:
            logger.http_request("POST", "/api/open-file", 403)
            return {
                "status": "error",
                "message": "IDE integration is disabled in configuration"
            }

        file_path = request.file_path

        # Validate file exists
        if not os.path.exists(file_path):
            logger.http_request("POST", "/api/open-file", 404)
            return {"status": "error", "message": f"File not found: {file_path}"}

        # Build IDE command
        ide_cmd = config.IDE_COMMAND
        full_command = [ide_cmd, file_path]

        logger.info(f"Opening file in {ide_cmd}: {file_path}")

        # Execute IDE command
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            logger.http_request("POST", "/api/open-file", 200)
            return {
                "status": "success",
                "message": f"Opened {file_path} in {ide_cmd}",
                "file_path": file_path
            }
        else:
            logger.error(f"Failed to open file in IDE: {result.stderr}")
            logger.http_request("POST", "/api/open-file", 500)
            return {
                "status": "error",
                "message": f"Failed to open file in IDE: {result.stderr}"
            }

    except subprocess.TimeoutExpired:
        logger.error("IDE command timed out")
        logger.http_request("POST", "/api/open-file", 500)
        return {"status": "error", "message": "IDE command timed out"}
    except FileNotFoundError:
        logger.error(f"IDE command not found: {config.IDE_COMMAND}")
        logger.http_request("POST", "/api/open-file", 500)
        return {
            "status": "error",
            "message": f"IDE command not found: {config.IDE_COMMAND}. Please ensure it's installed and in PATH."
        }
    except Exception as e:
        logger.error(f"Failed to open file in IDE: {e}")
        logger.http_request("POST", "/api/open-file", 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/load_chat")
async def load_chat(request: LoadChatRequest):
    """
    Load chat history for orchestrator agent.

    Returns:
        - messages: List of chat messages
        - turn_count: Total number of messages
    """
    try:
        logger.http_request("POST", "/load_chat")

        service: OrchestratorService = app.state.orchestrator_service
        result = await service.load_chat_history(
            orchestrator_agent_id=request.orchestrator_agent_id, limit=request.limit
        )

        logger.http_request("POST", "/load_chat", 200)
        return {
            "status": "success",
            "messages": result["messages"],
            "turn_count": result["turn_count"],
        }

    except Exception as e:
        logger.error(f"Failed to load chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send_chat")
async def send_chat(request: SendChatRequest):
    """
    Send message to orchestrator agent.

    Message is processed with streaming via WebSocket.
    This endpoint returns immediately after starting execution.

    Returns:
        - status: success/error
        - message: Confirmation message
    """
    try:
        logger.http_request("POST", "/send_chat")

        service: OrchestratorService = app.state.orchestrator_service

        # Process message asynchronously (streaming via WebSocket)
        asyncio.create_task(
            service.process_user_message(
                user_message=request.message,
                orchestrator_agent_id=request.orchestrator_agent_id,
            )
        )

        logger.http_request("POST", "/send_chat", 200)
        return {
            "status": "success",
            "message": "Message received, processing with streaming",
        }

    except Exception as e:
        logger.error(f"Failed to send chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset_context")
async def reset_context():
    """
    Reset orchestrator context to start a fresh conversation.

    Clears the session_id in memory AND database so:
    - Next message starts a new Claude SDK session
    - Context stays cleared even after backend restart
    - Chat history remains in database for reference

    Returns:
        - status: success
        - message: Confirmation message
    """
    try:
        logger.http_request("POST", "/reset_context")

        service: OrchestratorService = app.state.orchestrator_service
        orchestrator_id = app.state.orchestrator.id

        # Clear the session_id to start fresh on next message
        old_session = service.session_id
        service.session_id = None

        # Also reset the flag so new session_id gets saved to DB
        service.started_with_session = False

        # Clear session_id in database (persists across restarts)
        await database.clear_orchestrator_session(orchestrator_id)

        logger.info(f"Context reset. Old session: {old_session[:20] if old_session else 'None'}...")

        logger.http_request("POST", "/reset_context", 200)
        return {
            "status": "success",
            "message": "Context cleared. Next message will start a fresh session.",
        }

    except Exception as e:
        logger.error(f"Failed to reset context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_events")
async def get_events_endpoint(
    agent_id: Optional[str] = None,
    task_slug: Optional[str] = None,
    event_types: str = "all",
    limit: int = 50,
    offset: int = 0,
):
    """
    Get events from all sources for EventStream component.

    Query params:
        - agent_id: Optional filter by agent UUID
        - task_slug: Optional filter by task
        - event_types: Comma-separated list or "all" (default: "all")
        - limit: Max events to return (default 50)
        - offset: Pagination offset (default 0)

    Returns:
        - status: success/error
        - events: List of unified events with sourceType field
        - count: Total event count
    """
    try:
        logger.http_request("GET", "/get_events")

        # Parse event types (default: agent_logs and orchestrator_chat only, no system_logs)
        requested_types = (
            event_types.split(",")
            if event_types != "all"
            else ["agent_logs", "orchestrator_chat"]
        )

        all_events = []

        # Fetch agent logs
        if "agent_logs" in requested_types:
            agent_uuid = uuid.UUID(agent_id) if agent_id else None
            if agent_uuid:
                agent_logs = await database.get_agent_logs(
                    agent_id=agent_uuid, task_slug=task_slug, limit=limit, offset=offset
                )
            else:
                agent_logs = await database.list_agent_logs(
                    orchestrator_agent_id=app.state.orchestrator.id,
                    limit=limit,
                    offset=offset
                )

            # Add sourceType field
            for log in agent_logs:
                log["sourceType"] = "agent_log"
                all_events.append(log)

        # Fetch system logs
        if "system_logs" in requested_types:
            system_logs = await database.list_system_logs(limit=limit, offset=offset)
            for log in system_logs:
                log["sourceType"] = "system_log"
                all_events.append(log)

        # Fetch orchestrator chat (filtered by current orchestrator)
        if "orchestrator_chat" in requested_types:
            chat_logs = await database.list_orchestrator_chat(
                orchestrator_agent_id=app.state.orchestrator.id,
                limit=limit,
                offset=offset
            )
            for log in chat_logs:
                log["sourceType"] = "orchestrator_chat"
                all_events.append(log)

        # Sort by timestamp (newest first for limiting)
        all_events.sort(
            key=lambda x: x.get("timestamp") or x.get("created_at"), reverse=True
        )

        # Apply limit to get most recent events
        all_events = all_events[:limit]

        # Reverse to show oldest at top, newest at bottom
        all_events.reverse()

        # Convert UUIDs and datetimes to strings for JSON
        for event in all_events:
            for key, value in list(event.items()):
                if isinstance(value, uuid.UUID):
                    event[key] = str(value)
                elif hasattr(value, "isoformat"):
                    event[key] = value.isoformat()

        logger.http_request("GET", "/get_events", 200)
        return {"status": "success", "events": all_events, "count": len(all_events)}

    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list_agents")
async def list_agents_endpoint():
    """
    List all active agents for sidebar display.

    Returns:
        - status: success/error
        - agents: List of agent objects enriched with log_count from agent_logs table
    """
    try:
        logger.http_request("GET", "/list_agents")

        agents = await database.list_agents(
            orchestrator_agent_id=app.state.orchestrator.id,
            archived=False
        )

        # Serialize Pydantic models to dicts
        agents_data = [agent.model_dump() for agent in agents]

        # Enrich each agent with log count from agent_logs table
        async with database.get_connection() as conn:
            for agent_data in agents_data:
                agent_id = agent_data["id"]

                # Count logs for this agent from agent_logs table
                log_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM agent_logs WHERE agent_id = $1", agent_id
                )
                agent_data["log_count"] = log_count or 0

        logger.http_request("GET", "/list_agents", 200)
        return {"status": "success", "agents": agents_data}

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autocomplete-generate")
async def autocomplete_generate(request: AutocompleteGenerateRequest) -> AutocompleteResponse:
    """
    Generate autocomplete suggestions for user input.

    Args:
        request: AutocompleteGenerateRequest with user_input and orchestrator_agent_id

    Returns:
        AutocompleteResponse with list of autocomplete suggestions
    """
    try:
        logger.http_request("POST", "/autocomplete-generate")
        service: AutocompleteService = app.state.autocomplete_service
        response = await service.generate_autocomplete(
            user_input=request.user_input,
            orchestrator_agent_id=request.orchestrator_agent_id
        )
        logger.http_request("POST", "/autocomplete-generate", 200)
        return response
    except Exception as e:
        logger.error(f"Autocomplete generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autocomplete-update")
async def autocomplete_update(request: AutocompleteUpdateRequest):
    """
    Update autocomplete completion history.

    Tracks whether user accepted an autocomplete suggestion or typed manually.
    This data is used to improve future autocomplete suggestions.

    Args:
        request: AutocompleteUpdateRequest with completion_type and related fields

    Returns:
        Success status
    """
    try:
        logger.http_request("POST", "/autocomplete-update")
        service: AutocompleteService = app.state.autocomplete_service
        await service.update_completion_history(
            orchestrator_agent_id=request.orchestrator_agent_id,
            completion_type=request.completion_type,
            user_input_on_enter=request.user_input_on_enter,
            user_input_before_completion=request.user_input_before_completion,
            autocomplete_item=request.autocomplete_item,
            reasoning=request.reasoning
        )
        logger.http_request("POST", "/autocomplete-update", 200)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Autocomplete update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates and chat messages"""

    await ws_manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()

            # Log received message
            if data:
                logger.debug(f"📥 Received WebSocket message: {data[:100]}")

                # Try to parse as JSON for structured messages
                try:
                    message = json.loads(data)

                    # Route message based on type
                    if isinstance(message, dict) and "type" in message:
                        msg_type = message.get("type")

                        # Handle ADW broadcast requests from workflow processes
                        if msg_type == "adw_broadcast":
                            broadcast_type = message.get("broadcast_type")
                            logger.debug(f"ADW broadcast request: {broadcast_type}")

                            if broadcast_type == "adw_created":
                                await ws_manager.broadcast_adw_created(
                                    message.get("adw", {})
                                )
                            elif broadcast_type == "adw_updated":
                                await ws_manager.broadcast_adw_updated(
                                    message.get("adw_id", ""),
                                    message.get("adw", {})
                                )
                            elif broadcast_type == "adw_event":
                                await ws_manager.broadcast_adw_event(
                                    message.get("adw_id", ""),
                                    message.get("event", {})
                                )
                            elif broadcast_type == "adw_step_change":
                                await ws_manager.broadcast_adw_step_change(
                                    message.get("adw_id", ""),
                                    message.get("step", ""),
                                    message.get("event_type", ""),
                                    message.get("payload")
                                )
                            elif broadcast_type == "adw_status":
                                # Broadcast status as an adw_updated event
                                await ws_manager.broadcast_adw_updated(
                                    message.get("adw_id", ""),
                                    {
                                        "status": message.get("status"),
                                        "current_step": message.get("current_step"),
                                        "completed_steps": message.get("completed_steps"),
                                        "error_message": message.get("error_message"),
                                    }
                                )
                            elif broadcast_type == "adw_event_summary_update":
                                # Broadcast summary update for an existing ADW event
                                await ws_manager.broadcast_adw_event_summary_update(
                                    message.get("adw_id", ""),
                                    message.get("event_id", ""),
                                    message.get("summary", "")
                                )
                            else:
                                logger.warning(f"Unknown ADW broadcast type: {broadcast_type}")

                        # Handle agent broadcast requests from ADW workflow processes
                        elif msg_type == "agent_broadcast":
                            broadcast_type = message.get("broadcast_type")
                            logger.debug(f"Agent broadcast request: {broadcast_type}")

                            if broadcast_type == "agent_created":
                                await ws_manager.broadcast_agent_created(
                                    message.get("agent", {})
                                )
                            elif broadcast_type == "agent_status_changed":
                                await ws_manager.broadcast_agent_status_change(
                                    message.get("agent_id", ""),
                                    message.get("old_status", ""),
                                    message.get("new_status", "")
                                )
                            elif broadcast_type == "agent_updated":
                                await ws_manager.broadcast_agent_updated(
                                    message.get("agent_id", ""),
                                    message.get("agent", {})
                                )
                            else:
                                logger.warning(f"Unknown agent broadcast type: {broadcast_type}")
                        else:
                            # Log unknown message types for future event handlers
                            logger.debug(f"Received WebSocket message type: {msg_type}")

                except json.JSONDecodeError:
                    # Not JSON, treat as plain text (keep alive ping)
                    pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ════════════════════════════════════════════════════════════════════════════════
# AI Developer Workflow (ADW) Endpoints
# ════════════════════════════════════════════════════════════════════════════════


class ListAdwsRequest(BaseModel):
    """Request model for listing ADWs"""
    orchestrator_agent_id: str
    status: Optional[str] = None
    limit: Optional[int] = 20


class GetAdwEventsRequest(BaseModel):
    """Request model for getting ADW events"""
    adw_id: str
    limit: Optional[int] = 2000
    event_type: Optional[str] = None
    include_payload: Optional[bool] = True


@app.post("/adws")
async def list_adws(request: ListAdwsRequest):
    """
    List AI Developer Workflows for an orchestrator.

    Returns ADWs sorted by creation date (newest first).
    Optionally filter by status (pending, in_progress, completed, failed, cancelled).
    """
    try:
        logger.http_request("POST", "/adws")

        orchestrator_id = uuid.UUID(request.orchestrator_agent_id)
        adws = await database.list_adws(
            orchestrator_agent_id=orchestrator_id,
            status=request.status,
            limit=request.limit,
        )

        # Serialize UUIDs and datetimes
        for adw in adws:
            for key, value in adw.items():
                if isinstance(value, uuid.UUID):
                    adw[key] = str(value)
                elif hasattr(value, 'isoformat'):
                    adw[key] = value.isoformat()

        logger.http_request("POST", "/adws", 200)
        return {"status": "success", "adws": adws, "count": len(adws)}

    except Exception as e:
        logger.error(f"Failed to list ADWs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/adws/{adw_id}")
async def get_adw(adw_id: str):
    """
    Get a single ADW by ID with full status details.

    Returns the complete ADW record including:
    - Status and progress (current_step, completed_steps, total_steps)
    - Timing (started_at, completed_at, duration_seconds)
    - Error info (error_message, error_step) if failed
    - Input/output data
    """
    try:
        logger.http_request("GET", f"/adws/{adw_id}")

        adw = await database.get_adw(uuid.UUID(adw_id))

        if not adw:
            raise HTTPException(status_code=404, detail=f"ADW not found: {adw_id}")

        # Serialize UUIDs and datetimes
        for key, value in adw.items():
            if isinstance(value, uuid.UUID):
                adw[key] = str(value)
            elif hasattr(value, 'isoformat'):
                adw[key] = value.isoformat()

        logger.http_request("GET", f"/adws/{adw_id}", 200)
        return {"status": "success", "adw": adw}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ADW {adw_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/adws/{adw_id}/events")
async def get_adw_events(adw_id: str, request: GetAdwEventsRequest):
    """
    Get events for an ADW (swimlane squares) from BOTH agent_logs AND system_logs.

    Returns events sorted by timestamp (oldest first) for swimlane rendering.
    Each event represents a square in the swimlane UI.

    Optionally filter by event_type:
    - StepStart, StepEnd: Step lifecycle markers
    - PostToolUse: Tool execution events
    - text, result: Response events
    - SystemInfo, SystemWarning, SystemError: System log events
    """
    try:
        logger.http_request("POST", f"/adws/{adw_id}/events")

        # Fetch from agent_logs
        agent_events = await database.get_adw_logs(
            adw_id=uuid.UUID(adw_id),
            limit=request.limit,
            event_type=request.event_type,
            include_payload=request.include_payload,
        )

        # Fetch from system_logs (no event_type filter - system logs have different types)
        system_events = await database.get_adw_system_logs(
            adw_id=uuid.UUID(adw_id),
            limit=request.limit,
            include_metadata=request.include_payload,
        )

        # Merge and sort by timestamp
        events = agent_events + system_events

        # Serialize UUIDs and datetimes
        for event in events:
            for key, value in event.items():
                if isinstance(value, uuid.UUID):
                    event[key] = str(value)
                elif hasattr(value, 'isoformat'):
                    event[key] = value.isoformat()

        # Sort by timestamp (oldest first)
        events.sort(key=lambda e: e.get("timestamp", ""))

        # Group events by adw_step for swimlane rendering
        steps: Dict[str, List[Dict]] = {}
        for event in events:
            step = event.get("adw_step") or "_workflow"
            if step not in steps:
                steps[step] = []
            steps[step].append(event)

        logger.http_request("POST", f"/adws/{adw_id}/events", 200)
        return {
            "status": "success",
            "adw_id": adw_id,
            "events": events,
            "events_by_step": steps,
            "count": len(events),
        }

    except Exception as e:
        logger.error(f"Failed to get ADW events for {adw_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/adws/{adw_id}/summary")
async def get_adw_summary(adw_id: str):
    """
    Get a summary of an ADW including status and step breakdown.

    Returns:
    - ADW basic info (name, type, status)
    - Step summary with event counts per step
    - Agent info for each step
    """
    try:
        logger.http_request("GET", f"/adws/{adw_id}/summary")

        # Get ADW record
        adw = await database.get_adw(uuid.UUID(adw_id))
        if not adw:
            raise HTTPException(status_code=404, detail=f"ADW not found: {adw_id}")

        # Get all events grouped by step
        events = await database.get_adw_logs(
            adw_id=uuid.UUID(adw_id),
            limit=500,
            include_payload=False,
        )

        # Build step summary
        step_summary: Dict[str, Dict] = {}
        for event in events:
            step = event.get("adw_step") or "_workflow"
            if step not in step_summary:
                step_summary[step] = {
                    "step": step,
                    "event_count": 0,
                    "event_types": {},
                    "agent_id": None,
                    "started_at": None,
                    "ended_at": None,
                }

            step_summary[step]["event_count"] += 1

            # Track event type counts
            event_type = event.get("event_type", "unknown")
            step_summary[step]["event_types"][event_type] = (
                step_summary[step]["event_types"].get(event_type, 0) + 1
            )

            # Track agent and timing
            if event.get("agent_id"):
                step_summary[step]["agent_id"] = str(event["agent_id"])
            if event_type == "StepStart":
                step_summary[step]["started_at"] = event.get("timestamp")
            if event_type == "StepEnd":
                step_summary[step]["ended_at"] = event.get("timestamp")

        # Serialize ADW
        for key, value in adw.items():
            if isinstance(value, uuid.UUID):
                adw[key] = str(value)
            elif hasattr(value, 'isoformat'):
                adw[key] = value.isoformat()

        logger.http_request("GET", f"/adws/{adw_id}/summary", 200)
        return {
            "status": "success",
            "adw": adw,
            "steps": list(step_summary.values()),
            "total_events": len(events),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ADW summary for {adw_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════════
# ALPACA TRADING ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════


@app.get("/api/positions", response_model=GetPositionsResponse, tags=["Alpaca"])
async def get_positions(request: Request):
    """
    Get all iron condor positions from Alpaca.

    Returns grouped iron condor positions with all leg details.
    Positions are cached and circuit breaker protects against API failures.

    Returns:
        GetPositionsResponse with list of iron condor positions
    """
    try:
        logger.http_request("GET", "/api/positions")
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            logger.http_request("GET", "/api/positions", 200)
            return GetPositionsResponse(
                status="error",
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file with your real API keys from https://alpaca.markets/"
            )

        positions = await alpaca_service.get_all_positions()

        logger.http_request("GET", "/api/positions", 200)
        return GetPositionsResponse(
            status="success",
            positions=positions,
            total_count=len(positions)
        )

    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return GetPositionsResponse(
            status="error",
            message=str(e)
        )


@app.get("/api/positions/{position_id}", response_model=GetPositionResponse, tags=["Alpaca"])
async def get_position(request: Request, position_id: str):
    """
    Get a specific iron condor position by ID.

    Args:
        position_id: UUID of the position

    Returns:
        GetPositionResponse with position details or error
    """
    try:
        logger.http_request("GET", f"/api/positions/{position_id}")
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            logger.http_request("GET", f"/api/positions/{position_id}", 200)
            return GetPositionResponse(
                status="error",
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file with your real API keys from https://alpaca.markets/"
            )

        position = await alpaca_service.get_position_by_id(position_id)

        if position is None:
            logger.http_request("GET", f"/api/positions/{position_id}", 200)
            return GetPositionResponse(
                status="error",
                message=f"Position not found: {position_id}"
            )

        logger.http_request("GET", f"/api/positions/{position_id}", 200)
        return GetPositionResponse(
            status="success",
            position=position
        )

    except Exception as e:
        logger.error(f"Failed to get position {position_id}: {e}")
        return GetPositionResponse(
            status="error",
            message=str(e)
        )


@app.post("/api/positions/subscribe-prices", response_model=SubscribePricesResponse, tags=["Alpaca"])
async def subscribe_prices(request: Request, subscribe_request: SubscribePricesRequest):
    """
    Subscribe to real-time price updates for option symbols.

    Call this after loading positions to start receiving
    WebSocket price updates for the specified symbols.

    Args:
        subscribe_request: Request with list of OCC symbols

    Returns:
        SubscribePricesResponse with subscription status
    """
    try:
        logger.http_request("POST", "/api/positions/subscribe-prices")
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            logger.http_request("POST", "/api/positions/subscribe-prices", 200)
            return SubscribePricesResponse(
                status="error",
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file with your real API keys from https://alpaca.markets/"
            )

        await alpaca_service.start_price_streaming(subscribe_request.symbols)

        logger.http_request("POST", "/api/positions/subscribe-prices", 200)
        return SubscribePricesResponse(
            status="success",
            message=f"Subscribed to {len(subscribe_request.symbols)} symbols",
            symbols=subscribe_request.symbols
        )

    except Exception as e:
        logger.error(f"Failed to subscribe to prices: {e}")
        return SubscribePricesResponse(
            status="error",
            message=str(e)
        )


@app.post("/api/positions/subscribe-spot-prices", response_model=SubscribeSpotPricesResponse, tags=["Alpaca"])
async def subscribe_spot_prices(request: Request, subscribe_request: SubscribeSpotPricesRequest):
    """
    Subscribe to real-time spot (underlying stock) price updates.

    Call this after loading positions to start receiving
    WebSocket spot price updates for the underlying symbols.

    Args:
        subscribe_request: Request with list of stock symbols (e.g., ["SPY", "QQQ"])

    Returns:
        SubscribeSpotPricesResponse with subscription status
    """
    try:
        logger.http_request("POST", "/api/positions/subscribe-spot-prices")

        # Handle case where service failed to initialize
        if not hasattr(request.app.state, 'spot_price_service') or request.app.state.spot_price_service is None:
            logger.http_request("POST", "/api/positions/subscribe-spot-prices", 200)
            return SubscribeSpotPricesResponse(
                status="error",
                message="Spot Price service unavailable. Check server logs for initialization errors."
            )

        spot_price_service = get_spot_price_service(request.app)

        if not spot_price_service.is_configured:
            logger.http_request("POST", "/api/positions/subscribe-spot-prices", 200)
            return SubscribeSpotPricesResponse(
                status="error",
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file with your real API keys from https://alpaca.markets/"
            )

        await spot_price_service.start_spot_streaming(subscribe_request.symbols)

        logger.http_request("POST", "/api/positions/subscribe-spot-prices", 200)
        return SubscribeSpotPricesResponse(
            status="success",
            message=f"Subscribed to spot prices for {len(subscribe_request.symbols)} symbols",
            symbols=subscribe_request.symbols
        )

    except Exception as e:
        logger.error(f"Failed to subscribe to spot prices: {e}")
        return SubscribeSpotPricesResponse(
            status="error",
            message=str(e)
        )


@app.get("/api/positions/circuit-status", tags=["Alpaca"])
async def get_circuit_status(request: Request):
    """
    Get current circuit breaker status for Alpaca API.

    Returns:
        Dict with circuit state and configuration
    """
    try:
        logger.http_request("GET", "/api/positions/circuit-status")
        alpaca_service = get_alpaca_service(request.app)

        logger.http_request("GET", "/api/positions/circuit-status", 200)
        return {
            "status": "success",
            "circuit_state": alpaca_service.circuit_state,
            "is_configured": alpaca_service.is_configured,
        }

    except Exception as e:
        logger.error(f"Failed to get circuit status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/api/positions/{position_id}/close-strategy", response_model=CloseStrategyResponse, tags=["Alpaca"])
async def close_strategy(request: Request, position_id: str, close_request: CloseStrategyRequest):
    """
    Close an entire strategy (all legs) for a position.

    Submits orders to close all legs of the specified position.
    Uses market orders by default for immediate execution.

    Args:
        position_id: UUID of the position to close
        close_request: Request with order type settings

    Returns:
        CloseStrategyResponse with order results for each leg
    """
    try:
        logger.http_request("POST", f"/api/positions/{position_id}/close-strategy")
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            logger.http_request("POST", f"/api/positions/{position_id}/close-strategy", 200)
            return CloseStrategyResponse(
                status="error",
                position_id=position_id,
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file."
            )

        result = await alpaca_service.close_strategy(
            position_id=position_id,
            order_type=close_request.order_type
        )

        logger.http_request("POST", f"/api/positions/{position_id}/close-strategy", 200)
        return result

    except Exception as e:
        logger.error(f"Failed to close strategy {position_id}: {e}")
        return CloseStrategyResponse(
            status="error",
            position_id=position_id,
            message=str(e)
        )


@app.post("/api/positions/{position_id}/close-leg", response_model=CloseLegResponse, tags=["Alpaca"])
async def close_leg(request: Request, position_id: str, close_request: CloseLegRequest):
    """
    Close a single leg of a position.

    Submits an order to close the specified leg.
    Uses market orders by default for immediate execution.

    Args:
        position_id: UUID of the position containing the leg
        close_request: Request with leg_id and order type settings

    Returns:
        CloseLegResponse with order result
    """
    try:
        logger.http_request("POST", f"/api/positions/{position_id}/close-leg")
        alpaca_service = get_alpaca_service(request.app)

        if not alpaca_service.is_configured:
            logger.http_request("POST", f"/api/positions/{position_id}/close-leg", 200)
            return CloseLegResponse(
                status="error",
                message="Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file."
            )

        # Get position to find the leg
        position = await alpaca_service.get_position_by_id(position_id)
        if not position:
            logger.http_request("POST", f"/api/positions/{position_id}/close-leg", 200)
            return CloseLegResponse(
                status="error",
                message=f"Position not found: {position_id}"
            )

        # Find the leg
        leg = None
        for l in position.legs:
            if l.id == close_request.leg_id:
                leg = l
                break

        if not leg:
            logger.http_request("POST", f"/api/positions/{position_id}/close-leg", 200)
            return CloseLegResponse(
                status="error",
                message=f"Leg not found: {close_request.leg_id}"
            )

        # Close the leg
        result = await alpaca_service.close_leg(
            symbol=leg.symbol,
            quantity=leg.quantity,
            direction=leg.direction,
            order_type=close_request.order_type,
            limit_price=close_request.limit_price
        )

        if result.status == 'failed':
            logger.http_request("POST", f"/api/positions/{position_id}/close-leg", 200)
            return CloseLegResponse(
                status="error",
                order=result,
                message=result.error_message or "Failed to close leg"
            )

        logger.http_request("POST", f"/api/positions/{position_id}/close-leg", 200)
        return CloseLegResponse(
            status="success",
            order=result,
            message=f"Order submitted for {leg.symbol}"
        )

    except Exception as e:
        logger.error(f"Failed to close leg in position {position_id}: {e}")
        return CloseLegResponse(
            status="error",
            message=str(e)
        )


# ════════════════════════════════════════════════════════════════════════════════
# ALPACA AGENT CHAT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════


@app.post("/api/alpaca-agent/chat", tags=["Alpaca Agent"])
async def alpaca_agent_chat(request: Request, chat_request: AlpacaAgentChatRequest):
    """
    Chat with the Alpaca trading agent using natural language.

    Invokes the alpaca-mcp agent via Claude Code subprocess and streams
    the response back using Server-Sent Events (SSE).

    Args:
        chat_request: Request with user message

    Returns:
        StreamingResponse with SSE chunks
    """
    try:
        logger.http_request("POST", "/api/alpaca-agent/chat")
        logger.info(f"[ALPACA AGENT] Received chat request: {chat_request.message[:100]}...")

        # Check if service is available
        if not hasattr(request.app.state, 'alpaca_agent_service') or request.app.state.alpaca_agent_service is None:
            logger.error("[ALPACA AGENT] Service not initialized")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "error": "Alpaca Agent service not initialized. Backend may still be starting up."
                }
            )

        alpaca_agent_service: AlpacaAgentService = request.app.state.alpaca_agent_service
        logger.debug(f"[ALPACA AGENT] Service retrieved, working_dir={alpaca_agent_service.working_dir}")

        # Check if Claude SDK is available (claude_path is set to "sdk" when using SDK)
        if not alpaca_agent_service.claude_path:
            logger.error("[ALPACA AGENT] Claude SDK not available")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "error": "Claude Agent SDK not available. Check that claude-agent-sdk is installed."
                }
            )

        # Verify MCP config exists
        if not alpaca_agent_service.verify_mcp_config():
            logger.error("[ALPACA AGENT] MCP config not found")
            # Return JSON error response (not Pydantic model)
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": f"Alpaca MCP configuration not found at {alpaca_agent_service.mcp_config_path}. Ensure .mcp.json.alpaca exists in project root."
                }
            )

        logger.info("[ALPACA AGENT] MCP config verified, starting streaming response")

        # Stream response using SSE
        async def generate_sse():
            try:
                logger.debug("[ALPACA AGENT] Starting SSE generator")
                chunk_count = 0
                async for chunk in alpaca_agent_service.invoke_agent_streaming(chat_request.message):
                    chunk_count += 1
                    yield chunk
                logger.info(f"[ALPACA AGENT] SSE streaming complete, chunks={chunk_count}")
            except Exception as e:
                logger.error(f"[ALPACA AGENT] Streaming error: {e}", exc_info=True)
                # Use json.dumps to properly escape the error message
                error_chunk = json.dumps({"type": "error", "content": str(e)})
                yield f"data: {error_chunk}\n\n"
                yield "data: [DONE]\n\n"

        logger.http_request("POST", "/api/alpaca-agent/chat", 200)
        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"[ALPACA AGENT] Chat endpoint failed: {e}", exc_info=True)
        # Return JSON error response (not Pydantic model)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e)
            }
        )


# ════════════════════════════════════════════════════════════════════════════════
# GREEKS SNAPSHOT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════


@app.post("/api/greeks/snapshot", tags=["Greeks"])
async def trigger_greeks_snapshot(request: Request, underlying: str = "GLD"):
    """
    Manually trigger a Greeks snapshot for an underlying.

    Args:
        underlying: Underlying symbol (default: GLD)

    Returns:
        Snapshot result with count of persisted records
    """
    try:
        logger.http_request("POST", f"/api/greeks/snapshot?underlying={underlying}")
        service = get_greeks_snapshot_service(request.app)

        if not service.is_configured:
            return {
                "status": "error",
                "message": "Alpaca API not configured. Update ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file."
            }

        count = await service.fetch_and_persist_snapshots(
            underlying=underlying,
            snapshot_type="manual"
        )

        logger.http_request("POST", f"/api/greeks/snapshot?underlying={underlying}", 200)
        return {
            "status": "success",
            "underlying": underlying,
            "records": count,
            "message": f"Successfully persisted {count} Greeks snapshots for {underlying}"
        }

    except Exception as e:
        logger.error(f"Failed to trigger Greeks snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/greeks/latest", tags=["Greeks"])
async def get_latest_greeks(
    request: Request,
    underlying: str = "GLD",
    limit: int = 100
):
    """
    Get latest Greeks snapshots for an underlying.

    Args:
        underlying: Underlying symbol (default: GLD)
        limit: Maximum records to return (default: 100)

    Returns:
        List of latest Greeks snapshots
    """
    try:
        logger.http_request("GET", f"/api/greeks/latest?underlying={underlying}&limit={limit}")
        service = get_greeks_snapshot_service(request.app)

        snapshots = await service.get_latest_snapshots(underlying, limit)

        logger.http_request("GET", f"/api/greeks/latest?underlying={underlying}&limit={limit}", 200)
        return {
            "status": "success",
            "underlying": underlying,
            "snapshots": [s.model_dump() for s in snapshots],
            "count": len(snapshots)
        }

    except Exception as e:
        logger.error(f"Failed to get latest Greeks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/greeks/history/{symbol}", tags=["Greeks"])
async def get_greeks_history(
    request: Request,
    symbol: str,
    days: int = 30,
    limit: int = 1000
):
    """
    Get Greeks history for a specific option symbol.

    Args:
        symbol: OCC option symbol (e.g., GLD260117C00175000)
        days: Number of days of history (default: 30)
        limit: Maximum records to return (default: 1000)

    Returns:
        Greeks history ordered by snapshot_at ASC
    """
    try:
        logger.http_request("GET", f"/api/greeks/history/{symbol}?days={days}&limit={limit}")
        service = get_greeks_snapshot_service(request.app)

        history = await service.get_greeks_history(symbol, days, limit)

        logger.http_request("GET", f"/api/greeks/history/{symbol}?days={days}&limit={limit}", 200)
        return {
            "status": "success",
            "symbol": symbol,
            "history": [h.model_dump() for h in history],
            "count": len(history),
            "days": days
        }

    except Exception as e:
        logger.error(f"Failed to get Greeks history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════════
# TRADE HISTORY ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════


@app.get("/api/trades", response_model=TradeListResponse, tags=["Trades"])
async def get_trades(
    request: Request,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, all
    limit: int = 100,
    offset: int = 0
):
    """
    Get aggregated trade history.

    Returns trades grouped by trade_id with P&L calculations.
    Optionally filter by underlying symbol and/or status.

    Args:
        underlying: Filter by underlying symbol (e.g., "SPY")
        status: Filter by status ("open", "closed", or None for all)
        limit: Maximum number of trades to return
        offset: Offset for pagination

    Returns:
        TradeListResponse with list of trades
    """
    try:
        logger.http_request("GET", "/api/trades")
        sync_service = get_alpaca_sync_service(request.app)
        trades = await sync_service.get_trades(
            underlying=underlying,
            status=status,
            limit=limit,
            offset=offset
        )
        logger.http_request("GET", "/api/trades", 200)
        return TradeListResponse(
            status="success",
            trades=trades,
            total_count=len(trades)
        )
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        return TradeListResponse(status="error", message=str(e))


@app.get("/api/trades/detailed", response_model=DetailedTradeListResponse, tags=["Trades"])
async def get_detailed_trades(
    request: Request,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, partial, all
    limit: int = 50,
    offset: int = 0
):
    """
    Get detailed trade history with leg-level data.

    Returns trades with full leg breakdown including:
    - Open/close action and fill prices per leg
    - Per-leg P&L calculations
    - Aggregated summary per trade

    Args:
        underlying: Filter by underlying symbol (e.g., "SPY")
        status: Filter by status ("open", "closed", "partial", or "all")
        limit: Maximum number of trades to return (default 50)
        offset: Offset for pagination

    Returns:
        DetailedTradeListResponse with list of detailed trades
    """
    try:
        logger.http_request("GET", "/api/trades/detailed")
        sync_service = get_alpaca_sync_service(request.app)
        trades = await sync_service.get_detailed_trades(
            underlying=underlying,
            status=status,
            limit=limit,
            offset=offset
        )
        logger.http_request("GET", "/api/trades/detailed", 200)
        return DetailedTradeListResponse(
            status="success",
            trades=trades,
            total_count=len(trades)
        )
    except Exception as e:
        logger.error(f"Failed to get detailed trades: {e}")
        return DetailedTradeListResponse(status="error", message=str(e))


@app.get("/api/trade-stats", response_model=TradeStatsResponse, tags=["Trades"])
async def get_trade_stats(request: Request, status: Optional[str] = None):
    """
    Get trade summary statistics.

    Returns aggregated statistics including total P&L, win rate,
    and trade counts by status.

    Args:
        status: Filter by status ("open", "closed", or None for all)

    Returns:
        TradeStatsResponse with summary statistics
    """
    try:
        logger.http_request("GET", "/api/trade-stats")
        sync_service = get_alpaca_sync_service(request.app)
        stats = await sync_service.get_trade_stats(status=status)
        logger.http_request("GET", "/api/trade-stats", 200)
        return TradeStatsResponse(status="success", **stats)
    except Exception as e:
        logger.error(f"Failed to get trade stats: {e}")
        return TradeStatsResponse(status="error", message=str(e))


@app.post("/api/sync-orders", tags=["Trades"])
async def sync_orders(request: Request):
    """
    Trigger manual sync of orders from Alpaca.

    Fetches order history from Alpaca API and persists to database.
    Orders are automatically grouped into trades by trade_id.

    Returns:
        Dict with sync status and count of synced orders
    """
    try:
        logger.http_request("POST", "/api/sync-orders")
        sync_service = get_alpaca_sync_service(request.app)
        orders = await sync_service.sync_orders()
        logger.http_request("POST", "/api/sync-orders", 200)
        return {
            "status": "success",
            "synced_count": len(orders),
            "message": f"Synced {len(orders)} orders from Alpaca"
        }
    except Exception as e:
        logger.error(f"Failed to sync orders: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    # Display startup banner
    table = Table(
        title="Orchestrator 3 Stream Configuration",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Backend URL", config.BACKEND_URL)
    table.add_row("WebSocket URL", config.WEBSOCKET_URL)
    table.add_row("Database", "PostgreSQL (NeonDB)")

    console.print(table)

    # Run the server with config ports
    uvicorn.run(app, host=config.BACKEND_HOST, port=config.BACKEND_PORT)
