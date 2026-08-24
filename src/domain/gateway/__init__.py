"""
Gateway Domain package.
"""

from src.domain.gateway.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    GatewayError,
    GatewayValidationError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
    ToolDefinition,
)

__all__ = [
    "Role",
    "ToolCall",
    "ChatMessage",
    "ToolDefinition",
    "CompletionRequest",
    "StreamChunk",
    "CompletionResponse",
    "GatewayError",
    "GatewayValidationError",
    "ProviderUnavailableError",
    "AuthenticationError",
    "ModelNotFoundError",
    "RateLimitError",
    "AllProvidersFailedError",
]
