"""
Education Learning OS — Tutor Agent (Wiki + Ledger Aware) [CARD-326].
Provides topic grounding and Socratic context assembly from existing agent memory.db and Wiki.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.education.learner_model import select_quiz_items
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

logger = logging.getLogger(__name__)


def _verify_memory_repo_invariants(repo: AgentMemoryRepository) -> None:
    """Enforces single memory.db invariant [REQ-EDU-TUTOR-003]. Never allow second storage.db."""
    if not hasattr(repo, "db_path"):
        return
    db_str = str(repo.db_path).replace("\\", "/").lower()
    if "storage.db" in db_str:
        raise ValueError(f"Forbidden: Tutor must use memory.db, received storage.db path: {repo.db_path}")
    if "memory" not in Path(repo.db_path).name.lower() and "memory" not in db_str:
        raise ValueError(f"Forbidden: Expected memory.db path for tutor ledger, got: {repo.db_path}")


def assemble_tutor_topic_context(
    topic: str,
    *,
    memory_repo: Optional[AgentMemoryRepository] = None,
    wiki_tools: Optional[Any] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Assemble Socratic context for the active topic from existing memory.db and Wiki [REQ-EDU-TUTOR-002, REQ-EDU-TUTOR-003].
    """
    clean_topic = (topic or "").strip() or "General Study"
    weak_items: List[Dict[str, Any]] = []
    wiki_paths: List[str] = []

    if memory_repo is not None:
        _verify_memory_repo_invariants(memory_repo)
        try:
            items = select_quiz_items(memory_repo, limit=max(limit * 3, 10), topic=clean_topic)
            weak_items = [
                r for r in items
                if (str(r.get("grade") or "").lower() == "miss") or int(r.get("miss_count") or 0) > 0
            ][:limit]
            if not weak_items and items:
                weak_items = items[:limit]
        except Exception as exc:
            logger.debug("Failed to query mastery items for tutor topic %s: %s", clean_topic, exc)

    if wiki_tools is not None:
        try:
            if hasattr(wiki_tools, "search_notes"):
                search_results = wiki_tools.search_notes(clean_topic)
                if isinstance(search_results, list):
                    wiki_paths = [
                        res.get("relative_path") or res.get("path")
                        for res in search_results[:3]
                        if isinstance(res, dict)
                    ]
        except Exception as exc:
            logger.debug("Failed to search wiki notes for tutor topic %s: %s", clean_topic, exc)

    # Build Socratic prompt clause
    lines = [
        f"[Tutor Topic Grounding: {clean_topic}]",
        f"You are conducting a Socratic tutoring session on '{clean_topic}'.",
    ]
    if weak_items:
        lines.append("Active Mastery Needs / Known Misconceptions:")
        for w in weak_items:
            prompt = w.get("prompt") or "Concept check"
            exp = w.get("expected_answer") or ""
            lines.append(f"- Concept: {prompt} (Target understanding: {exp})")
        lines.append(
            "Instructions: Do NOT reveal these answers directly. Formulate a single, sharp Socratic question "
            "that prompts the learner to explain the foundational mechanism in their own words."
        )
    else:
        lines.append(
            "Instructions: Formulate a probing Socratic inquiry question about this topic to test the learner's "
            "mental model (Feynman technique) and identify any latent misconceptions."
        )

    if wiki_paths:
        lines.append(f"Grounding Wiki Notes: {', '.join(wiki_paths)}")

    prompt_clause = "\n".join(lines)

    return {
        "topic": clean_topic,
        "tutor_agent_id": "tutor",
        "weak_items": weak_items,
        "wiki_paths": wiki_paths,
        "context_prompt_clause": prompt_clause,
    }
