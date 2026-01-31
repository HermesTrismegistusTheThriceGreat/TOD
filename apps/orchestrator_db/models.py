"""
Pydantic Database Models for Multi-Agent Orchestration

These models map directly to the PostgreSQL tables defined in schema_orchestrator.sql.
They provide:
- Automatic UUID handling (converts asyncpg UUID objects to Python UUID)
- Type safety and validation
- Automatic JSON serialization/deserialization
- Field validation and defaults

Usage:
    from models import Agent, OrchestratorAgent, Prompt, AgentLog, SystemLog

    # Automatically handles UUID conversion from database
    agent = Agent(**row_dict)
    print(agent.id)  # Works with both UUID objects and strings
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════
# ORCHESTRATOR_AGENT MODEL
# ═══════════════════════════════════════════════════════════


class OrchestratorAgent(BaseModel):
    """
    Singleton orchestrator agent that manages other agents.

    Maps to: orchestrator_agents table
    """
    id: UUID
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    status: Optional[Literal['idle', 'executing', 'waiting', 'blocked', 'complete']] = None
    working_dir: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    archived: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('total_cost', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        """Parse JSON string metadata to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# AGENT MODEL
# ═══════════════════════════════════════════════════════════


class Agent(BaseModel):
    """
    Agent registry and configuration for managed agents.

    Maps to: agents table
    """
    id: UUID
    orchestrator_agent_id: UUID
    name: str
    model: str
    system_prompt: Optional[str] = None
    working_dir: Optional[str] = None
    git_worktree: Optional[str] = None
    status: Optional[Literal['idle', 'executing', 'waiting', 'blocked', 'complete']] = None
    session_id: Optional[str] = None
    adw_id: Optional[str] = None
    adw_step: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    archived: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'orchestrator_agent_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('total_cost', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        """Parse JSON string metadata to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# PROMPT MODEL
# ═══════════════════════════════════════════════════════════


class Prompt(BaseModel):
    """
    Prompts sent to agents from engineers or orchestrator.

    Maps to: prompts table
    """
    id: UUID
    agent_id: Optional[UUID] = None
    task_slug: Optional[str] = None
    author: Literal['engineer', 'orchestrator_agent']
    prompt_text: str
    summary: Optional[str] = None
    timestamp: datetime
    session_id: Optional[str] = None

    @field_validator('id', 'agent_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# AGENT_LOG MODEL
# ═══════════════════════════════════════════════════════════


class AgentLog(BaseModel):
    """
    Unified event log for hooks and agent responses during task execution.

    Maps to: agent_logs table
    """
    id: UUID
    agent_id: UUID
    session_id: Optional[str] = None
    task_slug: Optional[str] = None
    adw_id: Optional[str] = None
    adw_step: Optional[str] = None
    entry_index: Optional[int] = None
    event_category: Literal['hook', 'response', 'adw_step']
    event_type: str
    content: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    timestamp: datetime

    @field_validator('id', 'agent_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('payload', mode='before')
    @classmethod
    def parse_payload(cls, v):
        """Parse JSON string payload to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# SYSTEM_LOG MODEL
# ═══════════════════════════════════════════════════════════


class SystemLog(BaseModel):
    """
    Application-level system logs (global application events only).

    For agent-related logs, use agent_logs table instead.

    Maps to: system_logs table
    """
    id: UUID
    file_path: Optional[str] = None
    adw_id: Optional[str] = None
    adw_step: Optional[str] = None
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
    message: str
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        """Parse JSON string metadata to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# ORCHESTRATOR_CHAT MODEL
# ═══════════════════════════════════════════════════════════


class OrchestratorChat(BaseModel):
    """
    Append-only conversation log capturing 3-way communication: user ↔ orchestrator ↔ agents.

    Maps to: orchestrator_chat table
    """
    id: UUID
    created_at: datetime
    updated_at: datetime
    orchestrator_agent_id: UUID
    sender_type: Literal['user', 'orchestrator', 'agent']
    receiver_type: Literal['user', 'orchestrator', 'agent']
    message: str
    summary: Optional[str] = None
    agent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('id', 'orchestrator_agent_id', 'agent_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        """Parse JSON string metadata to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# AI_DEVELOPER_WORKFLOW MODEL
# ═══════════════════════════════════════════════════════════


class AiDeveloperWorkflow(BaseModel):
    """
    Tracks AI Developer Workflow executions in the system.

    Maps to: ai_developer_workflows table
    """
    id: UUID
    orchestrator_agent_id: Optional[UUID] = None
    adw_name: str
    workflow_type: str
    description: Optional[str] = None
    status: Literal['pending', 'in_progress', 'completed', 'failed', 'cancelled'] = 'pending'
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_step: Optional[str] = None
    error_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'orchestrator_agent_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('input_data', 'output_data', 'metadata', mode='before')
    @classmethod
    def parse_jsonb(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# ALPACA_ORDER MODEL
# ═══════════════════════════════════════════════════════════


class AlpacaOrder(BaseModel):
    """
    Alpaca order history record with trade grouping.

    Maps to: alpaca_orders table
    """
    id: UUID
    alpaca_order_id: str
    client_order_id: Optional[str] = None

    # Trade grouping
    trade_id: UUID
    strategy_type: Optional[Literal['iron_condor', 'iron_butterfly', 'vertical_spread', 'strangle', 'straddle', 'single_leg', 'options']] = None
    leg_number: Optional[int] = None

    # Order details
    symbol: str
    underlying: str
    side: Literal['buy', 'sell']
    qty: float
    filled_qty: float = 0.0
    order_type: Optional[Literal['market', 'limit', 'stop', 'stop_limit']] = None
    time_in_force: Optional[Literal['day', 'gtc', 'opg', 'cls', 'ioc', 'fok']] = None

    # Pricing
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_avg_price: Optional[float] = None

    # Status
    status: str

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'trade_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('qty', 'filled_qty', 'limit_price', 'stop_price', 'filled_avg_price', 'strike_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# ALPACA_POSITION MODEL
# ═══════════════════════════════════════════════════════════


class AlpacaPosition(BaseModel):
    """
    Current open position from Alpaca.

    Maps to: alpaca_positions table
    """
    id: UUID
    trade_id: Optional[UUID] = None

    symbol: str
    underlying: str
    qty: float
    side: Optional[Literal['long', 'short']] = None

    # Pricing
    avg_entry_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None

    # P/L
    unrealized_pl: Optional[float] = None
    unrealized_plpc: Optional[float] = None
    unrealized_intraday_pl: Optional[float] = None
    unrealized_intraday_plpc: Optional[float] = None

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    is_open: bool = True
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'trade_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('qty', 'avg_entry_price', 'current_price', 'market_value', 'cost_basis',
                     'unrealized_pl', 'unrealized_plpc', 'unrealized_intraday_pl',
                     'unrealized_intraday_plpc', 'strike_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# OPTION_GREEKS_SNAPSHOT MODEL
# ═══════════════════════════════════════════════════════════


class OptionGreeksSnapshot(BaseModel):
    """
    Option Greeks snapshot record from Alpaca API.

    Maps to: option_greeks_snapshots table
    """
    id: UUID
    snapshot_at: datetime
    snapshot_type: Optional[Literal['london_session', 'us_session', 'asian_session', 'manual']] = None

    # Option identifiers
    symbol: str
    underlying: str
    expiry_date: date
    strike_price: float
    option_type: Literal['call', 'put']

    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None

    # Pricing
    underlying_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    mid_price: Optional[float] = None
    last_trade_price: Optional[float] = None

    # Volume
    volume: int = 0
    open_interest: int = 0

    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('strike_price', 'delta', 'gamma', 'theta', 'vega', 'rho',
                     'implied_volatility', 'underlying_price', 'bid_price',
                     'ask_price', 'mid_price', 'last_trade_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# USER ACCOUNTS AND CREDENTIALS MODELS
# ═══════════════════════════════════════════════════════════


class UserAccount(BaseModel):
    """
    User's trading account (linked to Better Auth user).

    Maps to: user_accounts table
    """
    id: UUID
    user_id: str  # TEXT in DB, maps to user.id from Better Auth
    account_name: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class UserCredential(BaseModel):
    """
    Encrypted API credentials for a user account.

    Maps to: user_credentials table
    Note: api_key and secret_key are stored encrypted in DB.
    Decryption happens via SQLAlchemy TypeDecorator (see user_models.py).
    """
    id: UUID
    user_account_id: UUID
    user_id: str  # Denormalized for RLS
    credential_type: str  # "alpaca", "polygon", etc.
    nickname: Optional[str] = None  # User-friendly label for credential
    api_key: str  # Note: This is the decrypted value after ORM retrieval
    secret_key: str  # Note: This is the decrypted value after ORM retrieval
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'user_account_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# BETTER AUTH MODELS
# ═══════════════════════════════════════════════════════════


class AuthUser(BaseModel):
    """
    Better Auth user model.

    Maps to: "user" table
    """
    id: str
    name: str
    email: str
    email_verified: bool = False
    image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthSession(BaseModel):
    """
    Better Auth session model.

    Maps to: session table
    """
    id: str
    user_id: str
    token: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# EXPORT PUBLIC API
# ═══════════════════════════════════════════════════════════

__all__ = [
    "OrchestratorAgent",
    "Agent",
    "Prompt",
    "AgentLog",
    "SystemLog",
    "OrchestratorChat",
    "AiDeveloperWorkflow",
    "AlpacaOrder",
    "AlpacaPosition",
    "OptionGreeksSnapshot",
    "UserAccount",
    "UserCredential",
    "AuthUser",
    "AuthSession",
]
