"""CARD-672: the suite never reaches a real model, and a stuck test fails the run instead of hanging it.

The full suite and the release preflight hung at ~99% on Jarvis: test_gaps_api called the model behind whatever
OLLAMA_HOST/.env said, and a host that accepts the connection but never answers held the test for the 30 min
helper timeout at zero CPU.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[2]

REMOTE_PROVIDER_VARS = (
    "VLLM_HOST",
    "VLLM_BASE_URL",
    "LMSTUDIO_HOST",
    "LMSTUDIO_BASE_URL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "TOGETHER_API_KEY",
)


def test_session_points_ollama_at_a_closed_local_port():
    from conftest import HERMETIC_OLLAMA_HOST

    assert HERMETIC_OLLAMA_HOST.startswith("http://127.0.0.1:")
    assert os.environ.get("OLLAMA_HOST") == HERMETIC_OLLAMA_HOST


def test_session_blanks_remote_providers_so_dotenv_cannot_fill_them():
    for name in REMOTE_PROVIDER_VARS:
        assert os.environ.get(name) == "", name


def test_env_gateway_only_has_the_closed_local_ollama():
    from conftest import HERMETIC_OLLAMA_HOST
    from src.infrastructure.gateway.factory import GatewayProviderFactory

    gw = GatewayProviderFactory.create_gateway()
    providers = getattr(gw, "_providers")
    assert set(providers) == {"ollama"}
    assert providers["ollama"].base_url.rstrip("/") == HERMETIC_OLLAMA_HOST


def _run_child_pytest(tmp_path: Path, body: str, hang_seconds: str) -> tuple[subprocess.CompletedProcess, float]:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_child.py").write_text(textwrap.dedent(body), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TESTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["AUTOREIV_TEST_HANG_SECONDS"] = hang_seconds
    start = time.monotonic()
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "hang_watchdog", "-p", "no:cacheprovider", "-q", "test_child.py"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return res, time.monotonic() - start


@pytest.mark.slow
def test_watchdog_ends_a_stuck_test_with_a_traceback(tmp_path):
    res, took = _run_child_pytest(
        tmp_path,
        """
        import time

        def test_stuck():
            time.sleep(90)
        """,
        "3",
    )
    out = res.stdout + res.stderr
    assert res.returncode != 0, out
    assert took < 60, took
    assert "Timeout" in out and "test_stuck" in out, out


@pytest.mark.slow
def test_watchdog_leaves_normal_tests_alone(tmp_path):
    res, _ = _run_child_pytest(
        tmp_path,
        """
        import time

        def test_quick():
            time.sleep(0.2)

        def test_quick_again():
            assert True
        """,
        "3",
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "2 passed" in res.stdout
