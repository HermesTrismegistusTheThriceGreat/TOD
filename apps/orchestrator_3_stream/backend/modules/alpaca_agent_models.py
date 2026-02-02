#!/usr/bin/env python3
"""
Pydantic models for Alpaca Agent Chat feature.

This module defines the request/response models for the natural language trading interface
that allows users to interact with trading agents via chat. Models support both synchronous
HTTP responses and Server-Sent Events (SSE) streaming.

Models:
- AlpacaAgentChatRequest: User chat message input
- AlpacaAgentChatResponse: Synchronous chat response
- AlpacaAgentStreamChunk: SSE streaming chunk for real-time agent output
"""

from typing import Optional, Literal, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ═══════════════════════════════════════════════════════════
# CHAT REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class AlpacaAgentChatRequest(BaseModel):
    """
    Request model for sending a message to the Alpaca trading agent.

    The user's natural language message is processed by the agent, which can
    execute trading operations, query account information, or provide market analysis.

    Attributes:
        message: User's natural language input (e.g., "What are my current positions?")
        credential_id: UUID of the credential to use for this trading operation
    """
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(
        ...,
        description="User's natural language message to the trading agent",
        min_length=1
    )

    credential_id: str = Field(
        ...,
        description="UUID of the credential to use for this trading operation"
    )

    @field_validator('message')
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        """Validate message is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()

    @field_validator('credential_id')
    @classmethod
    def validate_credential_id(cls, v: str) -> str:
        """Validate credential_id is a valid UUID."""
        try:
            UUID(v)
            return v
        except ValueError:
            raise ValueError("credential_id must be a valid UUID")


class AlpacaAgentChatResponse(BaseModel):
    """
    Synchronous response model for chat requests.

    Used when the full agent response is returned in a single HTTP response
    (non-streaming mode).

    Attributes:
        status: Response status - "success" for successful agent interaction, "error" for failures
        response: The agent's complete response text (None if error occurred)
        error: Error message describing what went wrong (None if successful)
    """
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error'] = Field(
        ...,
        description="Response status indicating success or failure"
    )
    response: Optional[str] = Field(
        None,
        description="Agent's complete response text (present on success)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if request failed (present on error)"
    )

    @field_validator('response', 'error')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from response and error fields, converting empty strings to None."""
        if v is not None and isinstance(v, str):
            return v.strip() if v.strip() else None
        return v

    @model_validator(mode='after')
    def validate_status_field_consistency(self):
        """Validate that response and error fields are consistent with status.

        - When status='success': response must be present, error must be None
        - When status='error': error must be present, response must be None
        """
        if self.status == 'success':
            if not self.response:
                raise ValueError("response is required when status is 'success'")
            if self.error is not None:
                raise ValueError("error must be None when status is 'success'")
        elif self.status == 'error':
            if not self.error:
                raise ValueError("error is required when status is 'error'")
            if self.response is not None:
                raise ValueError("response must be None when status is 'error'")
        return self


# ═══════════════════════════════════════════════════════════
# SSE STREAMING MODELS
# ═══════════════════════════════════════════════════════════

class AlpacaAgentStreamChunk(BaseModel):
    """
    Server-Sent Event (SSE) streaming chunk for real-time agent output.

    The agent's processing is streamed to the client in real-time via SSE,
    allowing the UI to display thinking processes, tool usage, and incremental
    text responses as they occur.

    Chunk Types:
        - "thinking": Agent's internal reasoning/planning (from ThinkingBlock)
        - "tool_use": Agent is invoking a tool/function (from ToolUseBlock)
        - "text": Partial text response chunk (streaming text generation)
        - "content": Complete content block from agent response
        - "done": Final chunk indicating stream completion
        - "error": Error occurred during processing

    Attributes:
        type: Chunk type identifier (see Chunk Types above)
        content: Text content of the chunk (for text/thinking/content/error types)
        tool_name: Name of the tool being invoked (for tool_use type only)
        tool_input: Input parameters for the tool (for tool_use type only)
    """
    model_config = ConfigDict(from_attributes=True)

    type: Literal['thinking', 'tool_use', 'text', 'content', 'done', 'error'] = Field(
        ...,
        description="Type of stream chunk being sent"
    )
    content: Optional[str] = Field(
        None,
        description="Text content for text/thinking/content/error chunks"
    )
    tool_name: Optional[str] = Field(
        None,
        description="Name of tool being invoked (only for tool_use chunks)"
    )
    tool_input: Optional[Dict[str, Any]] = Field(
        None,
        description="Tool input parameters as key-value pairs (only for tool_use chunks)"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Allow empty strings for content (some chunks may have empty content)."""
        return v

    @model_validator(mode='after')
    def validate_chunk_requirements(self):
        """Validate that required fields are present based on chunk type."""
        if self.type == 'tool_use' and not self.tool_name:
            raise ValueError("tool_name is required for tool_use chunk type")
        return self


# ═══════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════

__all__ = [
    "AlpacaAgentChatRequest",
    "AlpacaAgentChatResponse",
    "AlpacaAgentStreamChunk",
]
