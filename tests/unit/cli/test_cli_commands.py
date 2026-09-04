"""
Unit tests for AutoReiv Unified CLI Commands [REQ-DEPLOY-001, REQ-DEPLOY-002].
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.cli.main import apply_storage_args, build_parser, main
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.domain.routines.models import RoutineRun, RoutineStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def mem_store():
    store = SQLiteStateStore(":memory:")
    store.initialize_db()
    return store


def test_cli_parser_subcommands():
    parser = build_parser()

    # Serve
    args = parser.parse_args(
        [
            "serve",
            "--port",
            "9000",
            "--host",
            "127.0.0.1",
            "--data-dir",
            "./user-data",
            "--db-path",
            "./test.db",
            "--wiki-path",
            "./test_wiki",
        ]
    )
    assert args.command == "serve"
    assert args.port == 9000
    assert args.host == "127.0.0.1"
    assert args.data_dir == "./user-data"
    assert args.db_path == "./test.db"
    assert args.wiki_path == "./test_wiki"

    # Status
    args = parser.parse_args(["status"])
    assert args.command == "status"

    # Routine list
    args = parser.parse_args(["routine", "list"])
    assert args.command == "routine"
    assert args.routine_command == "list"

    # Routine run
    args = parser.parse_args(["routine", "run", "morning-briefing"])
    assert args.command == "routine"
    assert args.routine_command == "run"
    assert args.routine_id == "morning-briefing"

    # Chat
    args = parser.parse_args(["chat"])
    assert args.command == "chat"
    assert args.agent_id == "assistant"

    args = parser.parse_args(["chat", "autoreiv"])
    assert args.command == "chat"
    assert args.agent_id == "autoreiv"

    args = parser.parse_args(["backup"])
    assert args.command == "backup"
    assert args.dest is None

    args = parser.parse_args(["backup", "out.zip"])
    assert args.command == "backup"
    assert args.dest == "out.zip"

    args = parser.parse_args(["restore", "out.zip", "--yes"])
    assert args.command == "restore"
    assert args.src == "out.zip"
    assert args.yes is True


def test_cli_status_command(mem_store, capsys):
    ret = main(["status", "--db-path", ":memory:"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "AutoReiv System Status" in captured.out
    assert "Host RAM" in captured.out
    assert "Registered Agents" in captured.out


def test_cli_routine_list_and_run(mem_store, capsys):
    # Routine list
    ret = main(["routine", "list", "--db-path", ":memory:"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "morning-briefing" in captured.out

    # Mock execute_routine for routine run
    with patch("src.cli.main.RoutineExecutor.execute_routine", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = RoutineRun(
            id="run-123",
            routine_id="morning-briefing",
            agent_id="assistant",
            status=RoutineStatus.SUCCESS,
            output="Morning Briefing Completed: 3 tasks active.",
            duration_ms=120.5,
        )
        ret = main(["routine", "run", "morning-briefing", "--db-path", ":memory:"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Morning Briefing Completed" in captured.out


def test_cli_chat_command(capsys):
    # Mock kernel.stream_turn to return simulated tokens
    async def mock_stream(*args, **kwargs):
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Hello! How can I assist you?")
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Hello! How can I assist you?")

    with (
        patch("src.cli.main.AgentKernel.stream_turn", side_effect=mock_stream),
        patch("builtins.input", side_effect=["Hello assistant", "exit"]),
    ):
        ret = main(["chat", "assistant", "--db-path", ":memory:"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Interactive Session" in captured.out
        assert "Hello! How can I assist you?" in captured.out


def test_cli_backup_and_restore_round_trip(tmp_path, monkeypatch, capsys):
    import sqlite3

    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    data = tmp_path / "data"
    data.mkdir()
    conn = sqlite3.connect(str(data / "autoreiv.db"))
    conn.execute("CREATE TABLE notes (body TEXT)")
    conn.execute("INSERT INTO notes VALUES ('cli-v1')")
    conn.commit()
    conn.close()
    (data / "wiki").mkdir()
    (data / "wiki" / "inbox.md").write_text("cli-wiki-v1", encoding="utf-8")
    dest = tmp_path / "backup.zip"

    ret = main(["backup", str(dest), "--data-dir", str(data)])
    assert ret == 0
    assert dest.is_file()
    captured = capsys.readouterr()
    assert "Wrote backup" in captured.out

    (data / "wiki" / "inbox.md").write_text("changed", encoding="utf-8")
    ret = main(["restore", str(dest), "--data-dir", str(data)])
    assert ret == 1
    assert (data / "wiki" / "inbox.md").read_text(encoding="utf-8") == "changed"

    ret = main(["restore", str(dest), "--yes", "--data-dir", str(data)])
    assert ret == 0
    assert (data / "wiki" / "inbox.md").read_text(encoding="utf-8") == "cli-wiki-v1"
    db_file = data / "database" / "autoreiv.db" if (data / "database" / "autoreiv.db").is_file() else data / "autoreiv.db"
    conn = sqlite3.connect(str(db_file))
    assert conn.execute("SELECT body FROM notes").fetchone()[0] == "cli-v1"
    conn.close()


def test_argv_without_db_path_resolves_to_data_dir_db(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    dest = tmp_path / "user-data"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    monkeypatch.setattr("src.infrastructure.data.resolver.repo_root", lambda: tmp_path / "co")
    (tmp_path / "co").mkdir()
    args = build_parser().parse_args(["serve"])
    assert args.db_path is None
    paths = apply_storage_args(args)
    assert paths.db_path == dest / "database" / "autoreiv.db"
    assert paths.wiki_path == dest / "wiki"
    assert paths.skills_path == dest / "skills"

