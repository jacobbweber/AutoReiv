"""Standing Job/Phase cross-phase cognitive memory bridge [CARD-226 / CARD-253].

Persists phase reflections/facts into per-agent <slug>_memory.db (CARD-116)
and recalls them after kill/resume. Never touches <slug>_storage.db.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from src.infrastructure.data.resolver import resolve_agent_memory_path
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

logger = logging.getLogger(__name__)

# CARD-253: refuse transcript dumps as memory facts.
try:
    from src.application.orchestration.working_set_context import (
        MEMORY_FACT_MAX_CHARS,
        assert_not_transcript_memory,
        looks_like_transcript_dump,
        sanitize_memory_fact,
    )
except Exception:  # pragma: no cover - circular import soft path
    MEMORY_FACT_MAX_CHARS = 500

    def looks_like_transcript_dump(text: str) -> bool:  # type: ignore
        return False

    def sanitize_memory_fact(text: str, **_kwargs):  # type: ignore
        t = (text or "").strip()
        return t[:MEMORY_FACT_MAX_CHARS] if t else None

    def assert_not_transcript_memory(text: str) -> str:  # type: ignore
        out = sanitize_memory_fact(text)
        if not out:
            raise ValueError("rejected memory fact")
        return out


_JOB_ENTITY_PREFIX = "job:"


def assert_memory_db_path(path: Union[str, Path]) -> Path:
    """Reject storage.db / non-memory cognitive paths [REQ-JPMEM-001]."""
    p = Path(path)
    name = p.name.lower()
    if name.endswith("_storage.db") or name == "storage.db":
        raise ValueError(f"Cognitive memory must not use storage.db path: {p}")
    if not name.endswith("_memory.db"):
        raise ValueError(f"Cognitive memory path must end with _memory.db: {p}")
    return p


def job_entity(job_id: str) -> str:
    return f"{_JOB_ENTITY_PREFIX}{job_id}"


def _slug(text: str, fallback: str = "phase") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip()).strip("_").lower()
    return (cleaned[:48] or fallback)


class JobPhaseMemoryBridge:
    """Write/recall job-scoped facts via CARD-116 AgentMemoryRepository."""

    def __init__(
        self,
        agent_id: str,
        data_dir: Optional[Union[str, Path]] = None,
        repository: Optional[AgentMemoryRepository] = None,
    ) -> None:
        self.agent_id = agent_id
        if repository is not None:
            self.repository = repository
            self.db_path = assert_memory_db_path(repository.db_path)
        else:
            path = resolve_agent_memory_path(agent_id, data_dir=data_dir)
            self.db_path = assert_memory_db_path(path)
            self.repository = AgentMemoryRepository(db_path=self.db_path)
        self.repository.initialize_schema()

    def persist_phase_facts(
        self,
        *,
        job_id: str,
        phase_index: int,
        phase_name: str,
        facts: Sequence[str],
    ) -> List[str]:
        """Persist phase reflections into memory.db; return fact ids [REQ-JPMEM-002]."""
        entity = job_entity(job_id)
        phase_slug = _slug(phase_name, fallback=f"phase_{phase_index}")
        fact_ids: List[str] = []
        cleaned: List[str] = []
        for f in facts or []:
            raw = str(f).strip()
            if not raw:
                continue
            # CARD-253 / REQ-LRCTX-003: full transcript dumps must not enter memory.db.
            if looks_like_transcript_dump(raw):
                logger.warning(
                    "Rejecting transcript dump masquerading as memory fact (job=%s phase=%s)",
                    job_id,
                    phase_index,
                )
                continue
            sanitized = sanitize_memory_fact(raw, max_chars=MEMORY_FACT_MAX_CHARS)
            if sanitized:
                cleaned.append(sanitized)
        if not cleaned:
            return fact_ids

        # Episodic milestone for the phase (job-scoped session id).
        try:
            self.repository.record_session_summary(
                session_id=f"job:{job_id}:phase:{phase_index}",
                summary=f"Phase {phase_index} ({phase_name}): " + "; ".join(cleaned)[:1800],
                key_decisions=cleaned[:12],
                turn_count=1,
                outcome_status="completed",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Job phase session summary skipped: %s", exc)

        for i, value in enumerate(cleaned):
            attr = f"phase_{phase_index}_{phase_slug}_{i}"
            try:
                fid = self.repository.add_semantic_fact(
                    entity=entity,
                    attribute=attr,
                    value=value[: max(MEMORY_FACT_MAX_CHARS, 500)],
                    category="job_phase",
                    confidence=1.0,
                )
                fact_ids.append(fid)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed persisting job phase fact: %s", exc)
        return fact_ids

    def recall_job_facts(self, *, job_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recall job-scoped semantic facts from memory.db only."""
        entity = job_entity(job_id)
        try:
            return self.repository.list_facts_for_entity(entity, limit=limit)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Job phase memory recall failed: %s", exc)
            return []

    def recall_lines(self, *, job_id: str, limit: int = 50) -> List[str]:
        facts = self.recall_job_facts(job_id=job_id, limit=limit)
        lines: List[str] = []
        for f in facts:
            attr = f.get("attribute") or "fact"
            val = (f.get("value") or "").strip()
            if val:
                lines.append(f"{attr}: {val}")
        return lines


def persist_phase_memory_for_job(
    *,
    agent_id: str,
    job_id: str,
    phase_index: int,
    phase_name: str,
    facts: Sequence[str],
    data_dir: Optional[Union[str, Path]] = None,
) -> List[str]:
    bridge = JobPhaseMemoryBridge(agent_id=agent_id, data_dir=data_dir)
    return bridge.persist_phase_facts(
        job_id=job_id,
        phase_index=phase_index,
        phase_name=phase_name,
        facts=facts,
    )


def prior_lines_from_job_memory(
    *,
    agent_id: str,
    job_id: str,
    data_dir: Optional[Union[str, Path]] = None,
    limit: int = 50,
) -> List[str]:
    """Durable prior lines for phase_assignment_prompt after kill/resume [REQ-JPMEM-003].

    CARD-253: filter transcript-shaped lines so dumps never re-enter working set.
    """
    bridge = JobPhaseMemoryBridge(agent_id=agent_id, data_dir=data_dir)
    lines = bridge.recall_lines(job_id=job_id, limit=limit)
    safe: List[str] = []
    for line in lines:
        if looks_like_transcript_dump(line):
            continue
        sanitized = sanitize_memory_fact(line)
        if sanitized:
            safe.append(sanitized)
    return safe
