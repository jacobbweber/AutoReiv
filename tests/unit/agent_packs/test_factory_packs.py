"""
Unit tests for Core Platform Factory Pack Manifests [REQ-FACT-002].
"""

import pytest

from src.application.agent_packs.schema import (
    FACTORY_PACK_IDS,
    AgentPackManifest,
    is_visible_in_chat,
)
from src.infrastructure.data.resolver import repo_root


def factory_pack_dir(pack_id: str):
    return repo_root() / "platform-packs" / pack_id


@pytest.mark.parametrize("pack_id", ["conductor", "inspector", "coder", "sandbox_runner", "critic"])
def test_factory_pack_manifest_exists_and_valid(pack_id):
    p_dir = factory_pack_dir(pack_id)
    manifest_path = p_dir / "pack.json"
    assert manifest_path.is_file(), f"Missing platform pack manifest for {pack_id}"

    manifest = AgentPackManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.id == pack_id
    assert manifest.schema_version == "1.1"
    assert manifest.show_in_chat is False
    assert is_visible_in_chat(manifest) is False


def test_factory_pack_ids_constant():
    assert FACTORY_PACK_IDS == {"conductor", "inspector", "coder", "sandbox_runner", "critic"}


def test_conductor_pack_role_and_tools():
    manifest = AgentPackManifest.model_validate_json(
        (factory_pack_dir("conductor") / "pack.json").read_text(encoding="utf-8")
    )
    assert "conductor" in manifest.id
    assert "coordination" in manifest.allowed_skill or "handoff_to_agent" in manifest.pack_tool_names
    # Conductor must NOT have direct command execution or shell tools
    assert "cli_exec" not in manifest.pack_tool_names
    assert "execute_code" not in manifest.pack_tool_names


def test_inspector_pack_is_strictly_read_only():
    manifest = AgentPackManifest.model_validate_json(
        (factory_pack_dir("inspector") / "pack.json").read_text(encoding="utf-8")
    )
    # Inspector must not have write or destructive tools
    for tool_name in manifest.pack_tool_names:
        assert not tool_name.startswith("write_")
        assert not tool_name.startswith("delete_")
        assert tool_name != "cli_exec"


def test_coder_pack_scoped_authoring():
    manifest = AgentPackManifest.model_validate_json(
        (factory_pack_dir("coder") / "pack.json").read_text(encoding="utf-8")
    )
    assert manifest.id == "coder"
    assert "write_pack_tool" in manifest.pack_tool_names or "edit_pack_tool" in manifest.pack_tool_names


def test_sandbox_runner_pack_execution():
    manifest = AgentPackManifest.model_validate_json(
        (factory_pack_dir("sandbox_runner") / "pack.json").read_text(encoding="utf-8")
    )
    assert manifest.id == "sandbox_runner"
    assert "run_sandbox_command" in manifest.pack_tool_names or "read_sandbox_file" in manifest.pack_tool_names


def test_critic_pack_sre_auditing():
    manifest = AgentPackManifest.model_validate_json(
        (factory_pack_dir("critic") / "pack.json").read_text(encoding="utf-8")
    )
    assert manifest.id == "critic"
    assert "audit_tool_code" in manifest.pack_tool_names or "evaluate_test_run" in manifest.pack_tool_names
