"""
Weekly Notes & Markdown To-Dos Tools [REQ-WNOTE-001, REQ-WNOTE-002, REQ-WNOTE-003].
Enables agents to maintain Obsidian-compatible Weekly Work Logs, daily reminders, and automated task carry-over.
"""

import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_tools import WikiTools

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE = (
    "---\n"
    'title: "{{week_title}} ({{week}})"\n'
    "domain: weekly\n"
    "topic: worklog\n"
    "category: notes\n"
    "document_type: log\n"
    "status: active\n"
    "tags:\n"
    "  - worklog\n"
    "  - weekly_notes\n"
    'week: "{{week}}"\n'
    'date_start: "{{date_start}}"\n'
    'date_end: "{{date_end}}"\n'
    "---\n"
    "[[My Dashboard]]\n\n"
    "## Projects\n"
    "- **Server Currency** - Work through Windows OS In-Place Upgrades/Migrations for all systems.\n"
    "- **AQS Migration** - Migrate app from server 2000 to 2022.\n"
    "- **Leaders Life** - Child Domain permissions delegation.\n\n"
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


class WeeklyNotesTools:
    """Tool group exposing Obsidian-compatible Weekly Notes and Markdown To-Dos tools."""

    def __init__(self, wiki_tools: WikiTools, wiki_root: str = "data/wiki"):
        self.wiki_tools = wiki_tools
        self.wiki_root = Path(wiki_root)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register weekly note and to-do tools into the ScopedToolRegistry."""
        registry.register_tool(
            name="get_or_create_weekly_note",
            description="Find or create the Markdown Weekly Note for a given week (e.g. '2026-W35') with Monday-Sunday dates and carried-over tasks.",
            parameters={
                "type": "object",
                "properties": {
                    "week_str": {
                        "type": "string",
                        "description": "Optional ISO week identifier like '2026-W35'. Defaults to current week.",
                    },
                },
            },
            handler=self.get_or_create_weekly_note,
        )

        registry.register_tool(
            name="log_daily_work_item",
            description="Append a work log entry, task, or reminder to a specific day or section in the Weekly Note.",
            parameters={
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "Day of the week (e.g. 'Monday', 'Tuesday', or 'carry_over')",
                    },
                    "item_text": {
                        "type": "string",
                        "description": "Description of the task, log entry, or reminder",
                    },
                    "is_completed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether the task is already completed (appends checkmark and timestamp)",
                    },
                    "section": {
                        "type": "string",
                        "default": "daily",
                        "enum": ["daily", "focusing", "ad_hoc", "carry_over", "done"],
                        "description": "Target section in the weekly note",
                    },
                    "week_str": {
                        "type": "string",
                        "description": "Optional ISO week identifier. Defaults to current week.",
                    },
                },
                "required": ["day", "item_text"],
            },
            handler=self.log_daily_work_item,
        )

        registry.register_tool(
            name="complete_weekly_task",
            description="Mark a specific task as completed in the Weekly Note with a completion checkmark and timestamp.",
            parameters={
                "type": "object",
                "properties": {
                    "task_text": {
                        "type": "string",
                        "description": "Task description or substring to locate and mark complete",
                    },
                    "week_str": {
                        "type": "string",
                        "description": "Optional ISO week identifier. Defaults to current week.",
                    },
                },
                "required": ["task_text"],
            },
            handler=self.complete_weekly_task,
        )

        registry.register_tool(
            name="rollover_weekly_tasks",
            description="Extract all incomplete tasks from the previous week's note and roll them over into the new week's Carry-Over section.",
            parameters={
                "type": "object",
                "properties": {
                    "from_week": {
                        "type": "string",
                        "description": "Source ISO week (e.g. '2026-W34'). Defaults to previous week.",
                    },
                    "to_week": {
                        "type": "string",
                        "description": "Destination ISO week (e.g. '2026-W35'). Defaults to current week.",
                    },
                },
            },
            handler=self.rollover_weekly_tasks,
        )

        registry.register_tool(
            name="get_weekly_summary",
            description="Retrieve a structured summary of active projects, carry-over tasks, daily logs, and completed items for the week.",
            parameters={
                "type": "object",
                "properties": {
                    "week_str": {
                        "type": "string",
                        "description": "Optional ISO week identifier. Defaults to current week.",
                    },
                },
            },
            handler=self.get_weekly_summary,
        )

    def _resolve_week_bounds(self, week_str: Optional[str] = None) -> Tuple[int, int, date, date, Dict[str, str]]:
        """Parse or determine ISO year and week number and compute start (Mon) and end (Sun) dates."""
        if week_str and "-W" in week_str.upper():
            parts = week_str.upper().split("-W")
            year = int(parts[0])
            week_num = int(parts[1])
        else:
            today = date.today()
            isocal = today.isocalendar()
            year = isocal.year
            week_num = isocal.week

        # ISO week: day 1 is Monday, day 7 is Sunday
        mon = date.fromisocalendar(year, week_num, 1)
        sun = date.fromisocalendar(year, week_num, 7)

        day_labels = {
            "monday": f"Monday {mon.day}",
            "tuesday": f"Tuesday {(mon + timedelta(days=1)).day}",
            "wednesday": f"Wednesday {(mon + timedelta(days=2)).day}",
            "thursday": f"Thursday {(mon + timedelta(days=3)).day}",
            "friday": f"Friday {(mon + timedelta(days=4)).day}",
            "saturday": f"Saturday {(mon + timedelta(days=5)).day}",
            "sunday": f"Sunday {sun.day}",
        }

        return year, week_num, mon, sun, day_labels

    def _get_previous_week_str(self, year: int, week_num: int) -> str:
        mon = date.fromisocalendar(year, week_num, 1)
        prev_mon = mon - timedelta(days=7)
        prev_iso = prev_mon.isocalendar()
        return f"{prev_iso.year}-W{prev_iso.week:02d}"

    def _load_template_content(self) -> str:
        """Load template from wiki resources directory or fallback."""
        template_candidates = [
            self.wiki_root / "03_Resources" / "templates" / "weekly_notes.md",
            self.wiki_root / "resources" / "templates" / "weekly_notes.md",
            self.wiki_root / "templates" / "weekly_notes.md",
        ]
        for p in template_candidates:
            if p.exists():
                return p.read_text(encoding="utf-8")
        return DEFAULT_TEMPLATE

    def extract_incomplete_tasks(self, markdown_text: str) -> List[str]:
        """Extract uncompleted tasks from a weekly markdown note, ignoring frontmatter."""
        # Strip frontmatter
        body = markdown_text
        if markdown_text.startswith("---"):
            parts = markdown_text.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]

        lines = body.splitlines()
        incomplete_tasks = []
        current_section = ""

        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("#"):
                current_section = trimmed.lower()
                continue

            # Ignore projects section and Done section
            if "## projects" in current_section or "### done" in current_section or "### ✅ done" in current_section:
                continue

            # Check for standard markdown unchecked checkbox or bullet without checkmark
            if trimmed.startswith("- [ ] "):
                task_content = trimmed[6:].strip()
                if task_content and "✅" not in task_content:
                    incomplete_tasks.append(task_content)
            elif trimmed.startswith("- ") and not trimmed.startswith("- [x]") and not trimmed.startswith("- [X]"):
                task_content = trimmed[2:].strip()
                if task_content and "✅" not in task_content:
                    incomplete_tasks.append(task_content)

        return incomplete_tasks

    def get_or_create_weekly_note(self, week_str: Optional[str] = None) -> Dict[str, Any]:
        """Find or create the weekly note for the specified week."""
        year, week_num, mon, sun, day_labels = self._resolve_week_bounds(week_str)
        formatted_week_str = f"{year}-W{week_num:02d}"

        candidate_paths = [
            f"notes/weekly/{formatted_week_str}.md",
            f"01_Notes/weekly/{formatted_week_str}.md",
            f"01_notes/weekly/{formatted_week_str}.md",
        ]
        for cp in candidate_paths:
            fp = self.wiki_root / cp
            if fp.exists():
                content = fp.read_text(encoding="utf-8")
                return {
                    "success": True,
                    "created": False,
                    "path": cp,
                    "week": formatted_week_str,
                    "content": content,
                }

        # Check for previous week's tasks to carry over
        prev_week_str = self._get_previous_week_str(year, week_num)
        prev_candidates = [
            self.wiki_root / f"notes/weekly/{prev_week_str}.md",
            self.wiki_root / f"01_Notes/weekly/{prev_week_str}.md",
            self.wiki_root / f"01_notes/weekly/{prev_week_str}.md",
        ]
        carried_tasks_lines = []
        for prev_path in prev_candidates:
            if prev_path.exists():
                prev_content = prev_path.read_text(encoding="utf-8")
                incomplete = self.extract_incomplete_tasks(prev_content)
                for t in incomplete:
                    carried_tasks_lines.append(f"- [ ] {t}")
                break

        carry_over_block = "\n".join(carried_tasks_lines) if carried_tasks_lines else "- "

        template = self._load_template_content()
        rendered = template
        rendered = rendered.replace("{{week}}", formatted_week_str)
        rendered = rendered.replace("{{week_title}}", f"WEEK {week_num}")
        rendered = rendered.replace("{{date_start}}", mon.isoformat())
        rendered = rendered.replace("{{date_end}}", sun.isoformat())
        rendered = rendered.replace("{{carry_over_tasks}}", carry_over_block)

        # Replace day placeholders
        rendered = re.sub(r"\{\{monday:dddd D\}\}", day_labels["monday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{tuesday:dddd D\}\}", day_labels["tuesday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{wednesday:dddd D\}\}", day_labels["wednesday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{thursday:dddd D\}\}", day_labels["thursday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{friday:dddd D\}\}", day_labels["friday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{saturday:dddd D\}\}", day_labels["saturday"], rendered, flags=re.IGNORECASE)
        rendered = re.sub(r"\{\{sunday:dddd D\}\}", day_labels["sunday"], rendered, flags=re.IGNORECASE)

        rel_path = f"notes/weekly/{formatted_week_str}.md"
        full_path = self.wiki_root / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(rendered, encoding="utf-8")

        # Also sync to 01_Notes/weekly if directory exists
        if (self.wiki_root / "01_Notes").exists():
            p2 = self.wiki_root / "01_Notes" / "weekly" / f"{formatted_week_str}.md"
            p2.parent.mkdir(parents=True, exist_ok=True)
            p2.write_text(rendered, encoding="utf-8")

        return {
            "success": True,
            "created": True,
            "path": rel_path,
            "week": formatted_week_str,
            "content": rendered,
            "carried_over_count": len(carried_tasks_lines),
        }

    def log_daily_work_item(
        self,
        day: str,
        item_text: str,
        is_completed: bool = False,
        section: str = "daily",
        week_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append an item under a specific day or section in the weekly note."""
        note_res = self.get_or_create_weekly_note(week_str)
        rel_path = note_res["path"]
        full_path = self.wiki_root / rel_path
        content = full_path.read_text(encoding="utf-8")

        today_str = date.today().isoformat()
        if is_completed:
            formatted_item = f"- [x] {item_text} ✅ {today_str}"
        else:
            formatted_item = f"- [ ] {item_text}"

        lines = content.splitlines()
        updated_lines = []
        inserted = False

        if section == "carry_over":
            target_header = "### 🔄 Carry-Over"
        elif section == "focusing":
            target_header = "### 🎯 Focusing"
        elif section == "ad_hoc":
            target_header = "### ⚡ Ad-Hoc"
        elif section == "done":
            target_header = "### ✅ Done"
        else:
            # Match day name (e.g. 'Monday', 'Tuesday', etc.)
            clean_day = day.strip().lower()
            target_header = clean_day

        for i, line in enumerate(lines):
            updated_lines.append(line)
            if not inserted:
                line_lower = line.lower()
                is_match = False
                if section != "daily" and target_header.lower() in line_lower:
                    is_match = True
                elif section == "daily" and line.startswith("### ") and clean_day in line_lower:
                    is_match = True

                if is_match:
                    # If next line is just empty bullet '- ', replace it or insert after
                    if i + 1 < len(lines) and lines[i + 1].strip() == "-":
                        # will be replaced
                        pass
                    updated_lines.append(formatted_item)
                    inserted = True

        # Clean up isolated empty '-' lines right after our insertion if any
        final_lines = []
        skip_next = False
        for j, line in enumerate(updated_lines):
            if skip_next:
                skip_next = False
                continue
            if line == formatted_item and j + 1 < len(updated_lines) and updated_lines[j + 1].strip() == "-":
                final_lines.append(line)
                skip_next = True
            else:
                final_lines.append(line)

        new_content = "\n".join(final_lines)
        full_path.write_text(new_content, encoding="utf-8")

        # Sync mirror path if present
        mirror_path = (
            self.wiki_root / ("01_Notes/weekly" if "notes/weekly" in rel_path else "notes/weekly") / full_path.name
        )
        if mirror_path.exists():
            mirror_path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "path": rel_path,
            "day": day,
            "item": formatted_item,
        }

    def complete_weekly_task(
        self,
        task_text: str,
        week_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark an existing task in the weekly note as completed."""
        note_res = self.get_or_create_weekly_note(week_str)
        rel_path = note_res["path"]
        full_path = self.wiki_root / rel_path
        content = full_path.read_text(encoding="utf-8")

        today_str = date.today().isoformat()
        lines = content.splitlines()
        matched = False
        new_lines = []

        for line in lines:
            if not matched and task_text.lower() in line.lower() and "###" not in line:
                matched = True
                cleaned = line
                # Convert checkbox
                if cleaned.strip().startswith("- [ ] "):
                    cleaned = cleaned.replace("- [ ] ", "- [x] ", 1)
                elif cleaned.strip().startswith("- ") and not cleaned.strip().startswith("- [x]"):
                    cleaned = cleaned.replace("- ", "- [x] ", 1)
                if "✅" not in cleaned:
                    cleaned = f"{cleaned} ✅ {today_str}"
                new_lines.append(cleaned)
            else:
                new_lines.append(line)

        if not matched:
            return {"success": False, "error": f"Task matching '{task_text}' not found in {rel_path}"}

        new_content = "\n".join(new_lines)
        full_path.write_text(new_content, encoding="utf-8")

        mirror_path = (
            self.wiki_root / ("01_Notes/weekly" if "notes/weekly" in rel_path else "notes/weekly") / full_path.name
        )
        if mirror_path.exists():
            mirror_path.write_text(new_content, encoding="utf-8")

        return {"success": True, "path": rel_path, "task": task_text, "completed_at": today_str}

    def rollover_weekly_tasks(
        self,
        from_week: Optional[str] = None,
        to_week: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rollover incomplete tasks from from_week into to_week's Carry-Over section."""
        year, week_num, _, _, _ = self._resolve_week_bounds(to_week)
        target_week_str = f"{year}-W{week_num:02d}"

        if not from_week:
            from_week = self._get_previous_week_str(year, week_num)

        from_candidates = [
            self.wiki_root / f"notes/weekly/{from_week}.md",
            self.wiki_root / f"01_Notes/weekly/{from_week}.md",
            self.wiki_root / f"01_notes/weekly/{from_week}.md",
        ]
        from_path = None
        for fc in from_candidates:
            if fc.exists():
                from_path = fc
                break

        if not from_path:
            return {"success": False, "error": f"Source weekly note '{from_week}.md' does not exist."}

        prev_content = from_path.read_text(encoding="utf-8")
        incomplete_tasks = self.extract_incomplete_tasks(prev_content)

        to_res = self.get_or_create_weekly_note(target_week_str)
        to_full_path = self.wiki_root / to_res["path"]
        to_content = to_full_path.read_text(encoding="utf-8")

        # Inject into ### 🔄 Carry-Over
        lines = to_content.splitlines()
        new_lines = []
        inserted = False

        for i, line in enumerate(lines):
            new_lines.append(line)
            if not inserted and "### 🔄 carry-over" in line.lower():
                for t in incomplete_tasks:
                    task_entry = f"- [ ] {t}"
                    if task_entry not in to_content:
                        new_lines.append(task_entry)
                inserted = True

        # Clean empty '-' line if present
        cleaned_lines = []
        for line in new_lines:
            if line.strip() == "-" and len(incomplete_tasks) > 0:
                continue
            cleaned_lines.append(line)

        final_to_content = "\n".join(cleaned_lines)
        to_full_path.write_text(final_to_content, encoding="utf-8")

        mirror_to = (
            self.wiki_root
            / ("01_Notes/weekly" if "notes/weekly" in to_res["path"] else "notes/weekly")
            / to_full_path.name
        )
        if mirror_to.exists():
            mirror_to.write_text(final_to_content, encoding="utf-8")

        return {
            "success": True,
            "from_week": from_week,
            "to_week": target_week_str,
            "carried_over_tasks": incomplete_tasks,
            "count": len(incomplete_tasks),
        }

    def get_weekly_summary(self, week_str: Optional[str] = None) -> Dict[str, Any]:
        """Extract a structured summary of the specified weekly note."""
        note_res = self.get_or_create_weekly_note(week_str)
        content = note_res["content"]

        lines = content.splitlines()
        current_section = "general"
        sections: Dict[str, List[str]] = {
            "projects": [],
            "focusing": [],
            "ad_hoc": [],
            "carry_over": [],
            "done": [],
        }
        daily_logs: Dict[str, List[str]] = {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": [],
        }

        for line in lines:
            trimmed = line.strip()
            lower = trimmed.lower()
            if lower.startswith("## projects"):
                current_section = "projects"
                continue
            elif "### 🎯 focusing" in lower:
                current_section = "focusing"
                continue
            elif "### ⚡ ad-hoc" in lower:
                current_section = "ad_hoc"
                continue
            elif "### 🔄 carry-over" in lower:
                current_section = "carry_over"
                continue
            elif "### ✅ done" in lower:
                current_section = "done"
                continue
            elif lower.startswith("### monday"):
                current_section = "day_Monday"
                continue
            elif lower.startswith("### tuesday"):
                current_section = "day_Tuesday"
                continue
            elif lower.startswith("### wednesday"):
                current_section = "day_Wednesday"
                continue
            elif lower.startswith("### thursday"):
                current_section = "day_Thursday"
                continue
            elif lower.startswith("### friday"):
                current_section = "day_Friday"
                continue
            elif lower.startswith("### saturday"):
                current_section = "day_Saturday"
                continue
            elif lower.startswith("### sunday"):
                current_section = "day_Sunday"
                continue
            elif trimmed.startswith("#"):
                current_section = "other"
                continue

            if trimmed.startswith("- ") and trimmed != "-":
                if current_section in sections:
                    sections[current_section].append(trimmed)
                elif current_section.startswith("day_"):
                    day_name = current_section.replace("day_", "")
                    daily_logs[day_name].append(trimmed)

        return {
            "success": True,
            "week": note_res["week"],
            "path": note_res["path"],
            "projects": sections["projects"],
            "focusing": sections["focusing"],
            "ad_hoc": sections["ad_hoc"],
            "carry_over": sections["carry_over"],
            "done": sections["done"],
            "daily_logs": daily_logs,
        }
