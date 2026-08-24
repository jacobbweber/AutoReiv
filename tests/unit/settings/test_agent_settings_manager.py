"""
Unit tests for Purpose Matrix & Agent Settings Manager [REQ-SETTINGS-002, REQ-SETTINGS-005].
"""

import httpx
import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.telemetry.collector import TelemetryCollector
from src.domain.kernel.models import AgentTone
from src.domain.settings.models import (
    AgentCustomization,
    FitStatus,
    HardwareSpecs,
    ModelPurpose,
    ModelPurposeMatrix,
)
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def service(store):
    collector = TelemetryCollector(store)
    agent_reg, _ = BuiltinAgentRegistry.bootstrap(store, collector)

    ollama_tags = {
        "models": [
            {
                "name": "qwen2.5:32b",
                "model": "qwen2.5:32b",
                "details": {"family": "qwen2", "parameter_size": "32.5B", "quantization_level": "Q4_K_M"},
            },
            {
                "name": "llama3.2:1b",
                "model": "llama3.2:1b",
                "details": {"family": "llama", "parameter_size": "1.2B", "quantization_level": "Q4_K_M"},
            },
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_tags))
    client = httpx.AsyncClient(transport=transport)
    adapter = OllamaProviderAdapter(client=client)

    gateway = MultiProviderGateway()
    gateway.register_provider(adapter)

    calc = HardwareFitCalculator()

    return SettingsService(
        state_store=store,
        gateway=gateway,
        agent_registry=agent_reg,
        hardware_calc=calc,
    )


def test_purpose_matrix_resolution(service):
    matrix = ModelPurposeMatrix(
        default_model="ollama/qwen2.5:7b",
        purposes={
            ModelPurpose.REASONING: "ollama/qwen2.5:32b",
            ModelPurpose.FAST: "ollama/llama3.2:1b",
        },
    )
    service.save_purpose_matrix(matrix)

    # Specific purpose mapped
    assert service.resolve_model_for_purpose(ModelPurpose.REASONING) == "ollama/qwen2.5:32b"
    assert service.resolve_model_for_purpose(ModelPurpose.FAST) == "ollama/llama3.2:1b"

    # Unmapped purpose falls back to default_model
    assert service.resolve_model_for_purpose(ModelPurpose.TASK_EXECUTION) == "ollama/qwen2.5:7b"


def test_effective_agent_profile_with_overrides(service):
    # 1. Base profile check
    base = service.get_effective_agent_profile("general-assistant")
    assert base is not None
    assert base.tone == AgentTone.FRIENDLY

    # 2. Save customization
    override = AgentCustomization(
        agent_id="general-assistant",
        tone="socratic",
        system_prompt="Custom system prompt for Socratic brief.",
        model="ollama/qwen2.5:32b",
        max_turns=20,
    )
    service.save_agent_customization(override)

    # 3. Check effective profile reflects customization
    customized = service.get_effective_agent_profile("general-assistant")
    assert customized is not None
    assert customized.tone == AgentTone.SOCRATIC
    assert customized.system_prompt == "Custom system prompt for Socratic brief."
    assert customized.model == "ollama/qwen2.5:32b"
    assert customized.max_turns == 20


@pytest.mark.asyncio
async def test_get_model_recommendations_on_nimo_specs(service):
    nimo_specs = HardwareSpecs(
        total_ram_gb=128.0,
        available_ram_gb=115.0,
        cpu_cores=16,
        is_unified_memory=True,
    )

    recs = await service.get_model_recommendations(specs_override=nimo_specs)
    assert len(recs) == 2

    # Both 32B and 1B should be optimal on 128GB Nimo PC
    m32b = next(r for r in recs if "32b" in r.model_id)
    assert m32b.fit_status == FitStatus.OPTIMAL
    assert m32b.recommendation_score >= 90.0
