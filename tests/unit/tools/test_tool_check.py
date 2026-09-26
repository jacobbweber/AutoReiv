"""CARD-511: check a Developer-built native tool once in the sandbox before it is registered.

Tests 1-12 of the card plan, plus the Developer guidance text (REQ-511-014).
Real sandbox subprocesses; no LLM.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.application.skills.sandbox_worker import SandboxedSubprocessWorker, SubprocessResult
from src.application.tools import tool_check
from src.application.tools.tool_check import (
    ToolCheckService,
    build_sample_arguments,
    detect_path_safety_violation,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
GOOD = "def run(text='', **kw):\n    return {'echo': text}\n"


class _SpyRunner:
    def __init__(self):
        self.calls = []

    async def __call__(self, args, **kwargs):
        self.calls.append(kwargs)
        return await SandboxedSubprocessWorker.run_sandboxed(args, **kwargs)


async def test_1_good_tool_passes_all_three_stages():
    result = await ToolCheckService().check_native(name="c511_good", code=GOOD, parameters=SCHEMA, risk_level="medium")
    assert result.status == "passed", result.error
    assert result.ok is True
    assert [stage["name"] for stage in result.stages] == ["static", "import", "sample_call"]
    assert all(stage["ok"] for stage in result.stages)
    assert result.sample_arguments == {"text": ""}
    assert result.checked_at
    assert result.operator_message().startswith("Checked: c511_good")


async def test_2_syntax_error_fails_static_without_running_the_sandbox():
    runner = AsyncMock()
    result = await ToolCheckService(runner=runner).check_native(
        name="c511_syntax", code="def run(**kw):\n    return (\n", parameters={}, risk_level="low"
    )
    assert result.status == "failed"
    assert result.stage == "static"
    assert "SyntaxError" in result.error
    assert "line" in result.error
    runner.assert_not_called()
    assert result.operator_message().startswith("Not registered: c511_syntax failed the static check")


@pytest.mark.parametrize(
    "code",
    [
        "class T:\n    def run(self, **kw):\n        return 1\n",
        "# def run(**kw)\nx = 1\n",
    ],
)
async def test_3_run_must_be_a_module_level_function(code):
    result = await ToolCheckService(runner=AsyncMock()).check_native(name="c511_norun", code=code, parameters={}, risk_level="low")
    assert result.status == "failed"
    assert result.stage == "static"
    assert "module-level" in result.error


async def test_4_import_error_fails_the_import_stage():
    code = "import nonexistent_c511_mod\n\ndef run(**kw):\n    return 1\n"
    result = await ToolCheckService().check_native(name="c511_import", code=code, parameters={}, risk_level="low")
    assert result.status == "failed"
    assert result.stage == "import"
    assert "ModuleNotFoundError: No module named 'nonexistent_c511_mod'" in result.error
    assert result.error.splitlines()[0].startswith("ModuleNotFoundError")


async def test_5_raising_tool_fails_the_sample_call():
    code = "def run(**kw):\n    raise ValueError('c511 deliberate failure')\n"
    result = await ToolCheckService().check_native(name="c511_raises", code=code, parameters={}, risk_level="low")
    assert result.status == "failed"
    assert result.stage == "sample_call"
    assert result.error.splitlines()[0] == "ValueError: c511 deliberate failure"
    assert len(result.error) <= 2000


async def test_6_non_json_result_fails_the_sample_call():
    code = "def run(**kw):\n    return object()\n"
    result = await ToolCheckService().check_native(name="c511_obj", code=code, parameters={}, risk_level="low")
    assert result.status == "failed"
    assert result.stage == "sample_call"
    assert "JSON" in result.error


async def test_7_slow_tool_times_out():
    code = "import time\n\ndef run(**kw):\n    time.sleep(30)\n    return 1\n"
    result = await ToolCheckService(call_timeout=1.0).check_native(name="c511_slow", code=code, parameters={}, risk_level="low")
    assert result.status == "failed"
    assert result.stage == "sample_call"
    assert "timed out after 1 s" in result.error


async def test_8_path_traversal_fails_and_eval_only_warns():
    trav = await ToolCheckService(runner=AsyncMock()).check_native(
        name="c511_trav", code="def run(**kw):\n    return open('../x').read()\n", parameters={}, risk_level="low"
    )
    assert trav.status == "failed"
    assert trav.stage == "static"
    assert "Path traversal" in trav.error

    ev = await ToolCheckService().check_native(
        name="c511_eval", code="def run(**kw):\n    return eval('1+1')\n", parameters={}, risk_level="low"
    )
    assert ev.status == "passed", ev.error
    assert any("eval" in warning for warning in ev.warnings)


async def test_9_high_risk_and_requested_skip_do_not_make_the_call():
    spy = _SpyRunner()
    high = await ToolCheckService(runner=spy).check_native(name="c511_high", code=GOOD, parameters=SCHEMA, risk_level="high")
    assert high.status == "checked_without_call"
    assert high.ok is True
    assert high.skip_reason == "high risk: sample call skipped"
    assert len(spy.calls) == 1  # import stage only
    assert "args.json" not in spy.calls[0]["files"]
    assert high.operator_message() == "Checked without a sample call: high risk: sample call skipped."

    spy2 = _SpyRunner()
    asked = await ToolCheckService(runner=spy2).check_native(
        name="c511_key", code=GOOD, parameters=SCHEMA, risk_level="low", sample_call="skip", skip_reason="needs an API key"
    )
    assert asked.status == "checked_without_call"
    assert asked.skip_reason == "needs an API key"
    assert len(spy2.calls) == 1

    with pytest.raises(ValueError, match="skip_reason"):
        await ToolCheckService().check_native(name="c511_x", code=GOOD, parameters=SCHEMA, risk_level="low", sample_call="skip")


def test_10_sample_arguments_are_built_from_the_schema():
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "integer"},
            "c": {"type": "number"},
            "d": {"type": "boolean"},
            "e": {"type": "array"},
            "f": {"type": "object"},
            "g": {"type": "string", "enum": ["x", "y"]},
            "h": {"type": "integer", "default": 5},
            "i": {"type": "string"},
        },
        "required": ["a", "b", "c", "d", "e", "f", "g", "h"],
    }
    assert build_sample_arguments(schema) == {"a": "", "b": 0, "c": 0, "d": False, "e": [], "f": {}, "g": "x", "h": 5}
    assert build_sample_arguments({}) == {}
    assert build_sample_arguments(None) == {}


async def test_10b_sample_arguments_that_break_the_schema_are_refused_before_running():
    runner = AsyncMock()
    svc = ToolCheckService(runner=runner)
    wrong_type = await svc.check_native(name="c511_s", code=GOOD, parameters=SCHEMA, risk_level="low", sample_arguments={"text": 5})
    assert wrong_type.status == "failed"
    assert wrong_type.stage == "sample_input"
    missing = await svc.check_native(name="c511_s", code=GOOD, parameters=SCHEMA, risk_level="low", sample_arguments={})
    assert missing.status == "failed"
    assert "text" in missing.error
    runner.assert_not_called()

    used = await ToolCheckService().check_native(
        name="c511_s", code=GOOD, parameters=SCHEMA, risk_level="low", sample_arguments={"text": "hello"}
    )
    assert used.status == "passed"
    assert used.sample_arguments == {"text": "hello"}


async def test_11_sandbox_that_cannot_start_is_could_not_run():
    async def launch_error(args, **kwargs):
        return SubprocessResult(stdout="", stderr="[WinError 2]", exit_code=-1, success=False, error="Subprocess launch error: [WinError 2]")

    result = await ToolCheckService(runner=launch_error).check_native(name="c511_nos", code=GOOD, parameters={}, risk_level="low")
    assert result.status == "could_not_run"
    assert result.ok is False
    message = result.operator_message()
    assert message.startswith("The check could not run:")
    assert "Nothing was registered; try again." in message

    async def boom(args, **kwargs):
        raise OSError("no interpreter")

    raised = await ToolCheckService(runner=boom).check_native(name="c511_nos", code=GOOD, parameters={}, risk_level="low")
    assert raised.status == "could_not_run"
    assert "no interpreter" in raised.error


def test_12_tool_check_has_no_factory_imports_and_owns_path_safety():
    source = (ROOT / "src/application/tools/tool_check.py").read_text(encoding="utf-8")
    imported = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    forbidden = ("agent_training_factory", "verification_battery", "tool_synthesizer", "factory_packets")
    assert not [name for name in imported if any(bad in name for bad in forbidden)]

    from src.application.orchestration import verification_battery

    assert verification_battery.detect_path_safety_violation is detect_path_safety_violation
    assert tool_check.detect_path_safety_violation("open('../x')")


def test_14_developer_guidance_mentions_the_check():
    native_skill = (ROOT / "platform-packs/developer/skills/native-tool-engineering/SKILL.md").read_text(encoding="utf-8")
    mcp_skill = (ROOT / "platform-packs/developer/skills/mcp-engineering/SKILL.md").read_text(encoding="utf-8")
    for text in (native_skill, mcp_skill):
        assert "sample_arguments" in text
        assert "sample_call" in text
        assert "Not registered" in text

    from src.application.tools.developer_mediation import build_packet, format_developer_prompt

    prompt = format_developer_prompt(build_packet("create", {"tool_name": "x_tool", "behavior": "Do x."}))
    assert "sample_arguments" in prompt
    assert "Not registered" in prompt
