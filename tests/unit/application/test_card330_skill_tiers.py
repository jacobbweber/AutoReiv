import pytest

from src.application.agent_packs.schema import (
    REQUIRED_PLATFORM_TOOLS,
    SkillTier,
    resolve_scoped_tools,
)
from src.application.agent_packs.service import (
    PlatformSkillMountError,
    validate_platform_skills,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile


def test_skill_tier_enum_and_constants():
    assert SkillTier.REQUIRED_PLATFORM == 'required_platform'
    assert SkillTier.OPTIONAL_PLATFORM == 'optional_platform'
    assert SkillTier.AGENT_PACK == 'agent_pack'

    # Check Required platform tools
    for tool in ('lookup_agents', 'handoff_to_agent', 'wiki_note_read', 'wiki_note_search', 'wiki_note_list'):
        assert tool in REQUIRED_PLATFORM_TOOLS


def test_required_platform_skills_automatically_granted():
    agent = AgentProfile(
        id='test_agent',
        name='Test Agent',
        description='A test agent',
        system_prompt='test',
        allowed_skill=[],
        pack_tool_names=[],
    )
    scoped = resolve_scoped_tools(agent)
    for tool in REQUIRED_PLATFORM_TOOLS:
        assert tool in scoped


def test_missing_required_platform_skill_raises_mount_error():
    # Only coordination tools present, missing wiki read
    incomplete_tools = {'lookup_agents', 'handoff_to_agent'}
    with pytest.raises(PlatformSkillMountError) as exc_info:
        validate_platform_skills(incomplete_tools)
    assert 'wiki_note_read' in str(exc_info.value) or 'wiki' in str(exc_info.value)


def test_optional_platform_skills_toggleable():
    agent_without = AgentProfile(
        id='agent_plain',
        name='Plain Agent',
        description='Plain',
        system_prompt='test',
        allowed_skill=[],
        pack_tool_names=[],
    )
    scoped_without = resolve_scoped_tools(agent_without)
    assert 'execute_code' not in scoped_without

    agent_with_sandbox = AgentProfile(
        id='agent_coder',
        name='Coder Agent',
        description='Coder',
        system_prompt='test',
        allowed_skill=['sandbox'],
        pack_tool_names=[],
    )
    scoped_with = resolve_scoped_tools(agent_with_sandbox)
    assert 'execute_code' in scoped_with


def test_pack_skills_strictly_isolated():
    agent_a = AgentProfile(
        id='agent_a',
        name='Agent A',
        description='A',
        system_prompt='test',
        allowed_skill=[],
        pack_tool_names=['special_tool_a'],
    )
    agent_b = AgentProfile(
        id='agent_b',
        name='Agent B',
        description='B',
        system_prompt='test',
        allowed_skill=[],
        pack_tool_names=['special_tool_b'],
    )
    scoped_a = resolve_scoped_tools(agent_a)
    scoped_b = resolve_scoped_tools(agent_b)

    assert 'special_tool_a' in scoped_a
    assert 'special_tool_a' not in scoped_b
    assert 'special_tool_b' in scoped_b
    assert 'special_tool_b' not in scoped_a


def test_tool_registry_scoping_prevents_prompt_bloat():
    registry = ScopedToolRegistry()

    # Register required tools
    for tool_name in REQUIRED_PLATFORM_TOOLS:
        registry.register_tool(tool_name, f'Tool {tool_name}', {}, lambda **k: None)

    # Register optional sandbox tool
    registry.register_tool('execute_code', 'Sandbox', {}, lambda **k: None)

    # Register pack tool
    registry.register_tool('pack_exclusive_tool', 'Pack', {}, lambda **k: None)

    # Register an unassigned foreign tool
    registry.register_tool('unassigned_foreign_tool', 'Foreign', {}, lambda **k: None)

    agent = AgentProfile(
        id='test_worker',
        name='Worker',
        description='Worker',
        system_prompt='test',
        allowed_skill=['sandbox'],
        pack_tool_names=['pack_exclusive_tool'],
    )

    tools_for_agent = registry.get_tools_for_agent(agent)
    tool_names = [t.name for t in tools_for_agent]

    # Must contain required tools
    for req in REQUIRED_PLATFORM_TOOLS:
        assert req in tool_names

    # Must contain ticked optional sandbox tool
    assert 'execute_code' in tool_names

    # Must contain own pack tool
    assert 'pack_exclusive_tool' in tool_names

    # Must NEVER contain foreign unassigned tool
    assert 'unassigned_foreign_tool' not in tool_names
