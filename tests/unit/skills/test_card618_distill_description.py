"""CARD-618: distilled skill descriptions use the ~200 limit from CARD-614, cut on a word boundary."""

from unittest.mock import AsyncMock

import pytest
import yaml

from src.application.skills.distillation_service import SkillDistillationService
from src.domain.skills.user_skill import SKILL_DESCRIPTION_LIMIT, clip_description

WORDS = "Use when the operator asks to file a gardening note: search the wiki first, reuse the existing tags"
LONG_150 = (WORDS + " and keep the summary short and plain.")[:150]
LONG_300 = " ".join([WORDS] * 3)


def _frontmatter(md: str) -> dict:
    return yaml.safe_load(md.split("---")[1])


def test_limit_is_shared_with_skill_studio():
    from src.web.routers.skill_studio import SKILL_DESCRIPTION_LIMIT as studio_limit

    assert SKILL_DESCRIPTION_LIMIT == studio_limit == 200


def test_clip_keeps_150_whole_and_cuts_300_on_a_word():
    assert clip_description(LONG_150) == " ".join(LONG_150.split())
    cut = clip_description(LONG_300)
    assert 150 < len(cut) <= 200
    assert LONG_300.startswith(cut) and LONG_300[len(cut)] == " "  # ends on a whole word


def test_llm_description_kept_and_frontmatter_parses():
    svc = SkillDistillationService(store=None)
    out = svc._build_distill_response("autoreiv", {"name": "Gardening Notes", "description": LONG_150}, "")
    assert out["description"] == LONG_150
    fm = _frontmatter(out["runbook_markdown"])  # the ': ' in the text must not break YAML
    assert fm["description"] == LONG_150
    title, desc = svc._parse_frontmatter(out["runbook_markdown"], "gardening-notes")
    assert desc == LONG_150

    long_out = svc._build_distill_response("autoreiv", {"name": "X", "description": LONG_300}, "")
    assert 150 < len(long_out["description"]) <= 200


@pytest.mark.asyncio
async def test_prompt_asks_for_200_not_60():
    gw = AsyncMock()
    gw.default_model_id = "m"
    gw.complete.return_value = AsyncMock(text='{"needs_tool": false}')
    svc = SkillDistillationService(store=None, gateway=gw)
    turn = {"target_agent_id": "autoreiv", "user_prompt": "p", "assistant_response": "a", "tool_calls": [], "tool_results": []}
    await svc._run_llm_distillation(turn, "")
    system = gw.complete.call_args.args[0].messages[0].content
    assert "at most 200 characters" in system and "60 characters" not in system
