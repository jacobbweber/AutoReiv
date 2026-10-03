"""CARD-614: a skill description may be about 200 characters and is never cut on load or save.

- Save then open returns the full description (the API never had a limit).
- The runbook generator gets the whole description and asks for at most 200 characters (was "strictly <= 60").
- The form: a 3-row box with maxlength 200, label and counter say 200 (see card_614 vitest for load/counter).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.web.routers.skill_studio import SKILL_DESCRIPTION_LIMIT
from tests.unit.web.test_skill_studio_routes import SKILL_MD, _client, app_env  # noqa: F401 - fixture

LONG = ("Use when Jacob asks to plan, water, feed or prune the vegetable garden beds, including seasonal sowing "
        "dates, frost warnings and the weekly watering rota for the greenhouse and raised beds.")


def test_long_description_is_within_the_new_limit_and_over_the_old():
    assert 60 < len(LONG) <= SKILL_DESCRIPTION_LIMIT == 200


@pytest.mark.asyncio
async def test_save_then_open_keeps_the_full_description(app_env):  # noqa: F811
    app, _ = app_env
    md = SKILL_MD.replace("description: Render 3D scenes via Blender MCP", f"description: {LONG}")
    md = md.replace("  - mcp_blender_render\n", "")
    md = md.replace("tools:\n", "tools: []\n")
    async with _client(app) as ac:
        saved = await ac.post("/api/skill_studio/save", json={"skill_id": "garden-care", "skill_content": md})
        assert saved.status_code == 200, saved.text
        opened = await ac.get("/api/skill_studio/skills/garden-care")
    assert opened.status_code == 200, opened.text
    assert opened.json()["description"] == LONG


@pytest.mark.asyncio
async def test_runbook_generator_gets_the_whole_description(app_env):  # noqa: F811
    app, _ = app_env
    seen = {}

    class _Resp:
        text = "---\nname: Garden\ndescription: x\ntools: []\n---\n# Garden\n"

    class _Gateway:
        default_model_id = "default"

        async def complete(self, request):
            seen["system"] = request.messages[0].content
            seen["user"] = request.messages[1].content
            return _Resp()

    app.state.gateway = _Gateway()
    async with _client(app) as ac:
        resp = await ac.post("/api/skill_studio/runbook", json={
            "agent_id": "autoreiv", "skill_id": "garden", "skill_name": "Garden",
            "trigger_description": LONG + "\n", "intent_notes": "", "selected_tools": [],
        })
    assert resp.status_code == 200
    assert f"Trigger Description: {LONG}\n" in seen["user"]
    assert "at most 200 characters" in seen["system"] and "60" not in seen["system"]


def test_form_says_200_and_does_not_cut_at_60():
    html = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert 'id="factorySkillTriggerInput" data-testid="factory-skill-description" rows="3" maxlength="200"' in html
    assert "up to about 200 chars" in html and "&le; 60 chars" not in html and ">0/200<" in html
    js = Path("src/web/static/modules/studios/skill_studio/workshop_meta.js").read_text(encoding="utf-8")
    assert ".slice(0, 60)" not in js
    studio = Path("src/web/static/modules/studios/skill_studio.js").read_text(encoding="utf-8")
    assert "}/60`" not in studio and "'0/60'" not in studio and "<= 60" not in studio
