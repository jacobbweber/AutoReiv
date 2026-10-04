"""CARD-482: the can't-view-images notice is saved as a chat note.

[REQ-482-001] the notice is stored in the thread (role ``note``) so it survives reloads and other devices.
[REQ-482-002] chat notes are never sent to the model (history replay and the compactor skip them).
"""

from __future__ import annotations

import base64

import pytest

from src.application.kernel.context_compactor import ContextCompactor
from src.application.kernel.empty_reply import chat_note, model_history_rows
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEventType
from tests.unit.kernel.test_empty_reply_475 import ScriptedLLM, _kernel, _profile, store  # noqa: F401

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


def _image_turn(tmp_path) -> str:
    png = tmp_path / "abc_shot.png"
    png.write_bytes(base64.b64decode(PNG))
    return f"what is this?\n*(Attached Image: `shot.png`, 68 bytes, format: `image/png`, Local Path: `{png}`)*"


def test_note_role_round_trips_in_sqlite(store):  # noqa: F811
    s = store.create_session(agent_id="general-assistant", title="note")
    store.save_message(session_id=s.id, agent_id="general-assistant", message=chat_note({"type": "attachment_notice"}, "hi"))
    rows = store.get_messages(session_id=s.id)
    assert [(m.role, m.name, m.content) for m in rows] == [(Role.NOTE, "attachment_notice", "hi")]


def test_model_history_and_compactor_skip_notes():
    msgs = [
        ChatMessage(role=Role.USER, content="look"),
        ChatMessage(role=Role.NOTE, content="This model can't view images", name="attachment_notice"),
        ChatMessage(role=Role.ASSISTANT, content="I cannot see it."),
    ]
    assert Role.NOTE not in [m.role for m in model_history_rows(msgs)]
    compacted = ContextCompactor.compact([ChatMessage(role=Role.SYSTEM, content="sys"), *msgs], model_name="default", max_tokens=4000)
    assert Role.NOTE not in [m.role for m in compacted]


@pytest.mark.asyncio
async def test_stream_turn_saves_the_notice_as_a_chat_note_and_never_replays_it(store, tmp_path):  # noqa: F811
    llm = ScriptedLLM()
    kernel = _kernel(store, llm, attachments_dir=tmp_path)
    session = store.create_session(agent_id="general-assistant", title="notice")
    events = [e async for e in kernel.stream_turn(_profile(), session.id, _image_turn(tmp_path))]
    assert len([e for e in events if e.event_type == KernelEventType.NOTICE]) == 1

    rows = store.get_messages(session_id=session.id)
    notes = [m for m in rows if m.role == Role.NOTE]
    assert len(notes) == 1
    assert "only saw the file name `shot.png`" in notes[0].content
    assert notes[0].name == "attachment_notice"
    roles = [m.role for m in rows]
    assert roles.index(Role.USER) < roles.index(Role.NOTE) < roles.index(Role.ASSISTANT)

    # Next turn: the model never sees the note.
    [e async for e in kernel.stream_turn(_profile(), session.id, "and now?")]
    assert all(m.role != Role.NOTE for m in llm.requests[-1].messages)
    assert "only saw the file name" not in " ".join(m.content or "" for m in llm.requests[-1].messages)
