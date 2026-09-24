"""Education Learning OS agent tools for Tutor quiz / flashcard / due-review turns.

CARD-438: quiz/flashcard tools wrap ``quiz_engine`` + mastery ledger ops (same
durable path as ``POST /api/education/quiz/grade``, mastery due/upsert).
CARD-439: due-review list/complete + retention run for Tutor education mode.
No bubble-theatre grades or fake due lists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.serialization.json_safe import to_jsonable as _json_safe


class EducationTools:
    """Tool group: durable quiz / flashcard turns into ``education_mastery``."""

    def __init__(
        self,
        *,
        data_dir: Optional[Union[str, Path]] = None,
        wiki_root: Optional[Union[str, Path]] = None,
        repository: Optional[AgentMemoryRepository] = None,
        default_agent_id: str = "tutor",
        orchestrator: Optional[Any] = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.wiki_root = Path(wiki_root) if wiki_root is not None else None
        self.repository = repository
        self.default_agent_id = (default_agent_id or "tutor").strip() or "tutor"
        self.orchestrator = orchestrator

    def _resolve_agent_id(self, agent_id: Optional[str] = None) -> str:
        target = (agent_id or "").strip()
        if not target:
            ctx = get_tool_context() or {}
            target = str(ctx.get("agent_id") or "").strip()
        if not target:
            target = self.default_agent_id
        return target

    def _resolve_repo(self, agent_id: Optional[str] = None) -> AgentMemoryRepository:
        if self.repository is not None:
            return self.repository
        target = self._resolve_agent_id(agent_id)
        repo = AgentMemoryRepository(agent_id=target, data_dir=self.data_dir)
        repo.initialize_schema()
        return repo

    def _wiki_store(self) -> WikiStore:
        if self.wiki_root is not None:
            return WikiStore(root_dir=self.wiki_root)
        return WikiStore()

    def education_quiz_extract(
        self,
        wiki_path: str,
        topic: Optional[str] = None,
        persist: bool = True,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract Q/A quiz items from a Wiki note; optionally upsert into mastery ledger."""
        from src.application.education.quiz_engine import extract_quiz_items_from_note

        path = (wiki_path or "").strip()
        if not path:
            return {"success": False, "error": "wiki_path is required", "durable": False}
        try:
            store = self._wiki_store()
            note = store.read_note(path)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"Wiki note not found: {path} ({exc})",
                "durable": False,
            }
        if not isinstance(note, dict) or note.get("success") is False:
            err = (note or {}).get("error") if isinstance(note, dict) else "not found"
            return {
                "success": False,
                "error": f"Wiki note not found: {path} ({err})",
                "durable": False,
            }
        content = note.get("content") or note.get("body") or ""
        title = (topic or "").strip() or note.get("title") or path
        items = extract_quiz_items_from_note(content, wiki_path=path, topic=title)
        persisted: List[Dict[str, Any]] = []
        agent = self._resolve_agent_id(agent_id)
        if persist and items:
            try:
                repo = self._resolve_repo(agent)
                for it in items:
                    mid = repo.upsert_education_mastery(
                        item_id=it["item_id"],
                        topic=it["topic"],
                        wiki_path=it["wiki_path"],
                        prompt=it["prompt"],
                        expected_answer=it["expected_answer"],
                        grade="unseen",
                    )
                    row = repo.get_education_mastery(mid)
                    if row:
                        persisted.append(row)
            except Exception as exc:  # noqa: BLE001
                return {
                    "success": False,
                    "error": f"Mastery upsert failed: {exc}",
                    "durable": False,
                    "items": _json_safe(items),
                    "agent_id": agent,
                }
        return _json_safe(
            {
                "success": True,
                "agent_id": agent,
                "wiki_path": path,
                "items": items,
                "persisted": persisted,
                "count": len(items),
                "durable": bool(persisted),
                "http_contract": "POST /api/education/quiz/extract",
            }
        )

    def education_quiz_next(
        self,
        limit: int = 5,
        topic: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return next retrieval quiz items from the mastery ledger (due/weak/miss preference)."""
        from src.application.education.analysis import select_quiz_with_miss_reason_pressure

        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            lim = max(1, min(int(limit or 5), 50))
            items = select_quiz_with_miss_reason_pressure(
                repo, limit=lim, topic=(topic or None)
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"quiz next failed: {exc}",
                "durable": False,
                "agent_id": agent,
            }
        return _json_safe(
            {
                "success": True,
                "agent_id": agent,
                "items": items,
                "count": len(items),
                "selection": "miss_reason_then_due_weak_miss_priming_unseen",
                "http_contract": "GET /api/education/quiz/next",
            }
        )

    def education_quiz_grade(
        self,
        item_id: str,
        answer: str = "",
        topic: Optional[str] = None,
        wiki_path: Optional[str] = None,
        prompt: Optional[str] = None,
        expected_answer: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Binary-grade a quiz answer and persist to ``education_mastery`` (no fake success)."""
        from src.application.education.quiz_engine import grade_answer_binary

        iid = (item_id or "").strip()
        if not iid:
            return {"success": False, "error": "item_id is required", "durable": False}
        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            existing = repo.get_education_mastery(iid)
            if existing is None:
                if not (prompt and expected_answer and wiki_path):
                    return {
                        "success": False,
                        "error": f"Unknown mastery item: {iid}",
                        "durable": False,
                        "agent_id": agent,
                    }
                repo.upsert_education_mastery(
                    item_id=iid,
                    topic=(topic or wiki_path or "").strip(),
                    wiki_path=(wiki_path or "").strip(),
                    prompt=(prompt or "").strip(),
                    expected_answer=(expected_answer or "").strip(),
                    grade="unseen",
                )
                existing = repo.get_education_mastery(iid)
            if existing is None:
                return {
                    "success": False,
                    "error": f"Unknown mastery item: {iid}",
                    "durable": False,
                    "agent_id": agent,
                }
            expected = existing.get("expected_answer") or expected_answer or ""
            if not str(expected).strip():
                return {
                    "success": False,
                    "error": (
                        f"Mastery item {iid} has empty expected_answer; "
                        "re-seed via Priming writeback or education_mastery_upsert before grading"
                    ),
                    "durable": False,
                    "agent_id": agent,
                }
            correct = grade_answer_binary(str(expected), answer or "")
            row = repo.record_education_grade(item_id=iid, correct=correct)
        except KeyError as exc:
            return {
                "success": False,
                "error": str(exc),
                "durable": False,
                "agent_id": agent,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"Grade failed (no durable write claimed): {exc}",
                "durable": False,
                "agent_id": agent,
            }
        return _json_safe(
            {
                "success": True,
                "durable": True,
                "agent_id": agent,
                "item_id": iid,
                "correct": correct,
                "grade": row.get("grade"),
                "next_due": row.get("next_due"),
                "interval_stage": row.get("interval_stage"),
                "item": row,
                "grader": "binary_external",
                "skill_hint": "quiz-turn",
                "http_contract": "POST /api/education/quiz/grade",
            }
        )

    def education_mastery_due(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List due SRS / flashcard items from the mastery ledger."""
        agent = self._resolve_agent_id(agent_id)
        try:
            repo = self._resolve_repo(agent)
            lim = max(1, min(int(limit or 50), 200))
            rows = repo.list_due_education_mastery(limit=lim)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"mastery due failed: {exc}",
                "durable": False,
                "agent_id": agent,
            }
        empty = len(rows) == 0
        return _json_safe(
            {
                "success": True,
                "agent_id": agent,
                "items": rows,
                "count": len(rows),
                "empty": empty,
                "empty_state": "No due reviews." if empty else None,
                "skill_hint": "due-review",
                "http_contract": "GET /api/education/mastery/due",
            }
        )

    def education_mastery_upsert(
        self,
        topic: str,
        wiki_path: str,
        prompt: str,
        expected_answer: str,
        item_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a mastery / flashcard item (unseen) into the Learning OS ledger."""
        from src.application.education.quiz_engine import extract_quiz_items_from_note

        t = (topic or "").strip()
        wp = (wiki_path or "").strip()
        pr = (prompt or "").strip()
        exp = (expected_answer or "").strip()
        if not t or not wp or not pr or not exp:
            return {
                "success": False,
                "error": "topic, wiki_path, prompt, and expected_answer are required",
                "durable": False,
            }
        agent = self._resolve_agent_id(agent_id)
        mid = (item_id or "").strip() or None
        try:
            if not mid:
                fake = extract_quiz_items_from_note(
                    f"## Quiz\n- Q: {pr}\n  A: {exp}\n",
                    wiki_path=wp,
                    topic=t,
                )
                mid = fake[0]["item_id"] if fake else None
            repo = self._resolve_repo(agent)
            saved = repo.upsert_education_mastery(
                item_id=mid or "",
                topic=t,
                wiki_path=wp,
                prompt=pr,
                expected_answer=exp,
                grade="unseen",
            )
            row = repo.get_education_mastery(saved)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"mastery upsert failed: {exc}",
                "durable": False,
                "agent_id": agent,
            }
        return _json_safe(
            {
                "success": True,
                "durable": True,
                "agent_id": agent,
                "item_id": saved,
                "item": row,
                "http_contract": "POST /api/education/mastery/upsert",
            }
        )

    def education_flashcard_next(
        self,
        limit: int = 5,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Next flashcard / SRS card(s) from due mastery (no separate flashcard router)."""
        result = self.education_mastery_due(agent_id=agent_id, limit=limit)
        if not result.get("success"):
            return result
        items = list(result.get("items") or [])[: max(1, min(int(limit or 5), 50))]
        return _json_safe(
            {
                "success": True,
                "agent_id": result.get("agent_id"),
                "items": items,
                "count": len(items),
                "skill_hint": "flashcard-turn",
                "http_contract": "GET /api/education/mastery/due",
                "note": "Flashcards share education_mastery SRS; no /api/education/flashcard/*.",
            }
        )

    def education_flashcard_grade(
        self,
        item_id: str,
        answer: str = "",
        topic: Optional[str] = None,
        wiki_path: Optional[str] = None,
        prompt: Optional[str] = None,
        expected_answer: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade a flashcard turn via the shared quiz-grade durable mastery path."""
        result = self.education_quiz_grade(
            item_id=item_id,
            answer=answer,
            topic=topic,
            wiki_path=wiki_path,
            prompt=prompt,
            expected_answer=expected_answer,
            agent_id=agent_id,
        )
        if isinstance(result, dict):
            result = dict(result)
            result["skill_hint"] = "flashcard-turn"
            # Keep honest: same HTTP contract as quiz grade / SRS advance
            result["http_contract"] = "POST /api/education/quiz/grade"
            result["shared_with"] = "education_quiz_grade"
        return result


    def education_due_review_list(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List due SRS reviews for Learning OS skill due-review (Tutor education mode).

        Sourced from ``GET /api/education/mastery/due`` / ``list_due_education_mastery``.
        Empty queue returns an explicit empty state (no fake items).
        """
        result = self.education_mastery_due(agent_id=agent_id, limit=limit)
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": "mastery due returned non-dict",
                "durable": False,
                "skill_hint": "due-review",
            }
        out = dict(result)
        out["skill_hint"] = "due-review"
        out["http_contract"] = "GET /api/education/mastery/due"
        items = list(out.get("items") or [])
        empty = len(items) == 0
        out["empty"] = empty
        out["count"] = len(items)
        if empty:
            out["empty_state"] = out.get("empty_state") or "No due reviews."
            out["items"] = []
        return _json_safe(out)

    def education_due_review_complete(
        self,
        item_id: str,
        answer: str = "",
        topic: Optional[str] = None,
        wiki_path: Optional[str] = None,
        prompt: Optional[str] = None,
        expected_answer: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete one due review via durable quiz-grade path; report due-queue delta.

        On grade failure returns ``success=false`` / ``durable=false`` - never fake success.
        """
        mid = (item_id or "").strip()
        if not mid:
            return {
                "success": False,
                "error": "item_id is required",
                "durable": False,
                "skill_hint": "due-review",
            }
        agent = self._resolve_agent_id(agent_id)
        before = self.education_due_review_list(agent_id=agent, limit=200)
        before_ids = {
            str(i.get("item_id") or "")
            for i in (before.get("items") or [])
            if isinstance(i, dict)
        }
        graded = self.education_quiz_grade(
            item_id=mid,
            answer=answer,
            topic=topic,
            wiki_path=wiki_path,
            prompt=prompt,
            expected_answer=expected_answer,
            agent_id=agent,
        )
        if not isinstance(graded, dict):
            return {
                "success": False,
                "error": "grade returned non-dict",
                "durable": False,
                "skill_hint": "due-review",
            }
        out = dict(graded)
        out["skill_hint"] = "due-review"
        out["http_contract"] = "POST /api/education/quiz/grade"
        out["shared_with"] = "education_quiz_grade"
        if not out.get("success"):
            out["left_due_queue"] = False
            out["still_due"] = mid in before_ids
            out["durable"] = False
            return _json_safe(out)

        after = self.education_due_review_list(agent_id=agent, limit=200)
        after_ids = {
            str(i.get("item_id") or "")
            for i in (after.get("items") or [])
            if isinstance(i, dict)
        }
        still_due = mid in after_ids
        left = (mid in before_ids) and (not still_due)
        out["left_due_queue"] = left
        out["still_due"] = still_due
        out["due_count_before"] = int(before.get("count") or 0)
        out["due_count_after"] = int(after.get("count") or 0)
        out["rescheduled"] = bool(out.get("next_due")) and not still_due
        return _json_safe(out)

    def education_retention_run(
        self,
        agent_id: Optional[str] = None,
        max_items: int = 5,
        force_due_item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run Learning OS retention routine (due ledger -> standing Job mint).

        Twin of ``POST /api/education/retention/run``. Without an orchestrator,
        returns honest failure / ``no_orchestrator`` - never invents minted job ids.
        Empty due set returns ``nothing_due`` with zero mints.
        """
        from src.application.education.retention_routine import (
            EDUCATION_RETENTION_ROUTINE_ID,
            run_education_retention,
        )

        agent = self._resolve_agent_id(agent_id)
        mid_force = (force_due_item_id or "").strip() or None
        try:
            repo = self._resolve_repo(agent)
            if mid_force:
                row = repo.get_education_mastery(mid_force)
                if not row:
                    return {
                        "success": False,
                        "error": f"Unknown mastery item: {mid_force}",
                        "durable": False,
                        "skill_hint": "due-review",
                        "http_contract": "POST /api/education/retention/run",
                    }
                past = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                with repo.get_connection() as conn:
                    conn.execute(
                        "UPDATE education_mastery SET next_due = ?, pending_job_id = NULL, "
                        "updated_at = ? WHERE item_id = ?",
                        (past, past, mid_force),
                    )
            result = run_education_retention(
                memory_repo=repo,
                orch=self.orchestrator,
                routine=None,
                agent_id=agent,
                max_items=max(1, min(int(max_items or 5), 20)),
                respect_enabled=True,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"retention run failed: {exc}",
                "durable": False,
                "skill_hint": "due-review",
                "http_contract": "POST /api/education/retention/run",
            }

        status = str((result or {}).get("status") or "")
        reason = str((result or {}).get("reason") or "")
        minted = list((result or {}).get("minted_job_ids") or [])
        success = status == "ok"
        return _json_safe(
            {
                "success": success,
                "durable": bool(minted) and success,
                "agent_id": agent,
                "routine_id": EDUCATION_RETENTION_ROUTINE_ID,
                "result": result,
                "minted_job_ids": minted,
                "skill_hint": "due-review",
                "http_contract": "POST /api/education/retention/run",
                "error": None if success else (reason or status or "retention failed"),
                "note": (
                    "Retention mints standing Jobs for due items; Chat toast is never Done. "
                    "Delivery profiles do not replace ledger/SRS."
                ),
            }
        )

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register Education Learning OS tools on the master ScopedToolRegistry."""
        registry.register_tool(
            name="education_quiz_extract",
            description=(
                "Extract Q/A quiz items from a Wiki note (## Quiz section) and optionally "
                "persist them into the education_mastery ledger (POST /api/education/quiz/extract)."
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
                },
                "required": ["wiki_path"],
            },
            handler=self.education_quiz_extract,
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
            handler=self.education_quiz_next,
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
            handler=self.education_quiz_grade,
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
            handler=self.education_mastery_due,
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
            handler=self.education_mastery_upsert,
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
            handler=self.education_flashcard_next,
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
            handler=self.education_flashcard_grade,
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
            handler=self.education_due_review_list,
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
            handler=self.education_due_review_complete,
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
            handler=self.education_retention_run,
        )
