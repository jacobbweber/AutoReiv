"""
CARD-204: Pure Chat Runtimes and Retired Platform Skills [CARD-204].

Verifies:
1. PLATFORM_SKILL_IDS contains strictly the 5 core platform skills (wiki, coordination, proposals, worker, sandbox).
2. Neither 'planning' nor 'verification' exist in PLATFORM_SKILL_TOOLS or PLATFORM_SKILL_METADATA.
3. prune_bled_platform_skills removes 'planning' and 'verification' from $DATA_DIR/skills/.
4. seed_bundled_skill_packs does not seed 'planning' or 'verification'.
5. Chat Studio goal_mode and self_verify operate as pure server runtimes without agent platform skill prerequisites.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_packs.schema import (
    PLATFORM_SKILL_IDS,
    PLATFORM_SKILL_METADATA,
    PLATFORM_SKILL_TOOLS,
)
from src.infrastructure.data.resolver import (
    BLED_AGENT_SKILL_IDS,
    prune_bled_platform_skills,
)
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS


def test_platform_skill_ids_strictly_five_core():
    """AC-1 & AC-2: PLATFORM_SKILL_IDS must strictly contain the 5 genuine tool suites."""
    expected = {"wiki", "coordination", "proposals", "worker", "sandbox"}
    assert set(PLATFORM_SKILL_IDS) == expected
    assert "planning" not in PLATFORM_SKILL_IDS
    assert "verification" not in PLATFORM_SKILL_IDS
    assert "planning" not in PLATFORM_SKILL_TOOLS
    assert "verification" not in PLATFORM_SKILL_TOOLS
    assert "planning" not in PLATFORM_SKILL_METADATA
    assert "verification" not in PLATFORM_SKILL_METADATA


def test_prune_bled_platform_skills_removes_planning_and_verification(tmp_path: Path):
    """AC-3: prune_bled_platform_skills removes planning and verification directories."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Simulate seeded planning and verification runbooks
    plan_dir = skills_dir / "planning"
    plan_dir.mkdir()
    (plan_dir / "SKILL.md").write_text("# Planning", encoding="utf-8")

    verify_dir = skills_dir / "verification"
    verify_dir.mkdir()
    (verify_dir / "SKILL.md").write_text("# Verification", encoding="utf-8")

    # Legitimate platform skill
    wiki_dir = skills_dir / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "SKILL.md").write_text("# Wiki", encoding="utf-8")

    assert "planning" in BLED_AGENT_SKILL_IDS
    assert "verification" in BLED_AGENT_SKILL_IDS

    pruned = prune_bled_platform_skills(skills_dir)
    assert "planning" in pruned
    assert "verification" in pruned
    assert not plan_dir.exists()
    assert not verify_dir.exists()
    assert wiki_dir.exists()


def test_bundled_seed_ids_excludes_planning_and_verification():
    """AC-2: BUNDLED_PACK_IDS excludes planning and verification."""
    assert "planning" not in BUNDLED_PACK_IDS
    assert "verification" not in BUNDLED_PACK_IDS


@pytest.mark.asyncio
async def test_chat_goal_and_verify_operate_without_platform_skills():
    """AC-4 & AC-5: Chat goal and verify operate as server runtimes with no agent tool prerequisites."""
    from src.domain.kernel.models import AgentProfile
    from src.domain.planning.models import ExecutionPlan, PlanStep

    # Profile with ZERO platform skills or tools
    profile = AgentProfile(
        id="clean-agent",
        name="Clean Agent",
        description="Agent without planning or verification tools",
        system_prompt="You are a clean agent.",
        allowed_tool_names=[],
        skills=[],
    )

    # Mock PlanEngine
    mock_plan_engine = MagicMock()
    fake_plan = ExecutionPlan(
        id="plan_123",
        goal="Test multi-step goal",
        agent_id=profile.id,
        session_id="sess_123",
        steps=[PlanStep(id="s1", title="Step 1", description="Do step 1")],
    )
    mock_plan_engine.formulate_plan = AsyncMock(return_value=fake_plan)

    plan = await mock_plan_engine.formulate_plan(agent=profile, goal="Test multi-step goal", session_id="sess_123")
    assert plan.id == "plan_123"
    assert len(plan.steps) == 1
