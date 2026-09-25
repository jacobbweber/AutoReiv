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
    SKILL_PROPOSAL = "skill_proposal"



class ToolCall(BaseModel):
    id: str = Field(description="Unique tool call identifier")
    name: str = Field(description="Name of the tool/function to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Parsed arguments")
    extra_content: Optional[Dict[str, Any]] = Field(default=None, description="Optional provider extra metadata such as Gemini thought_signature")


class ChatMessage(BaseModel):
    id: Optional[str] = Field(default=None, description="Optional persistent message ID")
    role: Role = Field(description="Role of the message author")
    content: str = Field(default="", description="Text content of the message")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Optional tool calls initiated by assistant")
    tool_call_id: Optional[str] = Field(default=None, description="Matching call ID if role is tool")
    name: Optional[str] = Field(default=None, description="Optional name of author or tool")
    images: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional multimodal image attachments")
    reasoning: Optional[str] = Field(
        default=None,
        description="Optional chain-of-thought / Thinking Process text for assistant turns [CARD-415]",
    )


class ToolDefinition(BaseModel):
    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema object for arguments")
    is_high_risk: bool = Field(default=False, description="Whether tool requires operator approval before execution")


class CompletionRequest(BaseModel):
    model: str = Field(description="Target model identifier, e.g. 'ollama/qwen2.5:7b' or 'openai/gpt-4o-mini'")
    messages: List[ChatMessage] = Field(description="List of conversation turns")
    tools: Optional[List[ToolDefinition]] = Field(default=None, description="Available tools")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    num_ctx: Optional[int] = Field(
        default=None,
        gt=0,
        description="Provider context window in tokens (Ollama num_ctx)",
    )
    stream: bool = Field(default=False, description="Whether to stream response tokens")
    think: Optional[bool] = Field(
        default=None,
        description="Ollama think mode. Nested complete() sets False so chain-of-thought cannot eat the read timeout.",
    )


class StreamChunk(BaseModel):
    content: str = Field(default="", description="Incremental text delta")
    reasoning_content: str = Field(default="", description="Incremental chain-of-thought reasoning delta (<think>)")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Tool call deltas if any")
    finish_reason: Optional[str] = Field(default=None, description="Finish reason if stream ended")
    is_finished: bool = Field(default=False, description="True when the final chunk has arrived")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token usage on the finished chunk")
    notice: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Operator notice from the gateway, e.g. an image dropped for a text-only model [CARD-475]",
    )


class CompletionResponse(BaseModel):
    model: str = Field(description="Model used for completion")
    message: ChatMessage = Field(description="Assistant response message")
    finish_reason: str = Field(default="stop", description="Completion stop reason")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token usage statistics")

    @property
    def text(self) -> str:
        """Extract text content from the completion assistant message."""
        return self.message.content if self.message else ""

