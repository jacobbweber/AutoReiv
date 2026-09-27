"""CARD-555: the live QA throwaway serve never writes into the real checkout.

REQ-555-001: the serve runs from a disposable git worktree outside the real checkout (checkout tools and cwd point there).
REQ-555-002: the real checkout is a protected write root for the serve (AUTOREIV_PROTECTED_WRITE_ROOTS).
REQ-555-003: a run fails if the real checkout's git status changes while it runs, and says so in summary.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import live_qa  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "qa@example.invalid")
    _git(repo, "config", "user.name", "QA")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / "a.txt").write_text("committed\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def test_sandbox_checkout_is_outside_the_real_checkout(tmp_path):
    sandbox = live_qa.sandbox_checkout_dir({})
    assert not live_qa.guard.is_within(sandbox, live_qa.CHECKOUT)
    assert live_qa.checkout_problems(live_qa.CHECKOUT / "scratch" / "live_qa_checkout", live_qa.CHECKOUT)
    assert live_qa.checkout_problems(live_qa.CHECKOUT, live_qa.CHECKOUT)
    assert live_qa.checkout_problems(tmp_path / "sandbox", live_qa.CHECKOUT) == []


def test_serve_launch_runs_from_the_sandbox_and_protects_the_real_checkout(tmp_path):
    sandbox = tmp_path / "sandbox"
    cmd, cwd, env = live_qa.serve_launch(8770, {"PATH": "p", "PYTHONPATH": "old"}, sandbox, live_qa.CHECKOUT)
    assert cwd == str(sandbox)
    assert env["AUTOREIV_CHECKOUT_ROOT"] == str(sandbox)
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(sandbox)
    assert str(live_qa.CHECKOUT) in env["AUTOREIV_PROTECTED_WRITE_ROOTS"].split(os.pathsep)
    assert "8770" in cmd and "127.0.0.1" in cmd
    assert env["PATH"] == "p"


def test_prepare_sandbox_checkout_copies_tracked_work_and_leaves_the_repo_alone(tmp_path):
    repo = _repo(tmp_path)
    (repo / "a.txt").write_text("uncommitted edit\n", encoding="utf-8")
    before = live_qa.git_status(repo)
    sandbox = live_qa.prepare_sandbox_checkout(repo, tmp_path / "sandbox")
    assert (sandbox / "a.txt").read_text(encoding="utf-8") == "uncommitted edit\n"
    (sandbox / "get_weather_tool.json").write_text("{}", encoding="utf-8")
    assert live_qa.git_status(repo) == before
    again = live_qa.prepare_sandbox_checkout(repo, tmp_path / "sandbox")  # a stale sandbox is replaced
    assert not (again / "get_weather_tool.json").exists()
    live_qa.remove_sandbox_checkout(repo, again)
    assert not again.exists()
    assert _git(repo, "worktree", "list").strip().count("\n") == 0
    assert live_qa.git_status(repo) == before


def test_checkout_changes_lists_what_appeared_or_went_away():
    before = " M a.txt"
    after = " M a.txt\n?? get_weather_tool.json"
    assert live_qa.checkout_changes(before, after) == ["?? get_weather_tool.json"]
    assert live_qa.checkout_changes(after, after) == []


def _fake_run(monkeypatch, tmp_path, statuses):
    seq = iter(statuses)
    last = {"v": statuses[-1]}

    def status(_checkout=None):
        try:
            last["v"] = next(seq)
        except StopIteration:
            pass
        return last["v"]

    monkeypatch.setattr(live_qa, "list_journeys", lambda *a, **k: ["card-520-teach-needs-tool"])
    monkeypatch.setattr(live_qa, "start", lambda *a, **k: 0)
    monkeypatch.setattr(live_qa, "stop", lambda *a, **k: True)
    monkeypatch.setattr(live_qa, "git_status", status)
    monkeypatch.setattr(live_qa.subprocess, "call", lambda *a, **k: 0)
    monkeypatch.setenv("AUTOREIV_QA_REPORT_DIR", str(tmp_path))
    out = tmp_path / "card-555"
    out.mkdir()
    (out / "summary.md").write_text("# AutoReiv live QA\n", encoding="utf-8")
    return out


def test_run_fails_when_the_real_checkout_changes(monkeypatch, tmp_path, capsys):
    out = _fake_run(monkeypatch, tmp_path, ["", "?? get_weather_tool.json"])
    rc = live_qa.main(["run", "--journeys", "card-520", "--viewports", "desktop", "--card", "CARD-555"])
    assert rc == live_qa.EXIT_CHECKOUT_CHANGED
    assert "real checkout changed" in capsys.readouterr().out
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "Real checkout guard" in summary and "get_weather_tool.json" in summary and "FAIL" in summary


def test_run_passes_when_the_real_checkout_is_unchanged(monkeypatch, tmp_path):
    out = _fake_run(monkeypatch, tmp_path, [" M a.txt", " M a.txt"])
    rc = live_qa.main(["run", "--journeys", "card-520", "--viewports", "desktop", "--card", "CARD-555"])
    assert rc == 0
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "Real checkout guard" in summary and "unchanged" in summary
