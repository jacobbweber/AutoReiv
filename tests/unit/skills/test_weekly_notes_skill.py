"""
Unit tests for WeeklyNotesSkill and Markdown Task Carry-Over Engine [REQ-WNOTE-001, REQ-WNOTE-002, REQ-WNOTE-003].
"""

import pytest

from src.application.skills.weekly_notes_skill import WeeklyNotesSkill
from src.application.skills.wiki_skill import WikiSkill


@pytest.fixture
def temp_wiki_root(tmp_path):
    templates_dir = tmp_path / "03_Resources" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir = tmp_path / "01_Notes" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)

    template_content = (
        "---\n"
        "tags:\n"
        "  - worklog\n"
        "  - weekly_notes\n"
        "week: {{week}}\n"
        "date_start: {{date_start}}\n"
        "date_end: {{date_end}}\n"
        "---\n"
        "[[My Dashboard]]\n\n"
        "## Projects\n"
        "- **Server Currency** - Work through Windows OS In-Place Upgrades.\n"
        "- **AQS Migration** - Migrate app from server 2000 to 2022.\n\n"
        "---\n\n"
        "## {{week_title}} Summary\n\n"
        "### 🎯 Focusing\n"
        "-\n\n"
        "### ⚡ Ad-Hoc\n"
        "-\n\n"
        "### 🔄 Carry-Over\n"
        "{{carry_over_tasks}}\n\n"
        "### ✅ Done\n"
        "-\n\n"
        "---\n\n"
        "## 📅 Daily Work Logs\n\n"
        "### {{monday:dddd D}}\n"
        "-\n\n"
        "### {{tuesday:dddd D}}\n"
        "-\n\n"
        "### {{wednesday:dddd D}}\n"
        "-\n\n"
        "### {{thursday:dddd D}}\n"
        "-\n\n"
        "### {{friday:dddd D}}\n"
        "-\n\n"
        "### {{saturday:dddd D}}\n"
        "-\n\n"
        "### {{sunday:dddd D}}\n"
        "-\n"
    )
    (templates_dir / "weekly_notes.md").write_text(template_content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def skill(temp_wiki_root):
    wiki_skill = WikiSkill(wiki_root=str(temp_wiki_root))
    return WeeklyNotesSkill(wiki_skill=wiki_skill, wiki_root=str(temp_wiki_root))


def test_get_or_create_weekly_note_creates_interpolated_note(skill, temp_wiki_root):
    # Week 35 of 2026 starts Monday Aug 24, 2026 and ends Sunday Aug 30, 2026
    res = skill.get_or_create_weekly_note("2026-W35")
    assert res["success"] is True
    assert "weekly/2026-W35.md" in res["path"]

    note_path = temp_wiki_root / res["path"]
    assert note_path.exists()

    content = note_path.read_text(encoding="utf-8")
    assert "2026-W35" in content
    assert "2026-08-24" in content
    assert "2026-08-30" in content
    assert "## WEEK 35 Summary" in content
    assert "### Monday 24" in content
    assert "### Tuesday 25" in content
    assert "### Wednesday 26" in content
    assert "### Thursday 27" in content
    assert "### Friday 28" in content
    assert "### Saturday 29" in content
    assert "### Sunday 30" in content


def test_log_daily_work_item(skill, temp_wiki_root):
    skill.get_or_create_weekly_note("2026-W35")

    res = skill.log_daily_work_item(
        week_str="2026-W35",
        day="Monday",
        item_text="Troubleshooting Packer Win2022 template creation",
        is_completed=True,
    )
    assert res["success"] is True

    content = (temp_wiki_root / res["path"]).read_text(encoding="utf-8")
    assert "Troubleshooting Packer Win2022 template creation" in content
    assert "✅" in content


def test_complete_weekly_task(skill, temp_wiki_root):
    skill.get_or_create_weekly_note("2026-W35")
    skill.log_daily_work_item(
        week_str="2026-W35",
        day="Tuesday",
        item_text="Ragnar Vet appointment",
        is_completed=False,
    )

    complete_res = skill.complete_weekly_task(
        week_str="2026-W35",
        task_text="Ragnar Vet appointment",
    )
    assert complete_res["success"] is True

    content = (temp_wiki_root / complete_res["path"]).read_text(encoding="utf-8")
    assert "Ragnar Vet appointment" in content
    assert "✅" in content


def test_rollover_weekly_tasks_carries_over_incomplete_tasks(skill, temp_wiki_root):
    # Setup Week 34 with some completed and some incomplete tasks
    skill.get_or_create_weekly_note("2026-W34")

    # Add incomplete task in Monday
    skill.log_daily_work_item(
        week_str="2026-W34",
        day="Monday",
        item_text="SQL GMSA Automation - Revisit implementing this",
        is_completed=False,
    )
    # Add completed task in Tuesday
    skill.log_daily_work_item(
        week_str="2026-W34",
        day="Tuesday",
        item_text="Completed server upgrade on st1-apisvr1",
        is_completed=True,
    )
    # Add incomplete task in Carry-Over
    skill.log_daily_work_item(
        week_str="2026-W34",
        day="Monday",
        item_text="SystemWare - Red Hat Support Ticket Permissions Issue",
        is_completed=False,
        section="carry_over",
    )

    # Now create Week 35 with rollover from Week 34
    rollover_res = skill.rollover_weekly_tasks(from_week="2026-W34", to_week="2026-W35")
    assert rollover_res["success"] is True
    assert len(rollover_res["carried_over_tasks"]) == 2

    w35_content = (temp_wiki_root / "notes" / "weekly" / "2026-W35.md").read_text(encoding="utf-8")
    assert "### 🔄 Carry-Over" in w35_content
    assert "SQL GMSA Automation - Revisit implementing this" in w35_content
    assert "SystemWare - Red Hat Support Ticket Permissions Issue" in w35_content
    assert "Completed server upgrade on st1-apisvr1" not in w35_content


def test_get_weekly_summary(skill, temp_wiki_root):
    skill.get_or_create_weekly_note("2026-W35")
    skill.log_daily_work_item(
        week_str="2026-W35",
        day="Wednesday",
        item_text="Tested AQS with Lisa Johnson",
        is_completed=True,
    )

    summary = skill.get_weekly_summary("2026-W35")
    assert summary["success"] is True
    assert summary["week"] == "2026-W35"
    assert len(summary["daily_logs"]["Wednesday"]) >= 1
