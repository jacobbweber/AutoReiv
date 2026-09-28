"""CARD-562: argument mismatches are a clear tool error listing accepted parameters; nothing runs, nothing is dropped."""

from __future__ import annotations

import asyncio

from src.application.kernel.tool_registry import ScopedToolRegistry, argument_mismatch_error
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile

SCHEMA = {
    "type": "object",
    "properties": {"content": {"type": "string"}, "filename": {"type": "string"}, "count": {"type": "integer"}},
    "required": ["content"],
}


def _setup():
    calls = []

    def handler(content: str, filename: str = "", count: int = 1):
        calls.append((content, filename, count))
        return {"ok": True}

    reg = ScopedToolRegistry()
    reg.register_tool(name="demo_write", description="d", parameters=SCHEMA, handler=handler)
    agent = AgentProfile(id="t", name="t", description="t", system_prompt="t", allowed_skill=["tool:demo_write"])
    return reg, agent, calls


def _run(reg, agent, args):
    return asyncio.run(reg.execute(ToolCall(id="c", name="demo_write", arguments=args), agent))


def test_unknown_argument_is_an_error_not_a_crash_or_a_silent_drop():
    reg, agent, calls = _setup()
    res = _run(reg, agent, {"content": "x", "title": "T"})
    assert res.success is False and calls == []
    assert "Unknown: title." in res.error
    assert "content (string, required)" in res.error and "count (integer)" in res.error
    assert "call it again" in res.error


def test_missing_required_argument_is_named():
    reg, agent, calls = _setup()
    res = _run(reg, agent, {"filename": "a.md"})
    assert res.success is False and calls == [] and "Missing: content." in res.error


def test_good_arguments_still_run():
    reg, agent, calls = _setup()
    res = _run(reg, agent, {"content": "x", "count": 2})
    assert res.success is True and calls == [("x", "", 2)]


def test_handlers_with_kwargs_are_left_alone():
    assert argument_mismatch_error("t", lambda **kw: kw, SCHEMA, {"anything": 1}) is None
