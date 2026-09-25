"""CARD-500: distill builds the prompt from the clicked turn only (REQ-500-002)."""

import json
from unittest.mock import AsyncMock

import pytest

from src.application.skills.distillation_service import SkillDistillationService
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SKILL_JSON = {
    "needs_tool": False,
    "skill_id": "cite-sources",
    "name": "Cite Sources",
    "description": "Always cite",
    "plain_summary": {"observed_slip": "s", "remedy": "r"},
    "when_to_use": "w",
    "procedure": ["p"],
    "pitfalls": ["x"],
    "verification": ["v"],
}


class RecordingGateway:
    def __init__(self):
        self.default_model_id = "mock"
        self.complete = AsyncMock()
        resp = AsyncMock()
        resp.text = json.dumps(SKILL_JSON)
        self.complete.return_value = resp

    def user_content(self) -> str:
        req = self.complete.call_args.args[0]
        return req.messages[-1].content


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


def _save(store, sid, role, content, **kw):
    return store.save_message(session_id=sid, agent_id="autoreiv", message=ChatMessage(role=role, content=content, **kw))


@pytest.mark.asyncio
async def test_distill_uses_the_clicked_turn_even_in_a_long_chat(store, tmp_path):
    """REQ-500-002: 13 turns (26 messages); Teach on the 2nd reply distills the 2nd turn only."""
    sess = store.create_session(agent_id="autoreiv", title="long")
    ids = {}
    for n in range(1, 14):
        _save(store, sess.id, Role.USER, f"QUESTION-{n:02d}")
        ids[n] = _save(store, sess.id, Role.ASSISTANT, f"ANSWER-{n:02d}")
    gw = RecordingGateway()
    svc = SkillDistillationService(store=store, gateway=gw, data_dir=tmp_path)
    await svc.distill_turn(session_id=sess.id, message_id=ids[2], guidance="cite")
    text = gw.user_content()
    assert "User Prompt: QUESTION-02" in text
    assert "Assistant Output: ANSWER-02" in text
    for other in ("QUESTION-01", "QUESTION-13", "ANSWER-13", "QUESTION-10"):
        assert other not in text


@pytest.mark.asyncio
async def test_distill_includes_only_the_clicked_turns_tool_calls_and_results(store, tmp_path):
    """REQ-500-002 / D3: tool calls and results come from the clicked turn, not the whole chat."""
    sess = store.create_session(agent_id="autoreiv", title="tools")
    _save(store, sess.id, Role.USER, "TURN-ONE please")
    _save(store, sess.id, Role.ASSISTANT, "", tool_calls=[ToolCall(id="t1", name="tool_alpha", arguments={"q": 1})])
    _save(store, sess.id, Role.TOOL, "ALPHA-RESULT", tool_call_id="t1", name="tool_alpha")
    first_final = _save(store, sess.id, Role.ASSISTANT, "TURN-ONE done")
    _save(store, sess.id, Role.USER, "TURN-TWO please")
    _save(store, sess.id, Role.ASSISTANT, "", tool_calls=[ToolCall(id="t2", name="tool_beta", arguments={"q": 2})])
    _save(store, sess.id, Role.TOOL, "BETA-RESULT", tool_call_id="t2", name="tool_beta")
    _save(store, sess.id, Role.ASSISTANT, "TURN-TWO done")
    gw = RecordingGateway()
    svc = SkillDistillationService(store=store, gateway=gw, data_dir=tmp_path)
    await svc.distill_turn(session_id=sess.id, message_id=first_final)
    text = gw.user_content()
    assert "User Prompt: TURN-ONE please" in text
    assert "Assistant Output: TURN-ONE done" in text
    assert "tool_alpha" in text and "ALPHA-RESULT" in text
    assert "tool_beta" not in text and "BETA-RESULT" not in text and "TURN-TWO" not in text
