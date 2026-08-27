"""
Unit Tests for Ephemeral Subprocess Sandbox & Skill [REQ-SANDBOX-001 - REQ-SANDBOX-004].
"""

import os
from unittest.mock import patch

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sandbox_skill import SandboxExecutionSkill
from src.application.skills.sandbox_worker import SandboxedSubprocessWorker


@pytest.mark.asyncio
async def test_sandbox_file_provisioning_and_output_extraction():
    input_files = {
        "input/payload.txt": "Hello from input file!",
        "config.json": '{"mode": "test"}',
    }
    python_code = """
import os

with open('input/payload.txt', 'r') as f:
    content = f.read()

print(f"Read: {content}")

os.makedirs('results', exist_ok=True)
with open('results/summary.txt', 'w') as f:
    f.write(f"Processed: {content.upper()}")
"""

    res = await SandboxedSubprocessWorker.run_python_code(
        code=python_code,
        files=input_files,
        read_outputs=["results/summary.txt", "non_existent.txt"],
    )

    assert res.success is True
    assert res.exit_code == 0
    assert "Read: Hello from input file!" in res.stdout
    assert "results/summary.txt" in res.output_files
    assert res.output_files["results/summary.txt"] == "Processed: HELLO FROM INPUT FILE!"
    assert "non_existent.txt" not in res.output_files


@pytest.mark.asyncio
async def test_sandbox_sensitive_environment_scrubbing():
    mock_env = {
        "PATH": os.environ.get("PATH", ""),
        "OPENAI_API_KEY": "sk-secret-key-12345",
        "GITHUB_TOKEN": "ghp_super_secret_token",
        "DATABASE_PASSWORD": "admin_password",
        "SAFE_VARIABLE": "visible_value",
    }

    python_code = """
import os
import json

sensitive_found = [k for k in os.environ if any(x in k.upper() for x in ['KEY', 'TOKEN', 'PASSWORD', 'SECRET'])]
safe_val = os.environ.get('SAFE_VARIABLE', '')

print(json.dumps({'sensitive_count': len(sensitive_found), 'safe_val': safe_val}))
"""

    with patch.dict(os.environ, mock_env, clear=True):
        res = await SandboxedSubprocessWorker.run_python_code(code=python_code)

    assert res.success is True
    assert '"sensitive_count": 0' in res.stdout
    assert '"safe_val": "visible_value"' in res.stdout


@pytest.mark.asyncio
async def test_sandbox_timeout_killing():
    python_code = """
import time
time.sleep(5)
"""
    res = await SandboxedSubprocessWorker.run_python_code(
        code=python_code,
        timeout_seconds=0.5,
    )

    assert res.success is False
    assert res.exit_code == -1
    assert "timed out" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_sandbox_output_stream_capping():
    python_code = """
print("A" * 1500)
"""
    res = await SandboxedSubprocessWorker.run_sandboxed(
        args=[os.sys.executable, "-c", python_code],
        max_output_bytes=500,
    )

    assert res.success is True
    assert res.truncated is True
    assert "[stdout truncated]" in res.stdout
    assert len(res.stdout) < 600


@pytest.mark.asyncio
async def test_sandbox_execution_skill_integration():
    registry = ScopedToolRegistry()
    skill = SandboxExecutionSkill(default_timeout_seconds=10.0)
    skill.register_tools(registry)

    # Tool should be registered
    tool_def = registry.get_tool_definition("execute_code")
    assert tool_def is not None
    assert tool_def.name == "execute_code"
    defs = registry.list_tools()
    assert any(d.name == "execute_code" for d in defs)

    # Execute tool directly from skill
    result = await skill.execute_code(
        code="print('Hello from tool registry!')",
        language="python",
    )

    assert result["success"] is True
    assert "Hello from tool registry!" in result["stdout"]
    assert result["exit_code"] == 0

    # Unsupported language
    bad_lang_result = await skill.execute_code(
        code="echo 123",
        language="unsupported_lang",
    )
    assert bad_lang_result["success"] is False
    assert "Unsupported execution language" in bad_lang_result["stderr"]
