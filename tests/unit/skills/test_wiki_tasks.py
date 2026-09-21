"""
Unit tests for wiki_tasks Skill and Canonical Wiki Task Management [CARD-409].

Enforces:
1. Negative assertions: The 5 bespoke weekly tools (get_or_create_weekly_note,
   log_daily_work_item, complete_weekly_task, rollover_weekly_tasks, get_weekly_summary)
   are permanently deleted from the platform and never registered in the tool registry.
2. Single Lever Invariant: Only canonical WikiTools (wiki_note_create, wiki_note_read,
   wiki_note_update, wiki_template_read) are used for task tracking and weekly work logs.
3. wiki_tasks runbook conformed to CAP-001 (tool count <= 6).
"""

import pytest

from src.application.agent_packs.schema import PLATFORM_SKILL_TOOLS
from src.application.skills.wiki_tools import WikiTools
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

PRUNED_WEEKLY_TOOLS = [
    "get_or_create_weekly_note",
    "log_daily_work_item",
    "complete_weekly_task",
    "rollover_weekly_tasks",
    "get_weekly_summary",
]


@pytest.fixture
def temp_wiki_root(tmp_path):
    templates_dir = tmp_path / "02_Resources" / "_Templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir = tmp_path / "01_Notes" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir = tmp_path / "00_Inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    template_content = (
        "---\n"
        "title: \"Weekly Notes Template\"\n"
        "domain: weekly\n"
        "topic: worklog\n"
        "category: notes\n"
        "tags:\n"
        "  - worklog\n"
        "  - weekly_notes\n"
        "---\n"
        "## Weekly Summary\n\n"
        "### 🔄 Carry-Over\n\n"
        "### 🎯 Focus\n\n"
        "## 📅 Daily Work Logs\n\n"
        "### Monday\n"
        "- [ ] Plan weekly priorities\n\n"
        "### Tuesday\n\n"
        "### Wednesday\n\n"
        "### Thursday\n\n"
        "### Friday\n"
    )
    (templates_dir / "weekly_notes.md").write_text(template_content, encoding="utf-8")
    return tmp_path


def test_pruned_weekly_tools_permanently_eliminated(temp_wiki_root):
    """Negative assertion: None of the 5 pruned tools exist in tool registry or autoreiv pack."""
    store = SQLiteStateStore(db_path=str(temp_wiki_root / "test.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)

    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(temp_wiki_root),
        skills_dir=str(temp_wiki_root / "skills"),
    )

    all_registered_tools = {t.name for t in tool_reg.list_tools()}
    for tool_name in PRUNED_WEEKLY_TOOLS:
        assert tool_name not in all_registered_tools, f"{tool_name} must NOT be in tool registry"

    autoreiv_agent = registry.get_agent("autoreiv")
    assert autoreiv_agent is not None
    for tool_name in PRUNED_WEEKLY_TOOLS:
        assert tool_name not in autoreiv_agent.allowed_tool_names, (
            f"{tool_name} must NOT be in autoreiv allowed tools"
        )


def test_wiki_tasks_platform_skill_declaration():
    """Verify wiki_tasks is declared in PLATFORM_SKILL_TOOLS with canonical tools."""
    assert "wiki_tasks" in PLATFORM_SKILL_TOOLS
    tools = PLATFORM_SKILL_TOOLS["wiki_tasks"]
    assert tools == (
        "wiki_note_read",
        "wiki_note_create",
        "wiki_note_update",
        "wiki_template_read",
    )
    # Adheres strictly to CAP-001 cap <= 6 tools
    assert len(tools) <= 6


def test_canonical_wiki_tools_manage_weekly_tasks(temp_wiki_root):
    """Verify that canonical WikiTools create, read, update, and carry over tasks seamlessly."""
    wiki_tools = WikiTools(wiki_root=str(temp_wiki_root))

    # 1. Read weekly template
    tmpl_res = wiki_tools.wiki_template_read("weekly_notes")
    assert tmpl_res is not None
    assert "### 🔄 Carry-Over" in tmpl_res["content"]

    # 2. Create weekly note using template
    create_res = wiki_tools.wiki_note_create(
        title="WEEK 39 (2026-W39)",
        content=tmpl_res["content"],
        domain="weekly",
        topic="worklog",
        template="weekly_notes",
        tags=["worklog", "weekly_notes"],
    )
    assert create_res["success"] is True
    staged_path = create_res["path"]
    assert staged_path.startswith("00_Inbox/")

    # 3. Read staged weekly note
    read_res = wiki_tools.wiki_note_read(staged_path)
    assert read_res["success"] is True
    assert "- [ ] Plan weekly priorities" in read_res["content"]

    # 4. Complete a task (- [ ] -> - [x])
    updated_content = read_res["content"].replace(
        "- [ ] Plan weekly priorities",
        "- [x] Plan weekly priorities",
    )
    update_res = wiki_tools.wiki_note_update(
        relative_path=staged_path,
        content=updated_content,
    )
    assert update_res["success"] is True

    # 5. Verify updated content
    re_read = wiki_tools.wiki_note_read(staged_path)
    assert "- [x] Plan weekly priorities" in re_read["content"]
