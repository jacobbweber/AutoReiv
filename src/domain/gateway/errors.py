"""
Domain error hierarchy for AutoReiv Gateway.
"""

from typing import Any, Dict, Optional


class GatewayError(Exception):
    """Base exception for all gateway-related errors."""

    def __init__(self, message: str, provider_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id

    def __str__(self) -> str:
        if self.provider_id:
            return f"[{self.provider_id}] {self.message}"
        return self.message


class GatewayValidationError(GatewayError):
    """Raised when request payload or configuration fails domain validation."""


class ProviderUnavailableError(GatewayError):
    """Raised when an LLM provider endpoint is unreachable or timing out."""


class AuthenticationError(GatewayError):
    """Raised when provider returns HTTP 401/403 credentials error."""


class ModelNotFoundError(GatewayError):
    """Raised when the requested model is not available or pulled on the provider."""


class RateLimitError(GatewayError):
    """Raised when the provider rate limit is exceeded."""


class AllProvidersFailedError(GatewayError):
    """Raised when all primary and fallback providers have failed."""

    def __init__(self, message: str, failures: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.failures = failures or {}

    def __str__(self) -> str:
        summary = ", ".join(f"{k}: {v}" for k, v in self.failures.items())
        return f"{self.message} (Failures: {summary})"
