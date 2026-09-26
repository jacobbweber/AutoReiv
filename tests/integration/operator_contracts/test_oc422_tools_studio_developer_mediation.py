"""CARD-422 operator contract: Tools Studio Talk and Submit.

REQ-422-001..004. Temp user-data only [ADR-0055].
Submit runs a developer turn or refuses. A queued job is not success.
Packaging preference is stored on the packet and is not applied.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import patch

from src.domain.gateway.models import ChatMessage, Role

BEHAVIOR = "Look up a wiki note by title and return the first paragraph."
DRAFT = {
    "tool_name": "wiki_note_peek",
    "behavior": BEHAVIOR,
    "language_hint": "Python",
    "runtime_hint": "in-process",
    "path_context": "packs/demo/tools",
    "packaging_preference": "native",
}


def _count(store, table: str) -> int:
    conn = store._get_connection()
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
    finally:
        if getattr(store, "_mem_conn", None) is None:
            conn.close()


def _status(job) -> str:
    status = getattr(job, "status", "")
    return status.value if hasattr(status, "value") else str(status or "")


class _RecordingKernel:
    def __init__(self, store, content: str):
        self.store = store
        self.content = content
        self.calls = []

    async def run_turn(self, **kwargs):
        self.calls.append(kwargs)
        messages = list(self.store.get_messages(kwargs["session_id"]) or [])
        assert any(BEHAVIOR in str(getattr(message, "content", "") or "") for message in messages)
        assert kwargs.get("resume") is True
        assert kwargs.get("job_id")
        assert kwargs.get("phase_id")
        agent = kwargs.get("agent")
        assert getattr(agent, "id", None) == "developer"
        return ChatMessage(role=Role.ASSISTANT, content=self.content)


class _BoomKernel:
    async def run_turn(self, **kwargs):
        raise RuntimeError("model down")


class _EmptyKernel:
    async def run_turn(self, **kwargs):
        return ChatMessage(role=Role.ASSISTANT, content="   ")


class _SlowKernel:
    async def run_turn(self, **kwargs):
        await asyncio.sleep(1)
        return ChatMessage(role=Role.ASSISTANT, content="too late")


def test_oc422_talk_opens_developer_chat_and_submit_runs_or_refuses(operator_client):
    """REQ-422-001, REQ-422-002, REQ-422-003, REQ-422-004."""
    client, store, _wiki = operator_client
    app = client.app
    jobs_before = _count(store, "jobs")

    missing = client.post(
        "/api/tools_studio/authoring/jobs",
        json={"intent": "create", "draft": {"behavior": ""}},
    )
    assert missing.status_code == 400, missing.text
    assert _count(store, "jobs") == jobs_before

    coded = client.post(
        "/api/tools_studio/authoring/jobs",
        json={"intent": "create", "draft": {"behavior": BEHAVIOR, "code": "def peek():\n    pass"}},
    )
    assert coded.status_code == 400, coded.text
    assert "implementation code" in coded.json()["detail"]["message"]
    assert _count(store, "jobs") == jobs_before

    unnamed = client.post(
        "/api/tools_studio/authoring/jobs",
        json={"intent": "delete", "draft": {"behavior": "remove it"}},
    )
    assert unnamed.status_code == 400, unnamed.text

    app.state.kernel = None
    refused = client.post("/api/tools_studio/authoring/jobs", json={"intent": "create", "draft": DRAFT})
    assert refused.status_code == 503, refused.text
    refused_detail = refused.json()["detail"]
    assert refused_detail["ran"] is False
    assert "unavailable" in refused_detail["message"].lower()
    assert _count(store, "jobs") == jobs_before

    reply = "I will add a read-only wiki lookup next. No package was written."
    kernel = _RecordingKernel(store, reply)
    app.state.kernel = kernel

    created = client.post("/api/tools_studio/authoring/jobs", json={"intent": "create", "draft": DRAFT})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["agent_id"] == "developer"
    assert body["status"] == "done"
    assert body["status"] != "queued"
    assert body["ran"] is True
    assert body["queued_only"] is False
    assert body["mediation"] == "developer_turn"
    assert body["persisted_tool"] is False
    assert body["packaging_applied"] is False
    assert body["reply"] == reply
    assert BEHAVIOR in body["prompt"]
    assert "wiki_note_peek" in body["prompt"]
    assert "native" in body["prompt"]
    packet = body["packet"]
    assert packet["schema"] == "tools_studio_authoring_packet"
    assert packet["studio"] == "tools"
    assert packet["intent"] == "create"
    assert packet["draft"]["packaging_preference"] == "native"
    assert packet["packaging_applied"] is False
    assert "code" not in packet["draft"]
    assert len(kernel.calls) == 1
    assert _count(store, "jobs") == jobs_before + 1

    job = store.get_job(body["job_id"])
    assert _status(job) == "done"
    assert job.agent_id == "developer"
    assert job.template_id == "tools_studio_developer_mediation"
    assert job.session_id == body["session_id"]

    messages = client.get(f"/api/sessions/{body['session_id']}/messages")
    assert messages.status_code == 200, messages.text
    transcript = " ".join(item["content"] for item in messages.json())
    assert BEHAVIOR in transcript
    assert reply in transcript
    session = store.get_session(body["session_id"])
    assert session.agent_id == "developer"

    observed = client.get(f"/api/observe/jobs/{body['job_id']}")
    assert observed.status_code == 200, observed.text
    kinds = {item.get("kind") for item in observed.json()["timeline"]}
    assert "tools_studio_authoring_packet" in kinds
    assert "tools_studio_developer_turn" in kinds

    fetched = client.get(f"/api/tools_studio/authoring/jobs/{body['job_id']}")
    assert fetched.status_code == 200, fetched.text
    detail = fetched.json()
    assert detail["queued_only"] is False
    assert detail["ran"] is True
    assert detail["packaging_applied"] is False
    assert detail["persisted_tool"] is False

    jobs_after_submit = _count(store, "jobs")
    talk = client.post("/api/tools_studio/authoring/talk", json={"intent": "modify", "draft": DRAFT})
    assert talk.status_code == 200, talk.text
    talked = talk.json()
    assert talked["opened_job"] is False
    assert talked["opened_chat"] is True
    assert talked["job_id"] is None
    assert talked["agent_id"] == "developer"
    assert talked["session_id"] != body["session_id"]
    assert BEHAVIOR in talked["prompt"]
    assert talked["persisted_tool"] is False
    assert _count(store, "jobs") == jobs_after_submit
    talk_messages = client.get(f"/api/sessions/{talked['session_id']}/messages")
    assert talk_messages.status_code == 200, talk_messages.text
    talk_body = " ".join(item["content"] for item in talk_messages.json())
    assert BEHAVIOR in talk_body
    assert talked["session_id"]
    talk_session = store.get_session(talked["session_id"])
    assert talk_session.agent_id == "developer"
    again = client.post("/api/tools_studio/authoring/talk", json={"intent": "modify", "draft": DRAFT})
    assert again.status_code == 200, again.text
    assert again.json()["session_id"] != talked["session_id"]

    app.state.kernel = _BoomKernel()
    boom = client.post("/api/tools_studio/authoring/jobs", json={"intent": "create", "draft": DRAFT})
    assert boom.status_code == 503, boom.text
    boom_detail = boom.json()["detail"]
    assert boom_detail["ran"] is False
    assert boom_detail["status"] == "failed"
    assert "did not run" in boom_detail["message"]
    failed = store.get_job(boom_detail["job_id"])
    assert _status(failed) == "failed"
    assert _status(failed) != "queued"

    app.state.kernel = _EmptyKernel()
    empty = client.post(
        "/api/tools_studio/authoring/jobs",
        json={"intent": "delete", "draft": {"tool_name": "wiki_note_peek", "behavior": "Remove wiki_note_peek."}},
    )
    assert empty.status_code == 503, empty.text
    empty_detail = empty.json()["detail"]
    assert empty_detail["ran"] is False
    assert empty_detail["status"] == "failed"
    assert _status(store.get_job(empty_detail["job_id"])) == "failed"

    app.state.kernel = _SlowKernel()
    with patch(
        "src.application.tools.developer_mediation.resolve_standing_phase_llm_timeout",
        return_value=0.05,
    ):
        timed = client.post("/api/tools_studio/authoring/jobs", json={"intent": "create", "draft": DRAFT})
    assert timed.status_code == 503, timed.text
    timed_detail = timed.json()["detail"]
    assert timed_detail["ran"] is False
    assert "timed out" in timed_detail["message"].lower()
    assert _status(store.get_job(timed_detail["job_id"])) == "failed"
    assert _status(store.get_job(timed_detail["job_id"])) != "queued"

    from src.application.tools import developer_mediation as mediation

    source = inspect.getsource(mediation)
    assert "write_project_file" not in source
    assert "scaffold_mcp" not in source
    assert "SkillToolBinding" not in source
    assert "skill_tool_bindings" not in source


class _RegisteringKernel:
    """Developer turn that calls the real register_native_tool with a broken tool [CARD-511]."""

    def __init__(self, app):
        self.app = app
        self.results = []

    async def run_turn(self, **kwargs):
        from src.domain.gateway.models import ToolCall

        call = ToolCall(
            id="c511_call",
            name="register_native_tool",
            arguments={
                "name": "c511_job_broken",
                "description": "Broken on purpose.",
                "code": "import nonexistent_c511_mod\n\ndef run(**kw):\n    return 1\n",
            },
        )
        result = await self.app.state.tool_registry.execute(
            call,
            kwargs["agent"],
            session_id=kwargs["session_id"],
            approval_mode="run",
            job_id=kwargs["job_id"],
        )
        self.results.append(result)
        output = result.output if isinstance(result.output, dict) else {}
        return ChatMessage(role=Role.ASSISTANT, content=str(output.get("message") or result.error or "no output"))


def test_oc511_job_records_the_tool_check_and_the_tool_is_not_registered(operator_client):
    """CARD-511 REQ-511-010: the Tools Studio job keeps the check result; persisted_tool stays false."""
    client, store, _wiki = operator_client
    app = client.app
    kernel = _RegisteringKernel(app)
    app.state.kernel = kernel

    created = client.post("/api/tools_studio/authoring/jobs", json={"intent": "create", "draft": DRAFT})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["persisted_tool"] is False
    assert body["packaging_applied"] is False
    assert body["reply"].startswith("Not registered: c511_job_broken failed the import check")
    checks = body["tool_checks"]
    assert len(checks) == 1
    assert checks[0]["tool"] == "c511_job_broken"
    assert checks[0]["status"] == "failed"
    assert checks[0]["stage"] == "import"
    assert checks[0]["message"].startswith("Not registered:")

    events = store.list_standing_journey_events(body["job_id"])
    assert any(event.get("kind") == "tools_studio_tool_check" for event in events)
    latest = store.get_latest_job_phase_checkpoint(body["job_id"])
    statuses = [cp.verifier_status for cp in store.list_job_phase_checkpoints(body["job_id"])]
    assert "failed" in statuses, (statuses, latest)

    fetched = client.get(f"/api/tools_studio/authoring/jobs/{body['job_id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["tool_checks"][0]["status"] == "failed"
    assert fetched.json()["persisted_tool"] is False
    assert all(row["name"] != "c511_job_broken" for row in client.get("/api/tools/native").json()["tools"])
