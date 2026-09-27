"""CARD-555: file-writing tools refuse a protected write root (the live QA serve protects the real checkout)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.application.sdlc.paths import PROTECTED_WRITE_ROOTS_ENV, protected_write_error
from src.application.skills.project_file_tools import ProjectFileTools
from src.application.skills.repo_tools import RepoCheckoutTools
from src.application.skills.sysadmin_tools import SysadminTools


@pytest.fixture
def protected(tmp_path, monkeypatch) -> Path:
    real = tmp_path / "real-checkout"
    real.mkdir()
    (real / "a.txt").write_text("original", encoding="utf-8")
    monkeypatch.setenv(PROTECTED_WRITE_ROOTS_ENV, str(real))
    return real


def test_helper_flags_paths_under_a_protected_root(protected, tmp_path):
    assert protected_write_error(protected / "get_weather_tool.json")
    assert protected_write_error(protected)
    assert protected_write_error(tmp_path / "sandbox" / "x.json") is None


def test_no_env_means_no_protection(tmp_path, monkeypatch):
    monkeypatch.delenv(PROTECTED_WRITE_ROOTS_ENV, raising=False)
    assert protected_write_error(tmp_path / "x.json") is None


def test_write_project_file_refuses_the_protected_root(protected, tmp_path):
    res = ProjectFileTools().write_project_file("get_weather_tool.json", "{}", project_root=str(protected))
    assert res["success"] is False and "protected" in res["error"]
    assert not (protected / "get_weather_tool.json").exists()
    other = tmp_path / "sandbox"
    other.mkdir()
    ok = ProjectFileTools().write_project_file("get_weather_tool.json", "{}", project_root=str(other))
    assert ok["success"] is True and (other / "get_weather_tool.json").is_file()


def test_repo_file_write_and_patch_refuse_the_protected_root(protected):
    tools = RepoCheckoutTools()
    res = tools.repo_file_write("new.txt", "x", checkout_root=str(protected))
    assert res["success"] is False and "protected" in res["error"]
    assert not (protected / "new.txt").exists()
    res = tools.repo_file_patch("a.txt", "changed", checkout_root=str(protected))
    assert res["success"] is False and "protected" in res["error"]
    assert (protected / "a.txt").read_text(encoding="utf-8") == "original"
    assert tools.repo_file_read("a.txt", checkout_root=str(protected))["success"] is True  # reads still work


def test_cli_exec_refuses_a_working_directory_in_the_protected_root(protected):
    res = asyncio.run(SysadminTools().run_cli_command("echo hi", cwd=str(protected)))
    assert res["exit_code"] == -1 and "protected" in res["error"]
