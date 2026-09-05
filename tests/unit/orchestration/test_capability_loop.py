"""
Unit and integration tests for Conditional Graph Orchestrator & The Rinse Loop [REQ-FACT-004, REQ-FACT-010, REQ-FACT-011, REQ-FACT-015].
"""

from pathlib import Path

import pytest

from src.application.orchestration.capability_graph import (
    AgentSplitPolicy,
    CapabilityGraphEngine,
    ToolConsolidationGate,
    UserPackFinalizer,
)
from src.domain.orchestration.factory_packets import FactoryJob
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    return s


@pytest.fixture
def factory_repo(store):
    return FactoryPacketRepository(store)


def test_capability_graph_engine_transitions(factory_repo):
    engine = CapabilityGraphEngine(repo=factory_repo)
    job = FactoryJob(
        id="fjob_100",
        target_agent_id="test-agent",
        session_id="sess_100",
        seed_intent="Create server admin",
        current_node_id="discovery_probe",
    )
    factory_repo.save_job(job)

    # 1. Advance discovery_probe with "ok" -> architecture_blueprint
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "architecture_blueprint"

    # 2. Advance architecture_blueprint with "ok" -> attempt_node
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "attempt_node"

    # 3. From attempt_node, capability gap encountered -> conduct_node
    next_node = engine.advance(job_id="fjob_100", outcome="need_capability")
    assert next_node == "conduct_node"

    # 4. From conduct_node -> coder_node
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "coder_node"

    # 5. From coder_node -> sandbox_battery_node
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "sandbox_battery_node"

    # 6. Battery passed -> attempt_node
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "attempt_node"

    # 7. All objectives pass -> critic_signoff_node -> hitl_deploy_gate_node
    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "critic_signoff_node"

    next_node = engine.advance(job_id="fjob_100", outcome="ok")
    assert next_node == "hitl_deploy_gate_node"


def test_tool_consolidation_gate_heuristics():
    gate = ToolConsolidationGate()

    # Fragmented verbs targeting the same resource
    proposed_tools = [
        {"name": "start_service", "target_entity": "system_service", "verb": "start"},
        {"name": "stop_service", "target_entity": "system_service", "verb": "stop"},
        {"name": "restart_service", "target_entity": "system_service", "verb": "restart"},
        {"name": "status_service", "target_entity": "system_service", "verb": "status"},
    ]

    recommendation = gate.evaluate(proposed_tools)
    assert recommendation["should_consolidate"] is True
    assert "system_service" in recommendation["target_entity"]
    assert recommendation["suggested_tool_name"] == "manage_system_service"
    assert set(recommendation["actions"]) == {"start", "stop", "restart", "status"}


def test_agent_split_policy_detects_domain_sprawl():
    policy = AgentSplitPolicy()

    # Agent with tools crossing 2 distinct operational domains
    tools = [
        {"name": "manage_game_server", "domain": "game_hosting"},
        {"name": "edit_game_settings", "domain": "game_hosting"},
        {"name": "backup_game_saves", "domain": "game_hosting"},
        {"name": "configure_iptables_firewall", "domain": "network_security"},
        {"name": "manage_wireguard_vpn", "domain": "network_security"},
        {"name": "inspect_network_routes", "domain": "network_security"},
    ]

    result = policy.evaluate_split(agent_id="game-agent", tools=tools)
    assert result["should_split"] is True
    assert len(result["split_proposals"]) == 2
    domains = {p["domain"] for p in result["split_proposals"]}
    assert domains == {"game_hosting", "network_security"}
    assert "handoff_to_agent" in result["recommended_contract"]


def test_user_pack_finalizer_strictly_writes_to_user_packs(tmp_path):
    finalizer = UserPackFinalizer(data_dir=str(tmp_path))

    manifest_data = {
        "id": "game-agent",
        "name": "Game Agent",
        "description": "Dedicated Palworld server management agent",
        "system_prompt": "Manage Palworld game server.",
        "tone": "concise",
        "pack_tool_names": ["manage_palworld_server"],
        "show_in_chat": True,
    }
    tool_files = {
        "tools/manage_palworld_server.py": "def manage_palworld_server(action: str): return {'success': True}",
        "skills/game_ops/SKILL.md": "# Palworld Operations Runbook\n\nRunbooks for managing palworld.\n",
    }

    pack_dir = finalizer.finalize_pack(
        agent_id="game-agent",
        manifest_data=manifest_data,
        files=tool_files,
    )

    pack_path = Path(pack_dir)
    assert pack_path.is_dir()
    assert (pack_path / "pack.json").is_file()
    assert (pack_path / "tools" / "manage_palworld_server.py").is_file()
    assert (pack_path / "skills" / "game_ops" / "SKILL.md").is_file()

    # Verify content
    tool_content = (pack_path / "tools" / "manage_palworld_server.py").read_text(encoding="utf-8")
    assert "def manage_palworld_server" in tool_content
    assert str(pack_path).startswith(str(tmp_path))
