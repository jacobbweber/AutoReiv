"""CARD-566 (found live): git_commit accepts paths sent as a JSON-encoded string, as some models do."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.application.skills.git_tools import GitTools

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.js").write_text("1\n", encoding="utf-8")
    (root / "b.js").write_text("1\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "qa@example.invalid")
    _git(root, "config", "user.name", "QA")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: fixture")
    _git(root, "switch", "-q", "-c", "card/1-t")
    (root / "a.js").write_text("2\n", encoding="utf-8")
    (root / "b.js").write_text("2\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("paths", ['["a.js", "b.js"]', "a.js, b.js", ["a.js", "b.js"]])
def test_paths_as_json_string_or_comma_list_commit_both_files(repo, paths):
    res = GitTools(root_resolver=lambda _=None: repo).git_commit(message="fix: both", paths=paths)
    assert res["success"] is True, res
    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == ["a.js", "b.js"]


def test_a_single_path_string_commits_only_that_file(repo):
    res = GitTools(root_resolver=lambda _=None: repo).git_commit(message="fix: one", paths="a.js")
    assert res["success"] is True, res
    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == ["a.js"]
