"""CARD-503: a distill that could not use the model says so (source/fallback_reason and a note on the card text)."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.skills.distillation_service import SkillDistillationService
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.skills.test_card500_distill_turn import SKILL_JSON


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


def _turn(store):
    sid = "s503"
    store.create_session(agent_id="autoreiv", title="t", session_id=sid)
    store.save_message(session_id=sid, agent_id="autoreiv", message=ChatMessage(role=Role.USER, content="weather?"))
    mid = store.save_message(session_id=sid, agent_id="autoreiv", message=ChatMessage(role=Role.ASSISTANT, content="It rains."))
    return sid, mid


def _gateway(text=None, exc=None):
    gw = AsyncMock()
    gw.default_model_id = "mock"
    if exc is not None:
        gw.complete = AsyncMock(side_effect=exc)
    else:
        resp = SimpleNamespace(text=text, message=SimpleNamespace(content=text))
        gw.complete = AsyncMock(return_value=resp)
    return gw


@pytest.mark.asyncio
async def test_model_answer_is_marked_model(store):
    sid, mid = _turn(store)
    out = await SkillDistillationService(store=store, gateway=_gateway(json.dumps(SKILL_JSON))).distill_turn(sid, mid)
    assert out["source"] == "model" and "fallback_reason" not in out


@pytest.mark.asyncio
@pytest.mark.parametrize("gw,reason", [
    (None, "no model is connected"),
    (_gateway(exc=asyncio.TimeoutError()), "the model did not answer in time"),
    (_gateway(exc=RuntimeError("boom")), "the model call failed"),
    (_gateway(text=""), "the model returned an empty answer"),
])
async def test_fallback_says_why(store, gw, reason):
    sid, mid = _turn(store)
    out = await SkillDistillationService(store=store, gateway=gw).distill_turn(sid, mid, guidance="cite sources")
    assert out["source"] == "fallback" and out["fallback_reason"] == reason
    assert out["plain_summary"]["observed_slip"].startswith(f"(Written without the model: {reason}.)")
