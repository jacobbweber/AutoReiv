"""CARD-695: Post-registration empty model reply recovery and DataDirResolver caching."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.model_capabilities import ModelCapabilityResolver
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.errors import EmptyModelReplyError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
)
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.content.store import configure as configure_store
from src.infrastructure.data.resolver import DataDirResolver
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


class _ScriptedGatewayProvider(LLMProviderPort):
    provider_id = "mock"

    def __init__(self, *, stream_steps=None, complete_steps=None):
        self.stream_steps = list(stream_steps or [])
        self.complete_steps = list(complete_steps or [])
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if self.complete_steps:
            return self.complete_steps.pop(0)
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content=""))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        chunks = (
            self.stream_steps.pop(0)
            if self.stream_steps
            else [StreamChunk(content="", is_finished=True, finish_reason="stop")]
        )
        for chunk in chunks:
            yield chunk

    async def list_models(self):
        return []


def _build_kernel(tmp_path: Path, llm: _ScriptedGatewayProvider) -> tuple[AgentKernel, SQLiteStateStore, ScopedToolRegistry]:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    configure_store(data_root=data_root)

    store = SQLiteStateStore(db_path=str(tmp_path / "state.db"))
    store.initialize_db()

    reg = ScopedToolRegistry()
    builder = AgentBuilderTools(agent_registry=None, tool_registry=reg, store=store, data_dir=data_root)
    builder.register_tools(reg)

    gw = MultiProviderGateway()
    gw.register_provider(llm)
    gw.set_capability_resolver(ModelCapabilityResolver(settings_getter=lambda k, d=None: d))

    kernel = AgentKernel(
        gateway=gw,
        tool_registry=reg,
        state_store=store,
        telemetry=TelemetryCollector(store=store),
        data_dir=str(data_root),
    )
    return kernel, store, reg


def _autoreiv_profile() -> AgentProfile:
    return AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Primary assistant",
        system_prompt="You are AutoReiv.",
        allowed_skill=["capability-authoring", "user:*"],
    )


@pytest.mark.asyncio
async def test_stream_turn_synthesizes_reply_when_model_returns_empty_after_write_skill_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    tool_code = (
        '"""Convert Celsius to Fahrenheit."""\n'
        'RISK = "read_only"\n\n'
        "def run(celsius: float = 0.0) -> dict:\n"
        '    return {"fahrenheit": round(celsius * 9.0 / 5.0 + 32.0, 2)}\n'
    )
    tc_skill = ToolCall(
        id="call_1",
        name="write_skill_file",
        arguments={
            "skill_id": "agora-temp-converter",
            "path": "SKILL.md",
            "content": "---\nname: Temp Converter\ndescription: Convert temperatures.\n---\n# Temp Converter\n",
        },
    )
    tc_tool = ToolCall(
        id="call_2",
        name="write_skill_file",
        arguments={
            "skill_id": "agora-temp-converter",
            "path": "tools/c_to_f.py",
            "content": tool_code,
            "sample_arguments": {"celsius": 100.0},
        },
    )
    llm = _ScriptedGatewayProvider(
        stream_steps=[
            [StreamChunk(content="", tool_calls=[tc_skill, tc_tool], is_finished=True, finish_reason="tool_calls")],
            # Post-registration step: model emits only reasoning and stops with empty content
            [StreamChunk(content="", reasoning_content="Done registering.", is_finished=True, finish_reason="stop")],
        ]
    )
    kernel, store, reg = _build_kernel(tmp_path, llm)
    session = store.create_session(agent_id="autoreiv", title="dogfood-skill")

    events = [
        ev
        async for ev in kernel.stream_turn(
            _autoreiv_profile(),
            session.id,
            "Create an Agora skill agora-temp-converter with c_to_f tool",
            approval_mode="run",
        )
    ]

    error_events = [ev for ev in events if ev.event_type == KernelEventType.ERROR]
    assert error_events == [], f"Unexpected error events: {error_events}"

    end_events = [ev for ev in events if ev.event_type == KernelEventType.TURN_END]
    assert len(end_events) == 1
    final_text = end_events[0].content or ""
    assert final_text.strip() != ""
    assert "empty reply" not in final_text.lower()
    assert "agora-temp-converter" in final_text
    assert "c_to_f" in final_text
    assert "c_to_f" in reg

    saved_assistant = [
        m for m in store.get_messages(session.id) if m.role == Role.ASSISTANT and not m.tool_calls
    ]
    assert len(saved_assistant) == 1
    assert "c_to_f" in (saved_assistant[0].content or "")


@pytest.mark.asyncio
async def test_run_turn_synthesizes_reply_when_model_returns_empty_after_write_skill_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    tc_skill = ToolCall(
        id="call_1",
        name="write_skill_file",
        arguments={
            "skill_id": "agora-notes-helper",
            "path": "SKILL.md",
            "content": "---\nname: Notes Helper\ndescription: Format notes.\n---\n# Notes Helper\n",
        },
    )
    llm = _ScriptedGatewayProvider(
        complete_steps=[
            CompletionResponse(
                model="mock/m",
                message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[tc_skill]),
            ),
            CompletionResponse(
                model="mock/m",
                message=ChatMessage(role=Role.ASSISTANT, content=""),
            ),
        ]
    )
    kernel, store, _ = _build_kernel(tmp_path, llm)
    session = store.create_session(agent_id="autoreiv", title="dogfood-run-turn")

    reply = await kernel.run_turn(
        _autoreiv_profile(),
        session.id,
        "Create agora-notes-helper skill",
        approval_mode="run",
    )
    assert reply.content and "agora-notes-helper" in reply.content
    assert "empty reply" not in reply.content.lower()


@pytest.mark.asyncio
async def test_empty_reply_without_prior_tool_call_still_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    llm = _ScriptedGatewayProvider(
        complete_steps=[
            CompletionResponse(model="mock/m", message=ChatMessage(role=Role.ASSISTANT, content=""))
        ]
    )
    kernel, store, _ = _build_kernel(tmp_path, llm)
    session = store.create_session(agent_id="autoreiv", title="still-errors")
    with pytest.raises(EmptyModelReplyError):
        await kernel.run_turn(_autoreiv_profile(), session.id, "hello")


def test_datadir_resolver_caches_sqlite_settings_and_isolates_backup_dir(tmp_path, monkeypatch):
    isolated_root = tmp_path / "isolated_data"
    db_path = isolated_root / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a real settings table in the isolated DB and in a fake platform default DB
    fake_home = tmp_path / "fake_home"
    fake_default_db = fake_home / ".autoreiv" / "database" / "autoreiv.db"
    fake_default_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(fake_default_db)) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT)")
        conn.execute(
            "INSERT INTO settings (key, value_json) VALUES (?, ?)",
            ("backup_dir", json.dumps(str(tmp_path / "leaked_live_backups"))),
        )
        conn.commit()

    custom_wiki = tmp_path / "custom_wiki"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT)")
        conn.execute(
            "INSERT INTO settings (key, value_json) VALUES (?, ?)",
            ("wiki_path", json.dumps(str(custom_wiki))),
        )
        conn.commit()

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(isolated_root))
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_BACKUP_DIR", raising=False)
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)

    connect_calls: list[str] = []
    real_connect = sqlite3.connect

    def counting_connect(target, *args, **kwargs):
        connect_calls.append(str(target))
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr("src.infrastructure.data.resolver.sqlite3.connect", counting_connect)

    for _ in range(40):
        resolved = DataDirResolver(home=fake_home, os_name="posix", in_docker=False).resolve()
        assert resolved.root == isolated_root
        assert resolved.wiki_path == custom_wiki
        # Must NOT leak backup_dir from fake_default_db when AUTOREIV_DATA_DIR is set
        assert resolved.backups_path == isolated_root / "backups"

    # Across 40 resolve() calls, sqlite3.connect should only run on cache miss (<= 2 calls, not 80)
    assert len(connect_calls) <= 2, f"Expected cached SQLite lookups, got {len(connect_calls)} connects"
    assert not any("fake_home" in c for c in connect_calls)


def test_card539_selection_narrows_speed_budget(tmp_path, monkeypatch):
    """Guard: 250 resolve_allowed_tools calls across random skill subsets complete in < 0.5s."""
    from src.application.agent_skills.allowed_tools import resolve_allowed_tools

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    configure_store(data_root=tmp_path / "data")

    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="d",
        system_prompt="p",
        allowed_skill=["capability-authoring", "project-cards", "software-development", "wiki-knowledge"],
    )
    # Warm once
    resolve_allowed_tools(agent)

    t0 = time.perf_counter()
    for _ in range(250):
        allowed = resolve_allowed_tools(agent)
        assert "write_skill_file" in allowed
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"250 resolve_allowed_tools calls took {elapsed:.2f}s (expected < 0.5s)"
