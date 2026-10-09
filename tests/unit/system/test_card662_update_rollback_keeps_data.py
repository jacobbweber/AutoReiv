"""CARD-662: the git update path and its rollback never wipe the user data folder.

Hermetic: temporary bare origin + clone + a throwaway data folder under tmp_path.
NEVER touches the live checkout or a real data folder.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import NoOpRestarter
from src.application.system.update_service import UpdateService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.slow

MARK = "card662-marker"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return (res.stdout or "").strip()


def _ident(repo: Path) -> None:
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")


def _snapshot(data: Path) -> dict[str, str]:
    """Hash of every file in the data folder except update backups."""
    out: dict[str, str] = {}
    for p in sorted(data.rglob("*")):
        rel = p.relative_to(data).as_posix()
        if p.is_file() and not rel.startswith("backups/") and not rel.endswith(("-wal", "-shm")):
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@pytest.fixture
def setup(tmp_path: Path):
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    other = tmp_path / "other"
    _git(tmp_path, "init", "--bare", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    _ident(work)
    (work / "README.md").write_text("v1\n", encoding="utf-8")
    (work / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "v1")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")
    v1 = _git(work, "rev-parse", "HEAD")
    # The prior release stays reachable as a branch: that is the rollback target.
    _git(work, "push", "origin", f"{v1}:refs/heads/release-1.0.0")

    _git(tmp_path, "clone", "-b", "main", str(bare), str(other))
    _ident(other)
    (other / "README.md").write_text("v2\n", encoding="utf-8")
    _git(other, "commit", "-am", "v2")
    _git(other, "push", "origin", "main")

    # A data folder that already holds real-looking user data.
    data = tmp_path / "data"
    (data / "database").mkdir(parents=True)
    (data / "wiki" / "00_Inbox").mkdir(parents=True)
    (data / "agents" / "my-agent").mkdir(parents=True)
    (data / "wiki" / "00_Inbox" / "marker.md").write_text(f"# {MARK}\n", encoding="utf-8")
    (data / "agents" / "my-agent" / "agent.yaml").write_text(f"id: my-agent\nnote: {MARK}\n", encoding="utf-8")
    db = data / "database" / "autoreiv.db"
    store = SQLiteStateStore(str(db))
    store.initialize_db()
    session = store.create_session(agent_id="default", title=MARK)

    svc = UpdateService(
        state_store=store,
        repo_root=str(work),
        data_dir=str(data),
        restarter=NoOpRestarter(),
        busy_detector=BusyDetector(
            chat_stream_checker=lambda: False,
            routine_checker=lambda: False,
            studio_job_checker=lambda: False,
        ),
        dep_installer=lambda root: (True, "ok"),
        serve_host="127.0.0.1",
        serve_port=8799,
    )
    return {"svc": svc, "data": data, "db": db, "work": work, "session_id": session.id, "v1": v1}


def _assert_marked_data_intact(env, before: dict[str, str]) -> None:
    data = env["data"]
    assert (data / "wiki" / "00_Inbox" / "marker.md").read_text(encoding="utf-8") == f"# {MARK}\n"
    assert MARK in (data / "agents" / "my-agent" / "agent.yaml").read_text(encoding="utf-8")
    after = _snapshot(data)
    for rel, digest in before.items():
        if rel.startswith("database/"):
            continue  # the live DB also records update history; checked by content below
        assert after.get(rel) == digest, f"{rel} changed or vanished"
    # Restart = a fresh store on the same file (schema init must not wipe rows).
    reopened = SQLiteStateStore(str(env["db"]))
    reopened.initialize_db()
    got = reopened.get_session(env["session_id"])
    assert got is not None and got.title == MARK


def test_git_update_keeps_data_and_takes_a_backup(setup):
    env = setup
    before = _snapshot(env["data"])
    result = env["svc"].apply_update(trigger="manual", restart=False)
    assert result.success, result.message
    assert result.new_commit != result.previous_commit
    assert result.backup_path and Path(result.backup_path).is_file()
    assert Path(result.backup_path).parent == env["data"] / "backups"
    _assert_marked_data_intact(env, before)


def test_rollback_to_prior_release_branch_keeps_data(setup):
    env = setup
    before = _snapshot(env["data"])
    assert env["svc"].apply_update(trigger="manual", restart=False).success
    rolled = env["svc"].switch_branch("release-1.0.0", restart=False)
    assert rolled.success, rolled.message
    assert _git(env["work"], "rev-parse", "HEAD") == env["v1"]
    _assert_marked_data_intact(env, before)
    # And forward again.
    forward = env["svc"].switch_branch("main", restart=False)
    assert forward.success, forward.message
    _assert_marked_data_intact(env, before)


def test_data_folder_lives_outside_the_checkout(setup):
    """Git operations only touch the checkout; the data folder is never inside it."""
    env = setup
    work = env["work"].resolve()
    data = env["data"].resolve()
    assert work not in data.parents and data != work


def test_install_doc_explains_update_and_rollback_per_path():
    """CARD-662: the install doc says what update and rollback mean for git and Docker, and that both keep data."""
    doc = (Path(__file__).resolve().parents[3] / "docs" / "install-and-uninstall.md").read_text(encoding="utf-8")
    assert "## Update and rollback" in doc
    section = doc.split("## Update and rollback", 1)[1]
    for needle in ("Settings", "pre-update", "release branch", "image tag", "same volume", "keeps your data"):
        assert needle in section, needle
