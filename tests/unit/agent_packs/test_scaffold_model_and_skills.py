
import pytest

from src.application.agent_packs.service import AgentPackService
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def isolated_service(tmp_path):
    data_dir = tmp_path / "data"
    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    tool_reg = ScopedToolRegistry()
    registry = BuiltinAgentRegistry(state_store=store, master_tool_registry=tool_reg)
    svc = AgentPackService(data_dir=data_dir, agent_registry=registry, store=store)
    return svc, store, registry


def test_kernel_resolves_agent_configured_provider_and_model(isolated_service):
    _, store, registry = isolated_service
    store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "gemini",
            "default_model_id": "gemini-2.5-flash",
        },
    )

    agent = AgentProfile(
        id="nexus-coder",
        name="Nexus Coder",
        description="Coder",
        system_prompt="Coding agent",
        provider="gemini",
        model="gemini-2.5-pro",
    )

    from src.application.gateway.gateway_service import MultiProviderGateway
    from src.application.telemetry.collector import TelemetryCollector

    gw = MultiProviderGateway(default_provider_id="gemini")
    telemetry = TelemetryCollector(store=store)
    kernel = AgentKernel(
        state_store=store,
        tool_registry=ScopedToolRegistry(),
        gateway=gw,
        telemetry=telemetry,
    )
    resolved = kernel._resolve_model(agent)
    assert resolved == "gemini/gemini-2.5-pro"
