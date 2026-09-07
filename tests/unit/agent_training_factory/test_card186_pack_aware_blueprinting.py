"""Unit tests for CARD-186: Pack-Aware Blueprinting, Modal Training Goal Input, and Skill Isolation."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_packs.service import AgentPackService
from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.blueprint import (
    BlueprintPhase,
    _load_existing_pack_info,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.orchestration.factory_packets import FactoryJob


def test_load_existing_pack_info(tmp_path: Path):
    pack_dir = tmp_path / "packs" / "finance"
    pack_dir.mkdir(parents=True)
    pack_json = {
        "id": "finance",
        "name": "Personal Finance Lead",
        "description": "Finance tracking and budgeting.",
        "storage_enabled": True,
        "storage": {"enabled": True, "type": "sqlite"},
        "skills": [
            {
                "id": "personal_finance",
                "name": "Personal Finance",
                "tools": ["log_transactions", "manage_budget"],
            }
        ],
        "pack_tool_names": ["log_transactions", "manage_budget"],
    }
    (pack_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    info = _load_existing_pack_info("finance", data_dir=tmp_path)
    assert info["exists"] is True
    assert info["name"] == "Personal Finance Lead"
    assert len(info["skills"]) == 1
    assert info["skills"][0]["id"] == "personal_finance"
    assert "log_transactions" in info["tools"]
    assert info["storage_enabled"] is True


@pytest.mark.asyncio
async def test_blueprint_phase_anchors_to_existing_skill_and_data_tool(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    pack_dir = tmp_path / "packs" / "finance"
    pack_dir.mkdir(parents=True)
    pack_json = {
        "id": "finance",
        "name": "Personal Finance Lead",
        "skills": [
            {
                "id": "personal_finance",
                "name": "Personal Finance",
                "tools": ["log_transactions"],
            }
        ],
        "pack_tool_names": ["log_transactions"],
        "storage_enabled": True,
    }
    (pack_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    job = FactoryJob(
        id="fjob_test_anchor",
        target_agent_id="finance",
        session_id="sess_test",
        seed_intent="Train forecasting and budgeting capabilities",
        objectives=["Analyze transactions and build monthly forecast"],
    )

    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(side_effect=Exception("LLM fallback test"))
    ctx = PhaseContext(job=job, repo=MagicMock(), gateway=mock_gateway, data_dir=tmp_path)

    phase = BlueprintPhase()
    result = await phase.run(ctx)

    assert result.outcome == "ok"
    bp = result.artifacts.get("blueprint", {})
    skills = bp.get("skills", [])
    tools = bp.get("tools", [])

    assert len(skills) >= 1
    # Must anchor to personal_finance, not a duplicate 'finance' skill
    assert skills[0]["id"] == "personal_finance"
    assert skills[0]["name"] == "Personal Finance"

    # Must generate an analytics tool, not generic manage_finance
    assert len(tools) >= 1
    tool_names = [t.get("name") for t in tools]
    assert any("analyze" in t or "forecast" in t or "analytics" in t for t in tool_names)
    assert not any(t == "manage_finance" for t in tool_names)


@pytest.mark.asyncio
async def test_blueprint_phase_guards_against_llm_duplicate_slug_skill(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    pack_dir = tmp_path / "packs" / "finance"
    pack_dir.mkdir(parents=True)
    pack_json = {
        "id": "finance",
        "name": "Personal Finance Lead",
        "skills": [{"id": "personal_finance", "name": "Personal Finance"}],
    }
    (pack_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    job = FactoryJob(
        id="fjob_test_guard",
        target_agent_id="finance",
        session_id="sess_test",
        seed_intent="Train finance",
        objectives=["Analytics"],
    )

    # LLM incorrectly returns skill id: 'finance'
    mock_llm_response = {
        "skills": [{"id": "finance", "name": "Finance Skill", "tools": ["analyze_finance"]}],
        "tools": [{"name": "analyze_finance", "target_entity": "finance", "actions": ["query"]}],
        "scenarios": ["Analyze works"],
    }
    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(return_value=MagicMock(content=json.dumps(mock_llm_response)))
    ctx = PhaseContext(job=job, repo=MagicMock(), gateway=mock_gateway, data_dir=tmp_path)

    phase = BlueprintPhase()
    result = await phase.run(ctx)

    bp = result.artifacts.get("blueprint", {})
    skills = bp.get("skills", [])
    # Guardrail should remap 'finance' to 'personal_finance'
    assert skills[0]["id"] == "personal_finance"


def test_private_pack_import_does_not_copy_skills_to_global_skills_dir(tmp_path: Path):
    data_dir = tmp_path / "data"
    packs_dir = data_dir / "packs" / "custom-specialist"
    skills_dir = data_dir / "skills"
    packs_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    # Pack has its own private skill
    pack_skill_dir = packs_dir / "skills" / "custom_skill"
    pack_skill_dir.mkdir(parents=True)
    (pack_skill_dir / "SKILL.md").write_text("---\nname: custom-skill\n---\n# Custom Skill\n", encoding="utf-8")

    pack_json = {
        "id": "custom-specialist",
        "name": "Custom Specialist",
        "skills": [{"id": "custom_skill", "name": "Custom Skill"}],
    }
    (packs_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    service = AgentPackService(data_dir=data_dir, agent_registry=MagicMock())
    service._import_folder(packs_dir)

    # Pack skill remains in pack directory
    assert (packs_dir / "skills" / "custom_skill" / "SKILL.md").is_file()
    # Pack skill MUST NOT leak to $DATA_DIR/skills/
    assert not (skills_dir / "custom_skill" / "SKILL.md").exists()


def test_user_catalog_resolves_and_saves_pack_scoped_skill(tmp_path: Path):
    data_dir = tmp_path / "data"
    packs_dir = data_dir / "packs" / "finance"
    skills_dir = data_dir / "skills"
    pack_skill_dir = packs_dir / "skills" / "personal_finance"
    pack_skill_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    skill_file = pack_skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: personal_finance\ndescription: Budgeting\n---\n# Personal Finance\nBody text", encoding="utf-8")

    catalog = UserSkillCatalog(skills_dir=skills_dir)
    # read_pack should find the pack-scoped skill
    res = catalog.read_pack("personal_finance")
    assert res["success"] is True
    assert res["manifest"]["name"] == "personal_finance"
    assert res["manifest"]["origin"] == "pack"

    # save_pack should update the pack-scoped file directly
    save_res = catalog.save_pack("personal_finance", name="Updated Finance", description="New desc", instructions="New body")
    assert save_res["success"] is True
    assert "New body" in skill_file.read_text(encoding="utf-8")
    # Must NOT have created in global skills_dir
    assert not (skills_dir / "personal_finance").exists()