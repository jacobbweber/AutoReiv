"""
Post-turn Cognitive Memory Extractor & Conflict Resolution Engine [CARD-116].

Adopts Andrej Karpathy's compilation principle ("Stop retrieving, start compiling")
with Mem0-style atomic conflict resolution (ADD, UPDATE, DELETE, BUMP).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

logger = logging.getLogger(__name__)

# Small-talk patterns to skip extraction and save compute
_TRIVIAL_UTTERANCE_PATTERN = re.compile(
    r"^(?:thanks?|thank\s+you|ok|okay|k|yes|no|yep|nope|hi|hello|hey|good\s+(?:morning|afternoon|evening)|bye|goodbye|cool|awesome|great|perfect|understood|done)(?:\s+there)?[.!?\s]*$",
    re.IGNORECASE,
)



def should_skip_extraction(user_text: str) -> bool:
    """Determine whether a turn is trivial small talk that warrants skipping extraction."""
    cleaned = user_text.strip()
    if not cleaned or len(cleaned) < 3:
        return True
    return bool(_TRIVIAL_UTTERANCE_PATTERN.match(cleaned))


class CandidateMemoryFact(BaseModel):
    """An atomic fact extracted from conversation turn."""

    action: Literal["ADD", "UPDATE", "DELETE", "BUMP"] = "ADD"
    category: str = Field(default="general", description="'user_pref', 'environment', 'domain', 'constraint'")
    entity: str = Field(description="Target entity, e.g. 'user', 'project', 'system'")
    attribute: str = Field(description="Normalized attribute name, e.g. 'os_platform', 'preferred_language'")
    value: str = Field(default="", description="Fact value string")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


def parse_extraction_response(raw_response: str) -> List[CandidateMemoryFact]:
    """Parse JSON array of candidate facts from LLM output, extracting from markdown blocks if present."""
    text = (raw_response or "").strip()
    if not text:
        return []

    # Strip markdown code fences if wrapped in ```json ... ``` or ``` ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Attempt to isolate array slice [ ... ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except Exception:
                return []
        else:
            return []

    if not isinstance(data, list):
        return []

    candidates: List[CandidateMemoryFact] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            # Normalize action
            raw_action = str(item.get("action", "ADD")).upper().strip()
            if raw_action not in ("ADD", "UPDATE", "DELETE", "BUMP"):
                raw_action = "ADD"
            candidate = CandidateMemoryFact(
                action=raw_action,  # type: ignore[arg-type]
                category=str(item.get("category", "general")).strip().lower() or "general",
                entity=str(item.get("entity", "")).strip().lower(),
                attribute=str(item.get("attribute", "")).strip().lower(),
                value=str(item.get("value", "")).strip(),
                confidence=float(item.get("confidence", 1.0)),
            )
            if candidate.entity and candidate.attribute:
                candidates.append(candidate)
        except Exception as exc:
            logger.debug("Failed to parse candidate fact item %s: %s", item, exc)
            continue

    return candidates


def build_extraction_prompt(user_text: str, assistant_text: str) -> str:
    """Construct lightweight extraction prompt for fast local Ollama or cloud models."""
    return f"""You are AutoReiv's Cognitive Memory Compiler.
Analyze the following conversation turn and extract key enduring facts about the user, project, environment, or constraints.
Output ONLY a valid JSON array of atomic facts according to this schema:
[
  {{
    "action": "ADD" | "UPDATE" | "DELETE" | "BUMP",
    "category": "user_pref" | "environment" | "domain" | "constraint" | "general",
    "entity": "<entity e.g. user, system, project>",
    "attribute": "<snake_case attribute e.g. os_platform, preferred_shell>",
    "value": "<concise fact value>",
    "confidence": 1.0
  }}
]

Guidelines:
- ADD: A newly discovered fact.
- UPDATE: An existing fact that changed.
- DELETE: A fact explicitly contradicted or revoked.
- BUMP: A known fact reaffirmed.
- If there are no durable facts to record, output [].

User: {user_text}
Assistant: {assistant_text}

JSON Output:"""


class MemoryExtractorService:
    """Service executing post-turn atomic fact compilation with conflict resolution."""

    def __init__(
        self,
        repository: AgentMemoryRepository,
        llm_service: Optional[Any] = None,
    ) -> None:
        self.repository = repository
        self.llm_service = llm_service

    def _find_active_fact(self, entity: str, attribute: str) -> Optional[Dict[str, Any]]:
        """Find active fact with matching entity and attribute."""
        with self.repository.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM semantic_facts
                WHERE entity = ? AND attribute = ? AND is_active = 1
                LIMIT 1
                """,
                (entity.strip().lower(), attribute.strip().lower()),
            ).fetchone()
            return dict(row) if row else None

    def apply_candidate_fact(self, candidate: CandidateMemoryFact) -> Dict[str, Any]:
        """Apply candidate fact against the repository with deterministic conflict resolution."""
        existing = self._find_active_fact(candidate.entity, candidate.attribute)

        if candidate.action == "DELETE":
            if existing:
                self.repository.delete_semantic_fact(existing["id"], permanent=False)
                return {"action_taken": "DELETE", "fact_id": existing["id"]}
            return {"action_taken": "SKIPPED", "fact_id": None}

        if candidate.action == "BUMP":
            if existing:
                self.repository.touch_fact(existing["id"])
                return {"action_taken": "BUMP", "fact_id": existing["id"]}
            # If not found, promote to ADD
            fid = self.repository.add_semantic_fact(
                entity=candidate.entity,
                attribute=candidate.attribute,
                value=candidate.value,
                category=candidate.category,
                confidence=candidate.confidence,
            )
            return {"action_taken": "ADD", "fact_id": fid}

        if candidate.action == "UPDATE":
            if existing:
                self.repository.update_semantic_fact(
                    fact_id=existing["id"],
                    value=candidate.value,
                    confidence=candidate.confidence,
                    category=candidate.category,
                )
                return {"action_taken": "UPDATE", "fact_id": existing["id"]}
            # If not found, add it
            fid = self.repository.add_semantic_fact(
                entity=candidate.entity,
                attribute=candidate.attribute,
                value=candidate.value,
                category=candidate.category,
                confidence=candidate.confidence,
            )
            return {"action_taken": "ADD", "fact_id": fid}

        # candidate.action == "ADD"
        if existing:
            # Check if values are essentially identical
            if existing["value"].strip().lower() == candidate.value.strip().lower():
                # Avoid duplicate! Promote to BUMP
                self.repository.touch_fact(existing["id"])
                return {"action_taken": "BUMP", "fact_id": existing["id"]}
            # Contradictory/updated value: Perform in-place UPDATE
            self.repository.update_semantic_fact(
                fact_id=existing["id"],
                value=candidate.value,
                confidence=candidate.confidence,
                category=candidate.category,
            )
            return {"action_taken": "UPDATE", "fact_id": existing["id"]}

        # Fresh new fact
        fid = self.repository.add_semantic_fact(
            entity=candidate.entity,
            attribute=candidate.attribute,
            value=candidate.value,
            category=candidate.category,
            confidence=candidate.confidence,
        )
        return {"action_taken": "ADD", "fact_id": fid}

    async def process_turn(
        self,
        user_text: str,
        assistant_text: str,
    ) -> List[Dict[str, Any]]:
        """Process a completed conversation turn, extract candidate facts, and apply them."""
        if should_skip_extraction(user_text):
            return []

        if self.llm_service is None:
            return []

        prompt = build_extraction_prompt(user_text, assistant_text)
        try:
            raw_response = await self.llm_service.generate(prompt)
            candidates = parse_extraction_response(raw_response)
            results = []
            for candidate in candidates:
                res = self.apply_candidate_fact(candidate)
                results.append(res)
            return results
        except Exception as exc:
            logger.warning("Cognitive memory extraction failed: %s", exc)
            return []
