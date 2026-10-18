"""Education Learning OS wiki curation, progress summary, and tool schema registration [CARD-715]."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.serialization.json_safe import to_jsonable as _json_safe


class EducationWikiProgressMixin:
    """Wiki curation and progress-summary tool handlers for EducationTools."""

    wiki_root: Optional[Path]

    def _resolve_agent_id(self, agent_id: Optional[str] = None) -> str:
        raise NotImplementedError

    def _resolve_repo(self, agent_id: Optional[str] = None) -> AgentMemoryRepository:
        raise NotImplementedError

    def _wiki_tools(self):
        from src.application.skills.wiki_tools import WikiTools

        if self.wiki_root is not None:
            return WikiTools(wiki_root=self.wiki_root)
        return WikiTools()

    def education_wiki_template_catalog(self) -> Dict[str, Any]:
        """List catalogued education-* Wiki templates for Learning OS curation."""
        from src.application.education.wiki_curation import (
            HTTP_CONTRACT,
            SKILL_ID,
            catalog_education_templates,
        )

        items = catalog_education_templates()
        return _json_safe(
            {
                "success": True,
                "count": len(items),
                "templates": items,
                "skill_hint": SKILL_ID,
                "http_contract": HTTP_CONTRACT,
                "note": "Use education-* templates when curating education notes; raw sources MAY omit education tags.",
            }
        )

    def education_wiki_curate_from_link(
        self,
        url: str = "",
        topic: str = "",
        title: str = "",
        template: str = "",
        raw_source: bool = False,
        body: str = "",
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Curate a link into a durable Wiki note (wiki_note_create / One-Door)."""
        from src.application.education.wiki_curation import curate_from_link

        _ = agent_id  # reserved for future agent-scoped wiki roots
        tools = self._wiki_tools()
        result = curate_from_link(
            tools,
            url=url or "",
            topic=topic or "",
            title=(title or None),
            template=(template or None),
            raw_source=bool(raw_source),
            body=(body or None),
        )
        return _json_safe(result)

    def education_wiki_curate_from_curriculum(
        self,
        curriculum: str = "",
        topic: str = "",
        template: str = "",
        raw_source: bool = False,
        max_items: int = 12,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Curate a curriculum outline into durable Wiki note(s)."""
        from src.application.education.wiki_curation import curate_from_curriculum

        _ = agent_id
        tools = self._wiki_tools()
        result = curate_from_curriculum(
            tools,
            curriculum=curriculum or "",
            topic=topic or "",
            template=(template or None),
            raw_source=bool(raw_source),
            max_items=int(max_items or 12),
        )
        return _json_safe(result)

    def education_progress_summary(
        self,
        agent_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trustable course + mastery + due summary for Learning OS skill progress-summary.

        Twin of ``GET /api/education/progress``. On failure returns success=false with
        mastery_pct=None — never invent percentages. Studio chrome is not required.
        """
        from src.application.education.progress_summary import build_progress_summary

        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            out = build_progress_summary(
                repo,
                agent_id=agent,
                topic_id=(topic_id or "").strip(),
                course_id=(course_id or "").strip(),
            )
        except Exception as exc:  # noqa: BLE001
            return _json_safe(
                {
                    "success": False,
                    "error": f"progress summary failed: {exc}",
                    "durable": False,
                    "agent_id": agent,
                    "skill_hint": "progress-summary",
                    "http_contract": "GET /api/education/progress",
                    "mastery": {"mastery_pct": None, "empty": True},
                    "empty": True,
                    "empty_state": "Progress unavailable.",
                    "studio_required": False,
                }
            )
        if not isinstance(out, dict):
            return _json_safe(
                {
                    "success": False,
                    "error": "progress summary returned non-dict",
                    "durable": False,
                    "skill_hint": "progress-summary",
                    "http_contract": "GET /api/education/progress",
                    "mastery": {"mastery_pct": None, "empty": True},
                    "studio_required": False,
                }
            )
        result = dict(out)
        result.setdefault("skill_hint", "progress-summary")
        result.setdefault("http_contract", "GET /api/education/progress")
        result["studio_required"] = False
        return _json_safe(result)

    def education_progress_courses(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List durable education courses for progress-summary (Learning OS course table)."""
        from src.application.education.progress_summary import summarize_courses

        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            lim = max(1, min(int(limit or 50), 200))
            rows = []
            if hasattr(repo, "list_education_courses"):
                rows = list(repo.list_education_courses(limit=lim) or [])
            summary = summarize_courses(rows)
        except Exception as exc:  # noqa: BLE001
            return _json_safe(
                {
                    "success": False,
                    "error": f"course list failed: {exc}",
                    "durable": False,
                    "agent_id": agent,
                    "skill_hint": "progress-summary",
                    "http_contract": "GET /api/education/course",
                }
            )
        return _json_safe(
            {
                "success": True,
                "agent_id": agent,
                "skill_hint": "progress-summary",
                "http_contract": "GET /api/education/course",
                **summary,
            }
        )

    def education_progress_mastery(
        self,
        agent_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """Mastery counts from education_mastery for progress-summary (no fake %)."""
        from src.application.education.progress_summary import summarize_mastery_rows

        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            lim = max(1, min(int(limit or 200), 500))
            rows = list(repo.list_education_mastery(limit=lim) or [])
            topic_s = (topic or "").strip()
            if topic_s:
                rows = [r for r in rows if str(r.get("topic") or "") == topic_s]
            summary = summarize_mastery_rows(rows)
        except Exception as exc:  # noqa: BLE001
            return _json_safe(
                {
                    "success": False,
                    "error": f"mastery summary failed: {exc}",
                    "durable": False,
                    "agent_id": agent,
                    "skill_hint": "progress-summary",
                    "http_contract": "GET /api/education/mastery",
                    "mastery_pct": None,
                    "empty": True,
                }
            )
        return _json_safe(
            {
                "success": True,
                "agent_id": agent,
                "topic": (topic or "").strip() or None,
                "skill_hint": "progress-summary",
                "http_contract": "GET /api/education/mastery",
                **summary,
            }
        )


def register_education_tools(tools: Any, registry: ScopedToolRegistry) -> None:
    """Register Education Learning OS tools on the master ScopedToolRegistry."""
    registry.register_tool(
        name="education_quiz_extract",
        description=(
            "Extract quiz items from a Wiki note and persist them into the education_mastery ledger. "
            "A note without quiz items gets suggested questions (from its definition lines) or your own "
            "questions=[{prompt, answer}], saved in a separate quiz note (<note>-quiz.md); the source note is "
            "never edited. Answers are graded by exact match, so keep them to a word or short phrase."
        ),
        parameters={
            "type": "object",
            "properties": {
                "wiki_path": {
                    "type": "string",
                    "description": "Relative Wiki path of the note to extract from.",
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic label (defaults to note title).",
                },
                "persist": {
                    "type": "boolean",
                    "description": "If true (default), upsert extracted items into mastery.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional agent id for memory.db (defaults to caller / tutor).",
                },
                "questions": {
                    "type": "array",
                    "description": "Optional questions you wrote, saved in the separate quiz note.",
                    "items": {
                        "type": "object",
                        "properties": {"prompt": {"type": "string"}, "answer": {"type": "string"}},
                        "required": ["prompt", "answer"],
                    },
                },
                "quiz_path": {
                    "type": "string",
                    "description": "Optional Wiki path for the quiz note (default <note>-quiz.md next to it).",
                },
            },
            "required": ["wiki_path"],
        },
        handler=tools.education_quiz_extract,
    )
    registry.register_tool(
        name="education_quiz_next",
        description=(
            "Fetch the next Learning OS quiz / retrieval item(s) from education_mastery "
            "(GET /api/education/quiz/next). Prefer due/weak/miss over random."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max items to return (1-50, default 5).",
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic filter.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional agent id (defaults to caller / tutor).",
                },
            },
            "required": [],
        },
        handler=tools.education_quiz_next,
    )
    registry.register_tool(
        name="education_quiz_grade",
        description=(
            "Binary-grade a quiz answer and DURABLY write pass/miss + SRS next_due into "
            "education_mastery (POST /api/education/quiz/grade). Never invent a successful "
            "grade on failure. Use for Learning OS skill quiz-turn."
        ),
        parameters={
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Mastery item id (edu_…).",
                },
                "answer": {
                    "type": "string",
                    "description": "Learner answer to grade.",
                },
                "topic": {"type": "string"},
                "wiki_path": {
                    "type": "string",
                    "description": "Required when registering a new item on the fly.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Required when registering a new item on the fly.",
                },
                "expected_answer": {
                    "type": "string",
                    "description": "Required when registering a new item on the fly.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional agent id (defaults to caller / tutor).",
                },
            },
            "required": ["item_id"],
        },
        handler=tools.education_quiz_grade,
    )
    registry.register_tool(
        name="education_mastery_due",
        description=(
            "List due SRS / flashcard items from education_mastery "
            "(GET /api/education/mastery/due)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max due items (default 50)."},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_mastery_due,
    )
    registry.register_tool(
        name="education_mastery_upsert",
        description=(
            "Upsert a mastery / flashcard card into education_mastery as unseen "
            "(POST /api/education/mastery/upsert)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "wiki_path": {"type": "string"},
                "prompt": {"type": "string"},
                "expected_answer": {"type": "string"},
                "item_id": {
                    "type": "string",
                    "description": "Optional stable id; derived from path+prompt when omitted.",
                },
                "agent_id": {"type": "string"},
            },
            "required": ["topic", "wiki_path", "prompt", "expected_answer"],
        },
        handler=tools.education_mastery_upsert,
    )
    registry.register_tool(
        name="education_flashcard_next",
        description=(
            "Fetch next due flashcard / SRS card(s) for Learning OS skill flashcard-turn. "
            "Shares mastery due ledger (no dedicated flashcard HTTP router)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max cards (default 5)."},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_flashcard_next,
    )
    registry.register_tool(
        name="education_flashcard_grade",
        description=(
            "Grade a flashcard turn via the shared durable quiz-grade path "
            "(POST /api/education/quiz/grade → education_mastery SRS). "
            "On failure returns success=false; never claim a durable grade."
        ),
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "answer": {"type": "string"},
                "topic": {"type": "string"},
                "wiki_path": {"type": "string"},
                "prompt": {"type": "string"},
                "expected_answer": {"type": "string"},
                "agent_id": {"type": "string"},
            },
            "required": ["item_id"],
        },
        handler=tools.education_flashcard_grade,
    )

    registry.register_tool(
        name="education_due_review_list",
        description=(
            "List due SRS / retention reviews from education_mastery for Learning OS "
            "skill due-review (GET /api/education/mastery/due). Empty queue returns "
            "empty=true and empty_state='No due reviews.' - never invent due items. "
            "Delivery profiles do not replace ledger/SRS."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max due items (default 50)."},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_due_review_list,
    )
    registry.register_tool(
        name="education_due_review_complete",
        description=(
            "Complete one due review: durable binary grade + SRS next_due via "
            "POST /api/education/quiz/grade, then report whether the item left the "
            "due queue. On failure returns success=false; never claim durable success."
        ),
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "Due mastery item id."},
                "answer": {"type": "string", "description": "Learner answer to grade."},
                "topic": {"type": "string"},
                "wiki_path": {"type": "string"},
                "prompt": {"type": "string"},
                "expected_answer": {"type": "string"},
                "agent_id": {"type": "string"},
            },
            "required": ["item_id"],
        },
        handler=tools.education_due_review_complete,
    )
    registry.register_tool(
        name="education_retention_run",
        description=(
            "Run the Education retention routine (POST /api/education/retention/run): "
            "due ledger -> standing Job mint. Empty due = nothing_due. Without "
            "orchestrator returns honest failure (no fake job ids). Does not claim "
            "delivery profiles replace ledger/SRS."
        ),
        parameters={
            "type": "object",
            "properties": {
                "max_items": {
                    "type": "integer",
                    "description": "Max due items to mint (1-20, default 5).",
                },
                "force_due_item_id": {
                    "type": "string",
                    "description": "Optional item id to force due now (smoke).",
                },
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_retention_run,
    )

    registry.register_tool(
        name="education_wiki_template_catalog",
        description=(
            "List catalogued education-* Wiki templates for Learning OS skill "
            "education-wiki-curation (from src/application/education/templates.py)."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=tools.education_wiki_template_catalog,
    )
    registry.register_tool(
        name="education_wiki_curate_from_link",
        description=(
            "Curate a link into a durable Wiki note via wiki_note_create "
            "(POST /api/education/wiki/curate mode=link). Use catalogued education-* "
            "templates when appropriate; set raw_source=true to omit education tags. "
            "On fetch/write failure returns success=false and does not claim the library updated."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute http(s) URL to curate."},
                "topic": {"type": "string", "description": "Study / course topic label."},
                "title": {"type": "string", "description": "Optional note title override."},
                "template": {
                    "type": "string",
                    "description": "Optional education-* template slug (default education-concept).",
                },
                "raw_source": {
                    "type": "boolean",
                    "description": "If true, stage a raw/source note without education tags.",
                },
                "body": {
                    "type": "string",
                    "description": "Optional pre-fetched text (skips network fetch).",
                },
                "agent_id": {"type": "string"},
            },
            "required": ["url"],
        },
        handler=tools.education_wiki_curate_from_link,
    )
    registry.register_tool(
        name="education_wiki_curate_from_curriculum",
        description=(
            "Curate a curriculum outline (bullets) into durable Wiki note(s) via "
            "wiki_note_create (POST /api/education/wiki/curate mode=curriculum). "
            "Failures return success=false; never claim durable library success."
        ),
        parameters={
            "type": "object",
            "properties": {
                "curriculum": {
                    "type": "string",
                    "description": "Multiline curriculum outline / bullet list.",
                },
                "topic": {"type": "string"},
                "template": {
                    "type": "string",
                    "description": "Optional education-* template slug (default education-concept).",
                },
                "raw_source": {
                    "type": "boolean",
                    "description": "If true, one raw outline note without education tags.",
                },
                "max_items": {"type": "integer", "description": "Max curriculum items (default 12)."},
                "agent_id": {"type": "string"},
            },
            "required": ["curriculum"],
        },
        handler=tools.education_wiki_curate_from_curriculum,
    )
    registry.register_tool(
        name="education_progress_summary",
        description=(
            "Trustable Learning OS progress for skill progress-summary: active/list "
            "courses, mastery counts (pass/miss/unseen), due count, optional learner. "
            "GET /api/education/progress. On failure success=false and mastery_pct=None "
            "- never invent percentages. Does not require Education Studio panels."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Optional topic to scope course/mastery."},
                "course_id": {"type": "string", "description": "Optional durable course id."},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_progress_summary,
    )
    registry.register_tool(
        name="education_progress_courses",
        description=(
            "List durable education_course rows for progress-summary "
            "(Learning OS course table / GET /api/education/course)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max courses (default 50)."},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_progress_courses,
    )
    registry.register_tool(
        name="education_progress_mastery",
        description=(
            "Mastery pass/miss/unseen counts from education_mastery for progress-summary "
            "(GET /api/education/mastery). Empty ledger => empty=true, mastery_pct=None."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Optional topic filter."},
                "limit": {"type": "integer"},
                "agent_id": {"type": "string"},
            },
            "required": [],
        },
        handler=tools.education_progress_mastery,
    )
