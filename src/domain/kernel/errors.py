"""
Domain error hierarchy for AutoReiv Agent Kernel.
"""

from typing import Optional


class KernelError(Exception):
    """Base exception for all agent kernel errors."""

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.agent_id = agent_id
        self.tool_name = tool_name

    def __str__(self) -> str:
        prefix = ""
        if self.agent_id:
            prefix += f"[{self.agent_id}] "
        if self.tool_name:
            prefix += f"(tool: {self.tool_name}) "
        return f"{prefix}{self.message}"


class AgentValidationError(KernelError):
    """Raised when an agent profile fails validation."""


class ToolPermissionDeniedError(KernelError):
    """Raised when an agent attempts to invoke a tool it is not authorized for."""


class ToolNotFoundError(KernelError):
    """Raised when a requested tool is not registered in the system."""


class TurnBudgetExceededError(KernelError):
    """Raised when an agent ReAct loop reaches its maximum turn limit."""


class CycleDetectedError(KernelError):
    """Raised when an agent gets stuck calling identical tools repeatedly."""


class ToolExecutionError(KernelError):
    """Raised when an underlying tool throws an unhandled exception during execution."""
