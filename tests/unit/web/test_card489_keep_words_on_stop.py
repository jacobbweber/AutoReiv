"""CARD-489: a stopped reply keeps the words already shown, marked as stopped."""

from __future__ import annotations

import re
from pathlib import Path

from src.application.kernel.stopped_reply import STOPPED_MARKER, PartialReply, stopped_message
from src.domain.gateway.models import Role
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _tok(text):
    return KernelEvent(event_type=KernelEventType.TOKEN, content=text)


def test_partial_collects_tokens_of_the_current_model_call():
    p = PartialReply()
    for w in ("Here ", "are ", "six ", "words ", "so ", "far"):
        p.observe(_tok(w))
    assert p.text() == "Here are six words so far"


def test_partial_resets_after_a_saved_step():
    p = PartialReply()
    p.observe(_tok("Let me look."))
    p.observe(KernelEvent(event_type=KernelEventType.TOOL_START, tool_call={"name": "read_file"}))
    assert p.text() == ""  # the kernel saved that text with the tool call
    p.observe(_tok("The file says"))
    assert p.text() == "The file says"
    p.observe(KernelEvent(event_type=KernelEventType.TURN_END, content="The file says hi."))
    assert p.text() == ""


def test_stopped_message_marks_the_text_and_is_an_assistant_row():  # REQ-489-001
    m = stopped_message("Here are six words so far ")
    assert m.role == Role.ASSISTANT
    assert m.content == f"Here are six words so far\n\n{STOPPED_MARKER}"
    assert "Stopped" in STOPPED_MARKER


def test_nothing_saved_before_the_first_token():  # REQ-489-003
    assert stopped_message("") is None
    assert stopped_message("   \n") is None


def test_stopped_row_round_trips_and_is_replayed_to_the_model(tmp_path):  # D2: labelled as stopped
    store = SQLiteStateStore(db_path=str(tmp_path / "s.db"))
    store.initialize_db()
    s = store.create_session(agent_id="assistant", title="stop")
    store.save_message(session_id=s.id, agent_id="assistant", message=stopped_message("partial words"))
    rows = store.get_messages(session_id=s.id)
    assert rows[-1].content.endswith(STOPPED_MARKER)
    from src.application.kernel.empty_reply import skip_empty_assistant_rows

    assert skip_empty_assistant_rows(rows)[-1].content.startswith("partial words")


def test_chat_worker_saves_the_partial_on_cancel():
    src = Path("src/web/routers/chat.py").read_text(encoding="utf-8")
    assert "partial = PartialReply()" in src
    assert re.search(r"partial\.observe\(event\)\s*\n\s*await _forward_kernel_event", src)
    assert src.count("partial.observe(event)") >= 2  # plain turns and the Direct fast path (live QA 2026-09-30)
    cancel = src.split("except asyncio.CancelledError:\n            logger.info(\"Chat stream worker cancelled", 1)[1][:700]
    assert "stopped_message(partial.text())" in cancel
    assert "store.save_message(" in cancel
