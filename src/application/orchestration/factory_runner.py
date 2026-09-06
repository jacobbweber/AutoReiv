"""Compatibility shim — FactoryRunner now aliases FactoryOrchestrator (CARD-171).

Prefer importing from src.application.agent_training_factory.
"""

from src.application.agent_training_factory.orchestrator import FactoryOrchestrator, FactoryRunner

__all__ = ["FactoryOrchestrator", "FactoryRunner"]
