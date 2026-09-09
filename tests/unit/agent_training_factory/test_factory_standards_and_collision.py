"""Tests for Skills/Tools standards, collision guard, and promote phase [CARD-197, REQ-FACT-052, REQ-FACT-053, REQ-FACT-054]."""

import json

import pytest

from src.application.agent_training_factory.phases.author import (
    _format_standard_skill_runbook,
    _is_stub_skill,
)
from src.application.agent_training_factory.phases.promote import (
    check_tool_collisions,
)
from src.application.orchestration.tool_synthesizer import ToolSynthesizer


def test_format_standard_skill_runbook_matt_pocock_headings():
    """Verify SKILL.md adheres to the 5 Matt Pocock sections [REQ-FACT-052]."""
    runbook = _format_standard_skill_runbook(
        skill_id="hyperv-vm-ops",
        skill_name="Hyper-V VM Operations",
        seed_intent="Manage Hyper-V VM lifecycle and checkpoints safely.",
        objectives=["Inspect VM status", "Create recovery checkpoint"],
        agent_id="hyperv-specialist",
        tool_names=["manage_hyperv_vm"],
        skill_description="Operational runbook for VM lifecycle.",
    )

    # Frontmatter check
    assert runbook.startswith("---")
    assert "name: hyperv-vm-ops" in runbook
    assert "description:" in runbook

    # 5 Mandatory Matt Pocock Sections
    assert "## Overview" in runbook
    assert "## Tools" in runbook
    assert "## Order" in runbook
    assert "## Pitfalls" in runbook
    assert "## Done-when" in runbook

    # Quality check: Not considered a stub
    assert not _is_stub_skill(
        skill_md=runbook,
        seed_intent="Manage Hyper-V VM lifecycle and checkpoints safely.",
        objectives=["Inspect VM status", "Create recovery checkpoint"],
        skill_id="hyperv-vm-ops",
    )


def test_tool_synthesizer_envelope_and_google_docstrings():
    """Verify synthesized Python tools return standard envelope and have Google-style docstrings [REQ-FACT-053]."""
    files = ToolSynthesizer.synthesize_tool(
        agent_id="database-analyst",
        seed_intent="Query SQLite metrics and generate revenue forecast reports.",
        objectives=["query database", "forecast revenue"],
        tool_name="analyze_database_analyst",
        skill_id="database-analytics",
    )

    tool_code = files["tools/analyze_database_analyst.py"]

    # Google-style docstring sections
    assert "Args:" in tool_code
    assert "Returns:" in tool_code
    assert "Raises:" in tool_code

    # Return envelope verification
    assert '"status": "success"' in tool_code
    assert '"data":' in tool_code
    assert '"error":' in tool_code

    # Execute synthesized tool in an isolated namespace to verify runtime behavior
    ns = {}
    exec(tool_code, ns)
    tool_fn = ns["analyze_database_analyst"]
    assert callable(tool_fn)

    # Test dry run
    dry_res = tool_fn(action="status", dry_run=True)
    assert dry_res["status"] == "success"
    assert "data" in dry_res
    assert dry_res["error"] is None
    # Backward compat
    assert dry_res["success"] is True

    # Test live execution
    live_res = tool_fn(action="query", name="monthly_sales")
    assert live_res["status"] == "success"
    assert live_res["data"]["name"] == "monthly_sales"
    assert live_res["error"] is None

    # Test invalid action raises ValueError
    with pytest.raises(ValueError):
        tool_fn(action="unsupported_dangerous_action")


def test_check_tool_collisions_duplicate_declarations():
    """Detect duplicate tool names declared within the proposed tools list [REQ-FACT-054]."""
    res = check_tool_collisions(
        target_agent_id="test-agent",
        proposed_tools=["tool_alpha", "tool_beta", "tool_alpha"],
    )
    assert res["has_collision"] is True
    assert "tool_alpha" in res["conflicts"]
    assert "tool_alpha" in res["duplicate_declarations"]


def test_check_tool_collisions_against_existing_pack_on_disk(tmp_path):
    """Detect tool name collision against target agent pack already on disk [REQ-FACT-054]."""
    pack_dir = tmp_path / "packs" / "finance-bot"
    pack_dir.mkdir(parents=True)
    (pack_dir / "pack.json").write_text(
        json.dumps({
            "id": "finance-bot",
            "name": "Finance Bot",
            "pack_tool_names": ["query_transactions", "export_ledger"],
        }),
        encoding="utf-8",
    )

    # Colliding with query_transactions
    res = check_tool_collisions(
        target_agent_id="finance-bot",
        proposed_tools=["query_transactions", "calculate_taxes"],
        data_dir=tmp_path,
    )
    assert res["has_collision"] is True
    assert "query_transactions" in res["conflicts"]
    assert "query_transactions" in res["target_pack_conflicts"]

    # Non-colliding tools
    res_clean = check_tool_collisions(
        target_agent_id="finance-bot",
        proposed_tools=["calculate_taxes", "forecast_spend"],
        data_dir=tmp_path,
    )
    assert res_clean["has_collision"] is False
    assert len(res_clean["conflicts"]) == 0
