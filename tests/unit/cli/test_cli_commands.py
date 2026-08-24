"""
Unit tests for AutoReiv Unified CLI Commands [REQ-DEPLOY-001, REQ-DEPLOY-002].
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.cli.main import build_parser, main
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
        ["serve", "--port", "9000", "--host", "127.0.0.1", "--db-path", "./test.db", "--wiki-path", "./test_wiki"]
    )
    assert args.command == "serve"
    assert args.port == 9000
    assert args.host == "127.0.0.1"
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
    args = parser.parse_args(["chat", "general-assistant"])
    assert args.command == "chat"
    assert args.agent_id == "general-assistant"


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
            agent_id="general-assistant",
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
        ret = main(["chat", "general-assistant", "--db-path", ":memory:"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Interactive Session" in captured.out
        assert "Hello! How can I assist you?" in captured.out
