"""Integration test suite: Dogfood Factory Eight-Phase Tool Training Pipeline (CARD-373).

Tests the complete 8-phase tool creation pipeline:
intent_distill -> ground -> blueprint -> author -> scenario_verify -> verify -> optimize -> promote -> HITL approval.

Validates:
1. Sequential advancement across all 8 phases.
2. Clean Python AST validation without syntax errors on authored tool code.
3. Matt Pocock progressive disclosure standard and valid frontmatter on SKILL.md.
4. Tool entropy budget (<= 7 tools) mechanical enforcement via CapabilityLinter.
5. Zero checkout pollution on promote: writes strictly to user data packs/<slug>/.
6. Promoted agent profile stored with origin="custom", discoverable in AgentRegistry, and loadable by AgentKernel.
7. Verification battery catches AST and Python syntax failures before promotion.
8. Tool collision detection and HITL conflict guard.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.agent_training_factory.orchestrator import FactoryOrchestrator
from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import _format_standard_skill_runbook
from src.application.agent_training_factory.phases.promote import check_tool_collisions
from src.application.agent_training_factory.phases.verify import VerifyPhase
from src.application.agent_training_factory.registry import (
    PHASE_AUTHOR,
    PHASE_BLUEPRINT,
    PHASE_GROUND,
    PHASE_INTENT_DISTILL,
    PHASE_OPTIMIZE,
    PHASE_PROMOTE,
    PHASE_SCENARIO_VERIFY,
    PHASE_VERIFY,
    default_registry,
)
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.verification_battery import VerificationBatteryService
from src.application.skills.linter import CapabilityLinter, SkillContractCompiler
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role
from src.domain.kernel.models import AgentOrigin
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.domain.skills.contract import LintSeverity
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockDeterministicProvider:
    """Predictable mock LLM provider for integration testing."""

    provider_id: str = "default"

    def __init__(self, canned_responses: dict[str, str] | None = None) -> None:
        self.provider_id = "default"
        self.canned_responses = canned_responses or {}
        self.calls: List[Any] = []

    async def complete(self, request: Any) -> CompletionResponse:
        self.calls.append(request)
        user_text = ""
        for m in getattr(request, "messages", []):
            if m.role == Role.USER:
                user_text = str(m.content)

        for match_key, canned in self.canned_responses.items():
            if match_key.lower() in user_text.lower():
                return CompletionResponse(
                    model=getattr(request, "model", "default"),
                    message=ChatMessage(role=Role.ASSISTANT, content=canned),
                )

        return CompletionResponse(
            model=getattr(request, "model", "default"),
            message=ChatMessage(
                role=Role.ASSISTANT,
                content=json.dumps({"status": "ok", "action": "noop", "notes": "mock completion"}),
            ),
        )

    async def stream(self, request: Any):
        res = await self.complete(request)
        from src.domain.gateway.models import StreamChunk

        yield StreamChunk(content=res.text, is_finished=True)

    async def list_models(self) -> List[Any]:
        return []


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    """Isolated environment preventing any checkout pollution."""
    data_dir = tmp_path / "user_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "autoreiv.db"
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki_path))

    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    repo = FactoryPacketRepository(store)
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(wiki_path),
        skills_dir=str(data_dir / "skills"),
    )

    gateway = MultiProviderGateway()
    mock_provider = MockDeterministicProvider()
    gateway.register_provider(mock_provider)

    orchestrator = FactoryOrchestrator(
        repo=repo,
        registry=default_registry(),
        store=store,
        data_dir=data_dir,
        battery_service=VerificationBatteryService(),
        gateway=gateway,
    )

    return {
        "tmp_path": tmp_path,
        "data_dir": data_dir,
        "db_path": db_path,
        "wiki_path": wiki_path,
        "store": store,
        "repo": repo,
        "telemetry": telemetry,
        "registry": registry,
        "tool_reg": tool_reg,
        "gateway": gateway,
        "mock_provider": mock_provider,
        "orchestrator": orchestrator,
    }


@pytest.mark.asyncio
async def test_dogfood_factory_pipeline_e2e_eight_phases(test_env):
    """Dogfood full 8-phase factory pipeline from seed intent to final promoted agent pack [CARD-373]."""
    repo: FactoryPacketRepository = test_env["repo"]
    store: SQLiteStateStore = test_env["store"]
    data_dir: Path = test_env["data_dir"]
    orchestrator: FactoryOrchestrator = test_env["orchestrator"]
    registry: BuiltinAgentRegistry = test_env["registry"]
    tool_reg: ScopedToolRegistry = test_env["tool_reg"]
    gateway: MultiProviderGateway = test_env["gateway"]

    # 1. Seed a realistic network inspection capability job
    target_slug = "dns-inspector"
    seed_intent = "Query DNS records, inspect nameserver status, and measure query latency."
    objectives = [
        "Inspect local and remote DNS server configuration",
        "Resolve DNS A and CNAME records for target hosts",
        "Measure end-to-end DNS lookup latency",
    ]

    job = FactoryJob(
        id="fjob_dogfood_dns_01",
        target_agent_id=target_slug,
        session_id="sess_factory_dogfood",
        seed_intent=seed_intent,
        objectives=objectives,
        status="queued",
        current_node_id=PHASE_INTENT_DISTILL,
    )
    repo.save_job(job)

    # -------------------------------------------------------------
    # Phase 1: Intent Distill
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_GROUND

    distill_packets = repo.list_packets(job.id, node_id=PHASE_INTENT_DISTILL)
    assert len(distill_packets) >= 1
    distill_payload = distill_packets[-1].payload
    assert "answers" in distill_payload
    assert isinstance(distill_payload["answers"], dict)
    assert "duration_ms" in distill_payload
    assert distill_payload["duration_ms"] >= 0

    # -------------------------------------------------------------
    # Phase 2: Ground
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_BLUEPRINT

    ground_packets = repo.list_packets(job.id, node_id=PHASE_GROUND)
    assert len(ground_packets) >= 1
    ground_payload = ground_packets[-1].payload
    assert "manifest" in ground_payload or "medium" in ground_payload

    # -------------------------------------------------------------
    # Phase 3: Blueprint
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_AUTHOR

    blueprint_packets = repo.list_packets(job.id, node_id=PHASE_BLUEPRINT)
    assert len(blueprint_packets) >= 1
    blueprint_payload = blueprint_packets[-1].payload
    assert "blueprint" in blueprint_payload or "proposed_tool" in blueprint_payload

    # -------------------------------------------------------------
    # Phase 4: Author
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_SCENARIO_VERIFY

    author_packets = repo.list_packets(job.id, node_id=PHASE_AUTHOR)
    assert len(author_packets) >= 1
    author_payload = author_packets[-1].payload
    files_map: Dict[str, str] = author_payload.get("files_map", {})
    assert len(files_map) >= 2

    # Verify tool code is generated and compiles cleanly with AST
    tool_file_key = next((k for k in files_map if k.startswith("tools/") and k.endswith(".py")), None)
    assert tool_file_key is not None, f"Expected a tool .py file in authored files: {list(files_map.keys())}"
    tool_name = Path(tool_file_key).stem
    tool_code = files_map[tool_file_key]

    # AST validation: must parse with zero Python syntax errors
    parsed_ast = ast.parse(tool_code)
    assert isinstance(parsed_ast, ast.Module)

    # Check function signature, typed action, and standardized envelope
    assert f"def {tool_name}(" in tool_code
    assert "action: str" in tool_code
    assert "Args:" in tool_code
    assert "Returns:" in tool_code
    assert '"status": "success"' in tool_code

    # Verify skill runbook is generated and passes Matt Pocock progressive disclosure
    skill_file_key = "skills/dns_inspector/SKILL.md"
    assert skill_file_key in files_map, f"Expected {skill_file_key} in authored files"
    skill_md = files_map[skill_file_key]

    # Verify 5 Matt Pocock sections
    assert "## Overview" in skill_md
    assert "## Tools" in skill_md
    assert "## Order" in skill_md
    assert "## Pitfalls" in skill_md
    assert "## Done-when" in skill_md

    # Mechanical CapabilityLinter validation
    compiler = SkillContractCompiler()
    contract, violations = compiler.compile(skill_md, path=skill_file_key)
    assert contract is not None
    error_violations = [v for v in violations if v.severity == LintSeverity.ERROR]
    assert len(error_violations) == 0, f"Skill lint errors: {[v.message for v in error_violations]}"
    assert contract.verification is not None
    assert contract.verification.rule.strip() != ""

    # Tool entropy budget verification (<= 7 tools)
    assert len(contract.requires_tools) <= 6

    # -------------------------------------------------------------
    # Phase 5: Scenario Verify
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_VERIFY

    scenario_packets = repo.list_packets(job.id, node_id=PHASE_SCENARIO_VERIFY)
    assert len(scenario_packets) >= 1
    assert scenario_packets[-1].payload.get("passed") is True

    # -------------------------------------------------------------
    # Phase 6: Code Verify (Sandbox Verification Battery)
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_OPTIMIZE
    eval_runs = repo.list_eval_runs(job.id)
    assert len(eval_runs) >= 1
    latest_eval = eval_runs[-1]
    assert latest_eval.stage_1_functional is True
    assert latest_eval.stage_2_safety is True
    assert latest_eval.stage_3_idempotency is True
    assert latest_eval.stage_4_critic is True
    assert latest_eval.overall_passed is True

    # -------------------------------------------------------------
    # Phase 7: Optimize
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    assert stepped is True
    job = repo.get_job(job.id)
    assert job.status == "running"
    assert job.current_node_id == PHASE_PROMOTE

    opt_packets = repo.list_packets(job.id, node_id=PHASE_OPTIMIZE)
    assert len(opt_packets) >= 1
    assert opt_packets[-1].payload.get("critic_verdict") == "approved"

    # -------------------------------------------------------------
    # Phase 8: Promote (HITL Gate)
    # -------------------------------------------------------------
    stepped = await orchestrator.step_job(job.id)
    # At promote, orchestrator parks the job awaiting human approval
    assert stepped is False
    job = repo.get_job(job.id)
    assert job.status == "waiting_approval"
    assert job.current_node_id == PHASE_PROMOTE

    promote_packets = repo.list_packets(job.id, node_id=PHASE_PROMOTE)
    assert len(promote_packets) >= 1
    promote_payload = promote_packets[-1].payload
    assert promote_payload.get("awaiting") == "hitl_approval"
    assert promote_payload.get("has_collision") is False
    assert tool_name in promote_payload.get("proposed_tools", [])

    # -------------------------------------------------------------
    # HITL Promotion & Deployment via FastAPI Router
    # -------------------------------------------------------------
    app = create_app(
        state_store=store,
        agent_registry=registry,
        tool_registry=tool_reg,
        gateway_instance=gateway,
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        promote_resp = await client.post(
            f"/api/agent_training_factory/jobs/{job.id}/promote",
            json={"decision": "approved", "allow_overwrite": False},
        )
        assert promote_resp.status_code == 200, f"Promote failed: {promote_resp.text}"
        promote_data = promote_resp.json()
        assert promote_data["success"] is True
        assert promote_data["status"] == "done"
        assert promote_data["agent_id"] == target_slug

    # -------------------------------------------------------------
    # Verification: Pack Files Written Exclusively to User Data
    # -------------------------------------------------------------
    pack_dir = data_dir / "packs" / target_slug
    assert pack_dir.is_dir(), f"Pack directory {pack_dir} was not created in user data"

    pack_json_file = pack_dir / "pack.json"
    assert pack_json_file.is_file(), "pack.json missing in deployed pack"
    pack_data = json.loads(pack_json_file.read_text(encoding="utf-8"))
    assert pack_data["id"] == target_slug
    assert tool_name in pack_data.get("pack_tool_names", [])

    deployed_tool_file = pack_dir / "tools" / f"{tool_name}.py"
    assert deployed_tool_file.is_file(), "Tool python file missing in deployed pack"
    # AST validation on deployed file
    ast.parse(deployed_tool_file.read_text(encoding="utf-8"))

    deployed_skill_file = pack_dir / "skills" / "dns_inspector" / "SKILL.md"
    assert deployed_skill_file.is_file(), "SKILL.md missing in deployed pack"

    # CapabilityLinter inspection on deployed skill
    linter = CapabilityLinter()
    lint_contract, lint_violations = linter.lint_file(deployed_skill_file)
    assert lint_contract is not None
    errs = [v for v in lint_violations if v.severity == LintSeverity.ERROR]
    assert len(errs) == 0, f"Lint errors on deployed skill: {[v.message for v in errs]}"
    assert lint_contract.verification is not None

    # Checkout Working-Tree Hygiene Check (Zero Checkout Pollution)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    platform_packs_dir = repo_root / "platform-packs"
    assert not (platform_packs_dir / target_slug).exists(), "Pollution: custom agent written into platform-packs!"

    # -------------------------------------------------------------
    # Verification: Agent Profile Registration & Origin Tagging
    # -------------------------------------------------------------
    profile = registry.get_agent(target_slug)
    assert profile is not None, "Promoted agent was not registered in AgentRegistry"
    assert profile.id == target_slug
    assert profile.show_in_chat is True
    assert tool_name in profile.allowed_tool_names

    # Check origin tag: custom agent must be tagged with origin="custom" [CARD-367, CARD-373]
    assert profile.origin == AgentOrigin.CUSTOM or str(profile.origin) == "custom"
    assert profile.origin.value == "custom"

    # Also check persisted profile in SQLite store
    stored_profile = store.get_agent_profile(target_slug)
    assert stored_profile is not None
    assert stored_profile.origin.value == "custom"

    # -------------------------------------------------------------
    # Verification: AgentKernel Loads and Runs Promoted Custom Agent
    # -------------------------------------------------------------
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=test_env["telemetry"],
        data_dir=str(data_dir),
    )

    session = store.create_session(agent_id=profile.id, title="Test Custom Agent Dogfood")
    kernel_response = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="Inspect current DNS server status.",
    )
    assert kernel_response.role == Role.ASSISTANT
    assert kernel_response.content is not None


@pytest.mark.asyncio
async def test_factory_pipeline_catches_syntax_error_before_promote(test_env):
    """Dogfooding AST guard: Invalid Python tool syntax is caught by Verify phase and prevented from promoting [CARD-373]."""
    repo: FactoryPacketRepository = test_env["repo"]
    store: SQLiteStateStore = test_env["store"]
    data_dir: Path = test_env["data_dir"]
    gateway: MultiProviderGateway = test_env["gateway"]

    job = FactoryJob(
        id="fjob_dogfood_syntax_fail",
        target_agent_id="broken-agent",
        session_id="sess_factory_dogfood",
        seed_intent="Attempt to run invalid tool code with broken syntax.",
        objectives=["Syntax validation test"],
        status="running",
        current_node_id=PHASE_VERIFY,
    )
    repo.save_job(job)

    # Deliberately broken Python code with syntax error
    broken_code = """
def manage_broken_agent(action: str = "status"
    # Missing closing parenthesis and colon!
    return {"status": "error"
"""

    valid_skill = """---
name: broken_agent
description: "Test runbook"
---

# Broken Agent
## Overview
Test overview.
## Purpose & Scope
Test purpose.
## Tools
- Required Capabilities: `manage_broken_agent`
## Order
- Step 1: Check status
## Pitfalls
- None
## Done-when
- Operation verified.
"""

    author_packet = FactoryPacket(
        job_id=job.id,
        packet_type="work",
        sender_role="author",
        recipient_role="scenario_verify",
        node_id=PHASE_AUTHOR,
        payload={
            "tool_name": "manage_broken_agent",
            "files_map": {
                "tools/manage_broken_agent.py": broken_code,
                "skills/broken_agent/SKILL.md": valid_skill,
            },
        },
    )
    repo.save_packet(author_packet)

    # Verify ast.parse indeed fails on this tool code
    with pytest.raises(SyntaxError):
        ast.parse(broken_code)

    ctx = PhaseContext(
        job=job,
        repo=repo,
        store=store,
        data_dir=data_dir,
        gateway=gateway,
        battery=VerificationBatteryService(),
    )

    verify_phase = VerifyPhase()
    result = await verify_phase.run(ctx)

    # Verify phase MUST fail the run and flag the syntax error
    assert result.outcome == "fail"
    eval_runs = repo.list_eval_runs(job.id)
    assert len(eval_runs) >= 1
    latest = eval_runs[-1]
    assert latest.overall_passed is False

    # Check orchestrator transition logic: failure transitions back to author (rinse), never promote
    reg = default_registry()
    next_node = reg.next_phase(PHASE_VERIFY, outcome="fail")
    assert next_node == PHASE_AUTHOR, f"Expected rinse to {PHASE_AUTHOR}, got {next_node}"


@pytest.mark.asyncio
async def test_factory_pipeline_collision_detection_and_rejection(test_env):
    """Dogfooding tool collision: proposed tool conflicting with existing pack raises 409 [CARD-373, REQ-FACT-054]."""
    repo: FactoryPacketRepository = test_env["repo"]
    store: SQLiteStateStore = test_env["store"]
    data_dir: Path = test_env["data_dir"]
    registry: BuiltinAgentRegistry = test_env["registry"]
    tool_reg: ScopedToolRegistry = test_env["tool_reg"]

    # Pre-create an existing pack in user data
    existing_pack_dir = data_dir / "packs" / "existing-service"
    existing_tools_dir = existing_pack_dir / "tools"
    existing_tools_dir.mkdir(parents=True, exist_ok=True)
    (existing_tools_dir / "manage_existing_tool.py").write_text(
        "def manage_existing_tool(): pass\n", encoding="utf-8"
    )
    (existing_pack_dir / "pack.json").write_text(
        json.dumps({
            "id": "existing-service",
            "name": "Existing Service",
            "pack_tool_names": ["manage_existing_tool"],
            "allowed_tool_names": ["manage_existing_tool"],
        }),
        encoding="utf-8",
    )

    # Tool collision checker inspection
    collision_result = check_tool_collisions(
        target_agent_id="new-agent",
        proposed_tools=["manage_existing_tool"],
        data_dir=data_dir,
    )
    assert collision_result["has_collision"] is True
    assert "manage_existing_tool" in collision_result["conflicts"]

    # Create job in waiting_approval state proposing the colliding tool
    job = FactoryJob(
        id="fjob_dogfood_collision",
        target_agent_id="new-agent",
        session_id="sess_factory_dogfood",
        seed_intent="Attempting to author existing tool",
        status="waiting_approval",
        current_node_id=PHASE_PROMOTE,
    )
    repo.save_job(job)

    pkt = FactoryPacket(
        job_id=job.id,
        packet_type="work",
        sender_role="author",
        recipient_role="scenario_verify",
        node_id=PHASE_AUTHOR,
        payload={
            "tool_names": ["manage_existing_tool"],
            "files_map": {
                "tools/manage_existing_tool.py": "def manage_existing_tool(): return {'status': 'success'}\n",
                "skills/new_agent/SKILL.md": "---\nname: new_agent\n---\n## Done-when\n- done",
            },
        },
    )
    repo.save_packet(pkt)

    app = create_app(
        state_store=store,
        agent_registry=registry,
        tool_registry=tool_reg,
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default promote (allow_overwrite=False) MUST be rejected with HTTP 409
        resp = await client.post(
            f"/api/agent_training_factory/jobs/{job.id}/promote",
            json={"decision": "approved", "allow_overwrite": False},
        )
        assert resp.status_code == 409
        err_detail = resp.json().get("detail", {})
        assert "manage_existing_tool" in str(err_detail.get("conflicts", []))

        # Authorized overwrite (allow_overwrite=True) succeeds
        resp_overwrite = await client.post(
            f"/api/agent_training_factory/jobs/{job.id}/promote",
            json={"decision": "approved", "allow_overwrite": True},
        )
        assert resp_overwrite.status_code == 200
        assert resp_overwrite.json()["status"] == "done"


def test_factory_skill_runbook_linter_and_entropy_budget():
    """Verify SKILL.md generator complies with Matt Pocock standard, done-when contract, and entropy ceiling [CARD-373]."""
    compiler = SkillContractCompiler()

    # Case 1: Valid compliant skill runbook (<= 6 tools)
    compliant_md = _format_standard_skill_runbook(
        skill_id="database-health",
        skill_name="Database Health Inspection",
        seed_intent="Query database metrics and inspect connection pool health.",
        objectives=["Inspect connection counts", "Measure active queries"],
        agent_id="database-analyst",
        tool_names=["query_db_metrics", "check_pool_status"],
        skill_description="Operational runbook for inspecting database health.",
    )

    contract, violations = compiler.compile(compliant_md, path="test/SKILL.md")
    assert contract is not None
    errors = [v for v in violations if v.severity == LintSeverity.ERROR]
    assert len(errors) == 0, f"Expected zero errors, got: {[e.message for e in errors]}"
    assert contract.verification is not None
    assert len(contract.requires_tools) == 2

    # Case 2: Tool entropy ceiling exceeded (> 6 tools triggers CAP-001)
    bloated_md = _format_standard_skill_runbook(
        skill_id="bloated-skill",
        skill_name="Bloated Operational Skill",
        seed_intent="Too many tools violating the entropy budget.",
        objectives=["Over-tooling test"],
        agent_id="bloated-agent",
        tool_names=[f"tool_{i}" for i in range(8)],  # 8 tools > 6 allowed
        skill_description="Bloated skill with 8 tools.",
    )

    _, violations_bloated = compiler.compile(bloated_md, path="test/SKILL.md")
    cap_001 = [v for v in violations_bloated if v.rule_id == "CAP-001"]
    assert len(cap_001) >= 1, "Expected CAP-001 tool budget violation for 8 tools"

    # Case 3: Missing Done-when triggers CAP-002
    body_no_done_when = """---
name: missing_done_when
description: "Missing verification"
---

# Incomplete Runbook
## Overview
Some overview.
## Purpose
Some purpose.
## Tools
- None
## Order
- Step 1
## Pitfalls
- None
"""
    _, violations_missing_done = compiler.compile(body_no_done_when, path="test/SKILL.md")
    cap_002 = [v for v in violations_missing_done if v.rule_id == "CAP-002"]
    assert len(cap_002) >= 1, "Expected CAP-002 missing verification violation"
