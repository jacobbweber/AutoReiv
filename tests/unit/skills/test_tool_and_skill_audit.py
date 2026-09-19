"""
Tool and Skill Registry Audit & Regression Suite [CARD-376].
Verifies that all active tools are hooked up, schemas are valid, and dead/vestigial tools remain pruned.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_packs.schema import PLATFORM_SKILL_TOOLS
from src.application.skills.linter import CapabilityLinter
from src.application.skills.manifest import BUILTIN_TOOL_GROUPS
from src.infrastructure.agents.registry import BuiltinAgentRegistry


@pytest.fixture
def bootstrapped_tools():
    store = MagicMock()
    store.get_all_installed_agent_ids.return_value = []
    store.list_agent_profiles.return_value = []
    store.get_agent_override.return_value = None
    store.get_agent_profile.return_value = None
    telemetry = MagicMock()
    _reg, tools = BuiltinAgentRegistry.bootstrap(store=store, telemetry=telemetry, wiki_root="scratch/test_wiki")
    return tools


def test_pruned_tools_not_in_registry(bootstrapped_tools):
    """Verify dead, vestigial, or unhooked tools are not registered on master tool registry [CARD-376]."""
    pruned_banned = [
        "delegate_to_fleet_agent",
        "lookup_homelab_docs",
        "manage_opentofu_hyperv",
        "check_port",
    ]
    registered = set(bootstrapped_tools._tools.keys())
    for tool_name in pruned_banned:
        assert tool_name not in registered, f"Pruned tool '{tool_name}' was unexpectedly re-registered."


def test_builtin_tool_groups_all_registered(bootstrapped_tools):
    """Verify every tool declared in BUILTIN_TOOL_GROUPS is registered on master tool registry [CARD-376]."""
    registered = set(bootstrapped_tools._tools.keys())
    for group in BUILTIN_TOOL_GROUPS:
        for tool_name in group.tool_names:
            assert tool_name in registered, (
                f"Tool '{tool_name}' from manifest group '{group.id}' is missing from master tool registry."
            )


def test_platform_skill_tools_all_registered(bootstrapped_tools):
    """Verify every tool mapped in PLATFORM_SKILL_TOOLS is registered on master tool registry [CARD-376]."""
    registered = set(bootstrapped_tools._tools.keys())
    for skill_id, tool_list in PLATFORM_SKILL_TOOLS.items():
        for tool_name in tool_list:
            assert tool_name in registered, (
                f"Tool '{tool_name}' in PLATFORM_SKILL_TOOLS['{skill_id}'] is missing from master tool registry."
            )


def test_all_registered_tools_have_valid_schemas_and_callables(bootstrapped_tools):
    """Verify all registered tools have descriptions, parameters, and valid handlers [CARD-376]."""
    for name, tool_reg in bootstrapped_tools._tools.items():
        assert name.strip() == name, f"Tool name '{name}' has leading/trailing whitespace."
        assert tool_reg.definition.description, f"Tool '{name}' is missing description."
        params = tool_reg.definition.parameters
        assert isinstance(params, dict), f"Tool '{name}' parameters must be a dictionary schema."
        assert params.get("type") == "object", f"Tool '{name}' parameters must have type 'object'."
        assert callable(tool_reg.handler), f"Tool '{name}' handler is not callable."


def test_all_platform_and_seed_skill_runbooks_pass_linter():
    """Verify every SKILL.md in platform packs and seeds passes CapabilityLinter cleanly [CARD-376]."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    platform_skills = list((repo_root / "platform-packs" / "autoreiv" / "skills").glob("*/SKILL.md"))
    seed_skills = list((repo_root / "src" / "infrastructure" / "skills" / "seeds").glob("*/SKILL.md"))
    assert len(platform_skills) >= 10, "Expected at least 10 platform skills"
    assert len(seed_skills) >= 10, "Expected at least 10 seed skills"

    linter = CapabilityLinter()
    for skill_file in platform_skills + seed_skills:
        contract, violations = linter.lint_file(skill_file)
        errors = [v for v in violations if v.severity.value == "error"]
        assert len(errors) == 0, (
            f"Skill '{skill_file.parent.name}' at {skill_file} has lint errors: "
            f"{[f'{v.rule_id}: {v.message}' for v in errors]}"
        )
