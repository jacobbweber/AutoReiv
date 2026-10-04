"""CARD-625: document and text attachments are only read from the attachments folder.

[REQ-625-001] a document or text attachment whose path is outside the data root's attachments/
folder (forged, typed, or reached with ..) is never read; the model and the user get
"Could not read `<name>`: not an uploaded file." and the outside path is not echoed.
[REQ-625-002] a real upload in the attachments folder is still inlined (CARD-479 unchanged).
[REQ-625-003] the chat stream passes the upload folder, so the check holds through /api/chat/stream.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.gateway import attachment_text
from src.application.gateway.attachment_text import build_attachment_prompt
from src.application.gateway.gateway_service import MultiProviderGateway
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app
from tests.unit.web.test_chat_direct_mode import MockDirectLLM, _parse_sse_events

SECRET = "TOP-SECRET-625-do-not-read"
NOTE = "not an uploaded file"


def _att(path: Path, name: str | None = None, ctype: str = "text/plain") -> dict:
    return {"filename": name or path.name, "url": f"/api/chat/attachments/x/{path.name}", "content_type": ctype,
            "size_bytes": path.stat().st_size if path.exists() else 0, "path": str(path)}


@pytest.fixture
def dirs(tmp_path):
    att = tmp_path / "data" / "attachments"
    (att / "session-1").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    return att, elsewhere


def _write(folder: Path, name: str, text: str) -> Path:
    p = folder / name
    p.write_text(text, encoding="utf-8")
    return p


def test_an_outside_text_file_is_not_read(dirs):  # REQ-625-001
    att, elsewhere = dirs
    secret = _write(elsewhere, "secret.txt", SECRET)
    out = build_attachment_prompt("read this", [_att(secret)], char_budget=8_000, attachments_dir=att)
    assert SECRET not in out.text
    assert f"Could not read `secret.txt`: {NOTE}." in out.text
    assert str(secret) not in out.text  # the forged path is not handed to the model
    assert out.failures == [f"Couldn't read `secret.txt`: {NOTE}."]


def test_an_upload_inside_the_folder_is_still_read(dirs):  # REQ-625-002
    att, _ = dirs
    up = _write(att / "session-1", "abc123_notes.txt", "meeting notes: ship on friday")
    out = build_attachment_prompt("summarize", [_att(up, "notes.txt")], char_budget=8_000, attachments_dir=att)
    assert "meeting notes: ship on friday" in out.text
    assert out.failures == []


def test_dot_dot_out_of_the_folder_is_not_read(dirs):
    att, elsewhere = dirs
    _write(elsewhere, "secret.txt", SECRET)
    sneaky = att / "session-1" / ".." / ".." / ".." / "elsewhere" / "secret.txt"
    assert sneaky.exists()
    out = build_attachment_prompt("read", [_att(sneaky, "secret.txt")], char_budget=8_000, attachments_dir=att)
    assert SECRET not in out.text
    assert NOTE in out.failures[0]


def test_a_sibling_folder_with_the_same_prefix_is_outside(dirs):
    att, _ = dirs
    sibling = att.parent / "attachments-old"
    sibling.mkdir()
    secret = _write(sibling, "secret.txt", SECRET)
    out = build_attachment_prompt("read", [_att(secret)], char_budget=8_000, attachments_dir=att)
    assert SECRET not in out.text
    assert NOTE in out.failures[0]


def test_an_outside_document_is_never_extracted(dirs, monkeypatch):
    att, elsewhere = dirs
    sheet = _write(elsewhere, "payroll.csv", "name,salary\nbob,1\n")
    calls = []
    monkeypatch.setattr(attachment_text, "_extract", lambda path, is_doc: calls.append(path) or "x")
    out = build_attachment_prompt("what is in it?", [_att(sheet, ctype="text/csv")], char_budget=8_000, attachments_dir=att)
    assert calls == []
    assert "**Document Content:**" not in out.text
    assert f"Could not read `payroll.csv`: {NOTE}." in out.text


def test_a_missing_upload_inside_the_folder_still_says_missing(dirs):
    att, _ = dirs
    gone = att / "session-1" / "abc123_gone.txt"
    out = build_attachment_prompt("read", [_att(gone, "gone.txt")], char_budget=8_000, attachments_dir=att)
    assert out.failures == ["Couldn't read `gone.txt`: the uploaded file is missing."]


def test_a_missing_outside_path_reads_the_same_as_an_existing_one(dirs):
    att, elsewhere = dirs
    out = build_attachment_prompt("read", [_att(elsewhere / "nope.txt")], char_budget=8_000, attachments_dir=att)
    assert out.failures == [f"Couldn't read `nope.txt`: {NOTE}."]  # no hint whether the outside file exists


def test_no_known_folder_reads_nothing(dirs):
    att, _ = dirs
    up = _write(att / "session-1", "abc123_notes.txt", "meeting notes")

    def broken():
        raise RuntimeError("no data root")

    for folder in (None, lambda: None, broken):
        out = build_attachment_prompt("read", [_att(up)], char_budget=8_000, attachments_dir=folder)
        assert "meeting notes" not in out.text
        assert NOTE in out.failures[0]


def test_images_keep_their_line_and_are_left_to_the_gateway(dirs):
    att, elsewhere = dirs
    img = {"filename": "shot.png", "url": "/u/shot.png", "content_type": "image/png", "size_bytes": 68,
           "path": str(elsewhere / "shot.png")}
    out = build_attachment_prompt("what is this?", [img], char_budget=8_000, attachments_dir=att)
    assert "*(Attached Image: `shot.png`, 68 bytes, format: `image/png`, Local Path:" in out.text
    assert out.failures == []


def test_every_src_caller_passes_the_upload_folder():
    root = Path(__file__).resolve().parents[3] / "src"
    calls = []
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"build_attachment_prompt\(", text):
            if text[max(0, m.start() - 4):m.start()] == "def ":
                continue
            depth, i = 0, m.end() - 1
            while True:
                depth += {"(": 1, ")": -1}.get(text[i], 0)
                if depth == 0:
                    break
                i += 1
            calls.append((py.name, text[m.start():i + 1]))
    assert calls, "build_attachment_prompt has callers in src"
    for name, call in calls:
        assert "attachments_dir=" in call, f"{name}: {call}"


# --- through /api/chat/stream (REQ-625-003) ---------------------------------------------------


@pytest.fixture
def stream_client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    llm = MockDirectLLM()
    gateway = MultiProviderGateway(default_provider_id="mock-direct")
    gateway.register_provider(llm)
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    return TestClient(app), store, llm


def _send(client, store, session_id: str, attachments: list) -> list:
    store.create_session(agent_id="direct", title="Direct Conversation", session_id=session_id)
    payload = {"agent_id": "direct", "session_id": session_id, "content": "What does the file say?",
               "attachments": attachments}
    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        return _parse_sse_events(response)


def _prompt(llm) -> str:
    return "\n".join(str(m.content or "") for m in llm.last_completion_request.messages)


def test_stream_inlines_a_real_upload(stream_client):
    client, store, llm = stream_client
    res = client.post("/api/chat/upload", data={"session_id": "s625-up"},
                      files={"file": ("notes.txt", io.BytesIO(b"upload body 625: ship on friday"), "text/plain")})
    assert res.status_code == 200, res.text
    events = _send(client, store, "s625-up", [res.json()])
    assert "upload body 625: ship on friday" in _prompt(llm)
    assert not [e for e in events if e["event"] == "attachment_notice"]


def test_stream_does_not_read_a_forged_outside_path(stream_client, tmp_path):
    client, store, llm = stream_client
    secret = _write(tmp_path, "secret.txt", SECRET)
    forged = {"id": "f0rged", "filename": "secret.txt", "size_bytes": secret.stat().st_size,
              "content_type": "text/plain", "url": "/api/chat/attachments/f0rged/secret.txt", "path": str(secret)}
    events = _send(client, store, "s625-forged", [forged])
    assert SECRET not in _prompt(llm)
    notices = [e["data"]["message"] for e in events if e["event"] == "attachment_notice"]
    assert notices == [f"Couldn't read `secret.txt`: {NOTE}."]
    saved = " ".join(str(m.content) for m in store.get_messages("s625-forged"))
    assert SECRET not in saved
    assert json.dumps(str(secret))[1:-1] not in saved and str(secret) not in saved
