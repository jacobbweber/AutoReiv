"""
Settings Application Service [REQ-SETTINGS-002, REQ-SETTINGS-005].
Manages purpose matrix routing, agent customizations, and model hardware recommendations.
"""

from typing import Any, Dict, List, Optional

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.generation_semaphore import configure_process_generation_limit
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import (
    AgentCustomization,
    HardwareSpecs,
    ModelFitReport,
    ModelPurpose,
    ModelPurposeMatrix,
)
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class SettingsService:
    """
    Application service managing platform settings, model purpose matrix routing,
    runtime agent customizations, and hardware fit estimations.
    """

    def __init__(
        self,
        state_store: SQLiteStateStore,
        gateway: MultiProviderGateway,
        agent_registry: BuiltinAgentRegistry,
        hardware_calc: HardwareFitCalculator,
    ):
        self.state_store = state_store
        self.gateway = gateway
        self.agent_registry = agent_registry
        self.hardware_calc = hardware_calc

    def save_purpose_matrix(self, matrix: ModelPurposeMatrix) -> None:
        """Persist the purpose routing matrix to SQLite."""
        self.state_store.set_setting("purpose_matrix", matrix.model_dump())
        apply = getattr(self.gateway, "set_max_concurrent_generations", None)
        if callable(apply):
            apply(matrix.max_concurrent_generations)
        configure_process_generation_limit(matrix.max_concurrent_generations)

    def get_purpose_matrix(self) -> ModelPurposeMatrix:
        """Fetch the current purpose routing matrix."""
        data = self.state_store.get_setting("purpose_matrix")
        if not data:
            return ModelPurposeMatrix()
        return ModelPurposeMatrix.model_validate(data)

    def resolve_model_for_purpose(self, purpose: ModelPurpose) -> str:
        """Resolve model ID for a requested operational purpose."""
        matrix = self.get_purpose_matrix()
        return matrix.purposes.get(purpose, matrix.default_model)

    def save_agent_customization(self, customization: AgentCustomization) -> None:
        """Persist agent persona/tone/tool overrides."""
        self.state_store.save_agent_override(customization)

    def get_agent_customization(self, agent_id: str) -> Optional[AgentCustomization]:
        """Fetch agent overrides from SQLite."""
        return self.state_store.get_agent_override(agent_id)

    def get_effective_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """
        Merge default built-in profile with any active runtime overrides in SQLite.
        """
        base = self.agent_registry.get_profile(agent_id)
        if not base:
            return None

        override = self.get_agent_customization(agent_id)
        if not override:
            return base

        updates: Dict[str, Any] = {}
        if override.tone:
            try:
                updates["tone"] = AgentTone(override.tone)
            except ValueError:
                pass
        if override.system_prompt is not None:
            updates["system_prompt"] = override.system_prompt
        if override.model is not None:
            updates["model"] = override.model
        if override.allowed_tool_names is not None:
            updates["allowed_tool_names"] = override.allowed_tool_names
        if override.max_turns is not None:
            updates["max_turns"] = override.max_turns

        return base.model_copy(update=updates)

    async def get_model_recommendations(
        self,
        specs_override: Optional[HardwareSpecs] = None,
    ) -> List[ModelFitReport]:
        """
        Query discovered models and calculate hardware fit reports against host specs.
        """
        models = await self.gateway.list_models()
        specs = self.hardware_calc.get_hardware_specs(override=specs_override)
        reports: List[ModelFitReport] = []

        for m in models:
            param_size = m.param_size_b or 7.0
            rep = self.hardware_calc.evaluate_fit(
                param_size_b=param_size,
                quantization=m.quantization,
                specs=specs,
                model_id=m.id,
            )
            reports.append(rep)

        return reports
