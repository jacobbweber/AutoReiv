"""
Unit tests for CARD-391: Developer Agent and Projects Studio Workspace Integration.
Verifies:
- [REQ-391-001]: Setting active project dynamically scopes Developer tools.
- [REQ-391-003]: Developer project file tools resolve relative to active project root.
- [REQ-391-004]: Jailed file operations reject path escaping outside active project root.
- Prompt grounding automatically includes active project path, AGENTS.md, and work cards.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.git_tools import GitTools
from src.application.skills.project_file_tools import ProjectFileTools
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_developer_tools_resolve_active_project_root():
    """Developer project file tools dynamically resolve relative paths against active project."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "my_project"
        proj_root.mkdir(parents=True)
        (proj_root / "src").mkdir()
        (proj_root / "src" / "main.py").write_text("print('hello world')", encoding="utf-8")

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="my_project", path=str(proj_root))

        tools = ProjectFileTools(root_resolver=proj_svc.resolve_root)

        # 1. list_project_dir
        list_res = tools.list_project_dir(path="src")
        assert list_res["success"] is True
        assert list_res["project_root"] == str(proj_root.resolve())
        entry_names = [e["name"] for e in list_res["entries"]]
        assert "main.py" in entry_names

        # 2. read_project_file
        read_res = tools.read_project_file(path="src/main.py")
        assert read_res["success"] is True
        assert read_res["content"] == "print('hello world')"
        assert read_res["project_root"] == str(proj_root.resolve())

        # 3. write_project_file
        write_res = tools.write_project_file(path="src/utils.py", content="def add(a, b): return a + b")
        assert write_res["success"] is True
        assert (proj_root / "src" / "utils.py").read_text(encoding="utf-8") == "def add(a, b): return a + b"


def test_developer_tools_reject_path_escaping_active_project():
    """Negative assertion: project tools strictly reject directory traversal outside active project [REQ-391-004]."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "jailed_project"
        proj_root.mkdir(parents=True)

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="jailed_project", path=str(proj_root))

        tools = ProjectFileTools(root_resolver=proj_svc.resolve_root)

        # Attempt to write outside project root using relative traversal
        write_escape = tools.write_project_file(path="../escaped.txt", content="malicious")
        assert write_escape["success"] is False
        assert "escapes project_root" in write_escape["error"]

        # Attempt to read outside project root
        read_escape = tools.read_project_file(path="../../etc/passwd")
        assert read_escape["success"] is False
        assert "escapes project_root" in read_escape["error"]


def test_git_tools_run_against_active_project_root():
    """GitTools resolves its working directory from the active project root."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "git_project"
        proj_root.mkdir(parents=True)

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="git_project", path=str(proj_root))

        git_tools = GitTools(root_resolver=proj_svc.resolve_root)
        status_res = git_tools.git_status()
        # Not a git repository yet, but properly targeted to git_project
        assert status_res["success"] is False
        assert "not a git repository" in status_res["error"].lower()


def test_developer_agent_kernel_prompt_grounding_with_active_project():
    """AgentKernel injects active project path, AGENTS.md, and work cards into Developer system prompt."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "grounded_project"
        proj_root.mkdir(parents=True)
        (proj_root / "AGENTS.md").write_text("# Project Constitution\n", encoding="utf-8")
        cards_dir = proj_root / "docs" / "cards"
        cards_dir.mkdir(parents=True)
        (cards_dir / "CARD-101-sample-task.md").write_text("# CARD-101\n", encoding="utf-8")

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="grounded_project", path=str(proj_root))

        registry = ScopedToolRegistry()
        gateway = MagicMock()
        telemetry = MagicMock()
        kernel = AgentKernel(
            gateway=gateway,
            tool_registry=registry,
            telemetry=telemetry,
            state_store=store,
        )

        dev_agent = AgentProfile(
            id="developer",
            name="Developer",
            description="Lead Software Engineer",
            system_prompt="You are the Lead Software Engineer.",
        )

        assembled = kernel._build_effective_system_message(dev_agent).content
        assert "## Active Selected Project" in assembled
        assert "grounded_project" in assembled
        assert str(proj_root) in assembled
        assert "Governance: AGENTS.md present at project root." in assembled
        assert "Active Work Cards (1 total): Recent: CARD-101-sample-task.md" in assembled
        assert "Use write_project_file, read_project_file, and list_project_dir" in assembled


def test_non_project_agent_excludes_active_project_from_prompt():
    """Negative assertion: Non-project agents (e.g. Tutor) do NOT receive project paths or cards in system prompt."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "isolated_project"
        proj_root.mkdir(parents=True)
        (proj_root / "AGENTS.md").write_text("# Project Constitution\n", encoding="utf-8")

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="isolated_project", path=str(proj_root))

        registry = ScopedToolRegistry()
        gateway = MagicMock()
        telemetry = MagicMock()
        kernel = AgentKernel(
            gateway=gateway,
            tool_registry=registry,
            telemetry=telemetry,
            state_store=store,
        )

        tutor_agent = AgentProfile(
            id="tutor",
            name="Tutor",
            description="Socratic Tutor",
            system_prompt="You are a patient Socratic tutor.",
            allowed_tool_names=["read_wiki_document", "search_wiki"],
        )

        assembled = kernel._build_effective_system_message(tutor_agent).content
        assert "## Active Selected Project" not in assembled
        assert "isolated_project" not in assembled
        assert str(proj_root) not in assembled


def test_read_only_project_agent_receives_read_only_guidance():
    """Agents with read-only project tools receive project context with inspection guidance only."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_root = Path(tmp_dir) / "review_project"
        proj_root.mkdir(parents=True)

        store = SQLiteStateStore(db_path=":memory:")
        store.initialize_db()
        proj_svc = ProjectsService(store=store)
        proj_svc.set_selected(slug="review_project", path=str(proj_root))

        registry = ScopedToolRegistry()
        gateway = MagicMock()
        telemetry = MagicMock()
        kernel = AgentKernel(
            gateway=gateway,
            tool_registry=registry,
            telemetry=telemetry,
            state_store=store,
        )

        reviewer_agent = AgentProfile(
            id="reviewer",
            name="Code Reviewer",
            description="Read-only reviewer",
            system_prompt="You review code for quality.",
            allowed_tool_names=["read_project_file", "list_project_dir"],
        )

        assembled = kernel._build_effective_system_message(reviewer_agent).content
        assert "## Active Selected Project" in assembled
        assert "review_project" in assembled
        assert "Use read_project_file and list_project_dir to inspect and review files inside this project." in assembled
        assert "write_project_file" not in assembled
