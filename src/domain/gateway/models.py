"""
Domain models for AutoReiv LLM Gateway.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    id: str = Field(description="Unique tool call identifier")
    name: str = Field(description="Name of the tool/function to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Parsed arguments")


class ChatMessage(BaseModel):
    role: Role = Field(description="Role of the message author")
    content: str = Field(default="", description="Text content of the message")
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None, description="Optional tool calls initiated by assistant"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="Matching call ID if role is tool"
    )
    name: Optional[str] = Field(default=None, description="Optional name of author or tool")


class ToolDefinition(BaseModel):
    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema object for arguments"
    )


class CompletionRequest(BaseModel):
    model: str = Field(
        description="Target model identifier, e.g. 'ollama/qwen2.5:7b' or 'openai/gpt-4o-mini'"
    )
    messages: List[ChatMessage] = Field(description="List of conversation turns")
    tools: Optional[List[ToolDefinition]] = Field(default=None, description="Available tools")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = Field(default=False, description="Whether to stream response tokens")


class StreamChunk(BaseModel):
    content: str = Field(default="", description="Incremental text delta")
    reasoning_content: str = Field(
        default="", description="Incremental chain-of-thought reasoning delta (<think>)"
    )
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None, description="Tool call deltas if any"
    )
    finish_reason: Optional[str] = Field(default=None, description="Finish reason if stream ended")
    is_finished: bool = Field(default=False, description="True when the final chunk has arrived")


class CompletionResponse(BaseModel):
    model: str = Field(description="Model used for completion")
    message: ChatMessage = Field(description="Assistant response message")
    finish_reason: str = Field(default="stop", description="Completion stop reason")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token usage statistics")
