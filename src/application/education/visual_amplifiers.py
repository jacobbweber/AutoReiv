"""Education Visual Amplifiers: Mermaid + step-through on Retrieval [CARD-249].

Dual Coding Mermaid / step-through deepens real quiz/mastery pedagogy.
An amplifier NEVER ships without a Retrieval path (item_id + mastery ledger).
Amplifiers without Retrieval = edutainment and are refused.
Lumina / concept-player film is OUT of P0.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

AMPLIFIER_ENTITY = "education_amplifier"
AMPLIFIER_CATEGORY = "education_amplifier"
AMPLIFIER_KIND_MERMAID = "mermaid"
AMPLIFIER_KIND_STEP_THROUGH = "step_through"
AMPLIFIER_FACT_PREFIX = "edu_amp_"

_MERMAID_FENCE_RE = re.compile(
    r"```(?:mermaid)\s*\n(?P<body>.*?)```",
    re.IGNORECASE | re.DOTALL,
)
_STEP_SECTION_RE = re.compile(
    r"^##\s+Step-through\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FLOW_NODE_RE = re.compile(
    r"(?P<id>[A-Za-z][\w]*)\s*(?:\[(?P<sq>[^\]]+)\]|\((?P<round>[^\)]+)\)|\{(?P<diamond>[^\}]+)\}|\(\((?P<stadium>[^\)]+)\)\))",
)
_SEQ_PARTICIPANT_RE = re.compile(
    r"^\s*(?:participant|actor)\s+(?P<label>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SEQ_MSG_RE = re.compile(
    r"^\s*(?P<from>\S+)\s*(?:-->>?|->>?)\s*(?P<to>\S+)\s*:\s*(?P<msg>.+?)\s*$",
    re.MULTILINE,
)
_BULLET_STEP_RE = re.compile(
    r"^[-\*]\s+(?:\d+[\.\)]\s+)?(?P<label>.+?)\s*$",
    re.MULTILINE,
)


class VisualsOnlyRejected(ValueError):
    """Raised when an amplifier lacks a Retrieval (quiz/mastery) path."""


def _iso_now(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _amp_id_for(wiki_path: str, mermaid_body: str, kind: str) -> str:
    digest = hashlib.sha1(f"{wiki_path}|{kind}|{mermaid_body}".encode("utf-8")).hexdigest()[:12]
    return f"amp_{digest}"


def _fact_id_for_item(item_id: str) -> str:
    return f"{AMPLIFIER_FACT_PREFIX}{item_id}"


def extract_mermaid_blocks(content: str) -> List[str]:
    """Return fenced Mermaid bodies from a Dual Coding / study note."""
    return [m.group("body").strip() for m in _MERMAID_FENCE_RE.finditer(content or "") if m.group("body").strip()]


def _parse_explicit_step_through(content: str) -> List[Dict[str, Any]]:
    text = content or ""
    m = _STEP_SECTION_RE.search(text)
    if not m:
        return []
    rest = text[m.end() :]
    nxt = re.search(r"^##\s+\S", rest, re.MULTILINE)
    section = rest[: nxt.start()] if nxt else rest
    steps: List[Dict[str, Any]] = []
    for i, match in enumerate(_BULLET_STEP_RE.finditer(section), start=1):
        label = (match.group("label") or "").strip()
        if not label:
            continue
        steps.append({"order": i, "label": label, "source": "step_through_section"})
    return steps


def build_step_through(mermaid_source: str, *, note_content: str = "") -> List[Dict[str, Any]]:
    """Build ordered pedagogy steps from Mermaid and/or ## Step-through section.

    Prefer explicit ## Step-through bullets when present; else derive from
    flowchart nodes / sequence messages (deterministic, no LLM).
    """
    explicit = _parse_explicit_step_through(note_content)
    if explicit:
        return explicit

    src = mermaid_source or ""
    steps: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # Sequence diagram messages (ordered pedagogy signal)
    for match in _SEQ_MSG_RE.finditer(src):
        label = f"{match.group('from')} -> {match.group('to')}: {match.group('msg').strip()}"
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        steps.append({"order": len(steps) + 1, "label": label, "source": "sequence_message"})

    if steps:
        return steps

    # Flowchart / graph nodes in document order
    for match in _FLOW_NODE_RE.finditer(src):
        label = (
            match.group("sq")
            or match.group("round")
            or match.group("diamond")
            or match.group("stadium")
            or match.group("id")
        )
        label = (label or "").strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        steps.append(
            {
                "order": len(steps) + 1,
                "label": label,
                "node_id": match.group("id"),
                "source": "flowchart_node",
            }
        )

    if steps:
        return steps

    # Participants as weak fallback
    for match in _SEQ_PARTICIPANT_RE.finditer(src):
        label = (match.group("label") or "").strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        steps.append({"order": len(steps) + 1, "label": label, "source": "sequence_participant"})

    return steps


def extract_amplifiers_from_note(
    content: str,
    *,
    wiki_path: str,
    topic: str = "",
) -> List[Dict[str, Any]]:
    """Extract Mermaid + step-through amplifier candidates from a Dual Coding note.

    Candidates are NOT shippable until attached to a Retrieval item_id.
    """
    text = content or ""
    blocks = extract_mermaid_blocks(text)
    amplifiers: List[Dict[str, Any]] = []
    for body in blocks:
        steps = build_step_through(body, note_content=text)
        amp_id = _amp_id_for(wiki_path, body, AMPLIFIER_KIND_MERMAID)
        amplifiers.append(
            {
                "amplifier_id": amp_id,
                "kind": AMPLIFIER_KIND_MERMAID,
                "topic": topic or wiki_path,
                "wiki_path": wiki_path,
                "mermaid": body,
                "steps": steps,
                "step_count": len(steps),
                "has_step_through": bool(steps),
                "retrieval_required": True,
                "item_id": None,
                "shippable": False,
                "lumina_film": False,
            }
        )
    # Explicit step-through without Mermaid still needs a diagram OR is incomplete;
    # only emit a step_through-only candidate if Mermaid missing but section exists
    # AND we refuse to mark shippable without Retrieval + preferably Mermaid.
    if not blocks:
        steps = _parse_explicit_step_through(text)
        if steps:
            amp_id = _amp_id_for(wiki_path, json.dumps(steps), AMPLIFIER_KIND_STEP_THROUGH)
            amplifiers.append(
                {
                    "amplifier_id": amp_id,
                    "kind": AMPLIFIER_KIND_STEP_THROUGH,
                    "topic": topic or wiki_path,
                    "wiki_path": wiki_path,
                    "mermaid": None,
                    "steps": steps,
                    "step_count": len(steps),
                    "has_step_through": True,
                    "retrieval_required": True,
                    "item_id": None,
                    "shippable": False,
                    "lumina_film": False,
                }
            )
    return amplifiers


def require_retrieval_path(
    item_id: Optional[str],
    repo: Any = None,
    *,
    mastery_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate Retrieval path; raise VisualsOnlyRejected if missing/unknown."""
    iid = (item_id or "").strip()
    if not iid:
        raise VisualsOnlyRejected(
            "Amplifier refused: missing item_id (Retrieval path required; visuals-only = edutainment)"
        )
    row = mastery_row
    if row is None and repo is not None:
        try:
            row = repo.get_education_mastery(iid)
        except Exception:  # noqa: BLE001
            row = None
    if row is None:
        raise VisualsOnlyRejected(
            f"Amplifier refused: item_id={iid} not on mastery ledger (Retrieval path required)"
        )
    return dict(row)


def attach_amplifier_to_retrieval(
    amplifier: Dict[str, Any],
    item_id: str,
    *,
    repo: Any,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Attach amplifier to a mastery/quiz item and persist linkage in memory.db."""
    row = require_retrieval_path(item_id, repo)
    attached = dict(amplifier or {})
    attached["item_id"] = item_id
    attached["topic"] = attached.get("topic") or row.get("topic")
    attached["wiki_path"] = attached.get("wiki_path") or row.get("wiki_path")
    attached["prompt"] = row.get("prompt")
    attached["shippable"] = True
    attached["retrieval_required"] = True
    attached["retrieval_path"] = "mastery_ledger_quiz"
    attached["lumina_film"] = False
    attached["attached_at"] = _iso_now(now)

    fact_id = _fact_id_for_item(item_id)
    value = json.dumps(
        {
            "amplifier_id": attached.get("amplifier_id"),
            "kind": attached.get("kind"),
            "item_id": item_id,
            "wiki_path": attached.get("wiki_path"),
            "mermaid": attached.get("mermaid"),
            "steps": attached.get("steps") or [],
            "attached_at": attached["attached_at"],
            "retrieval_path": "mastery_ledger_quiz",
            "lumina_film": False,
        },
        ensure_ascii=False,
    )
    _upsert_amplifier_fact(repo, fact_id=fact_id, item_id=item_id, value=value)
    attached["fact_id"] = fact_id
    return attached


def _upsert_amplifier_fact(repo: Any, *, fact_id: str, item_id: str, value: str) -> str:
    existing = None
    try:
        existing = repo.get_semantic_fact(fact_id)
    except Exception:  # noqa: BLE001
        existing = None
    if existing:
        try:
            with repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, category = ?, confidence = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                    (value, AMPLIFIER_CATEGORY, 1.0, fact_id),
                )
            return fact_id
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=AMPLIFIER_ENTITY,
            attribute=f"amplifier_for_{item_id}",
            value=value,
            category=AMPLIFIER_CATEGORY,
            confidence=1.0,
            decay_half_life_days=365.0,
            fact_id=fact_id,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fact_id,
                value=value,
                category=AMPLIFIER_CATEGORY,
                confidence=1.0,
            )
        except Exception:  # noqa: BLE001
            pass
        return fact_id


def get_amplifier_for_item(repo: Any, item_id: str) -> Optional[Dict[str, Any]]:
    """Load persisted amplifier for a mastery item; None if unset."""
    require_retrieval_path(item_id, repo)
    fact_id = _fact_id_for_item(item_id)
    try:
        fact = repo.get_semantic_fact(fact_id)
    except Exception:  # noqa: BLE001
        fact = None
    if not fact or int(fact.get("is_active") or 0) != 1:
        return None
    try:
        payload = json.loads(str(fact.get("value") or "{}"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    payload["fact_id"] = fact_id
    payload["shippable"] = True
    payload["retrieval_required"] = True
    payload["lumina_film"] = False
    return payload


def amplify_quiz_items(
    items: Sequence[Dict[str, Any]],
    repo: Any,
) -> Dict[str, Any]:
    """Attach shippable amplifiers to quiz items that have Retrieval + stored amp.

    Items without amplifiers pass through unchanged. Never invents visuals-only rows.
    Does not mutate ledger fields (next_due / grade / interval_stage).
    """
    amplified: List[Dict[str, Any]] = []
    with_amp = 0
    for row in items or []:
        copy_row = dict(row)
        iid = str(copy_row.get("item_id") or "").strip()
        amp = None
        if iid:
            try:
                amp = get_amplifier_for_item(repo, iid)
            except VisualsOnlyRejected:
                amp = None
            except Exception:  # noqa: BLE001
                amp = None
        if amp:
            copy_row["amplifier"] = amp
            copy_row["amplifier_mermaid"] = amp.get("mermaid")
            copy_row["amplifier_steps"] = amp.get("steps") or []
            copy_row["has_visual_amplifier"] = True
            with_amp += 1
        else:
            copy_row["has_visual_amplifier"] = False
        amplified.append(copy_row)
    return {
        "items": amplified,
        "amplified_count": with_amp,
        "count": len(amplified),
        "retrieval_required": True,
        "lumina_film": False,
        "replaces_srs": False,
        "replaces_ledger": False,
    }


def refuse_visuals_only(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Explicit guard used by API: visuals-only / missing Retrieval is refused."""
    data = dict(payload or {})
    item_id = data.get("item_id")
    visuals_only = bool(data.get("visuals_only"))
    if visuals_only or not (item_id or "").strip():
        raise VisualsOnlyRejected(
            "Amplifier refused: visuals-only / missing Retrieval path (edutainment guard) [CARD-249]"
        )
    return {"ok": True, "item_id": item_id, "visuals_only": False}


def build_amplifier_ask_clause(amplifier: Optional[Dict[str, Any]] = None) -> str:
    """Ask clause that pairs Dual Coding visual with Retrieval - never visuals-only."""
    if not amplifier or not amplifier.get("item_id"):
        return (
            " Visual amplifiers: only attach Mermaid/step-through to Retrieval-backed quiz items;"
            " never ship visuals-only (edutainment guard CARD-249). Lumina film is OUT."
        )
    steps = amplifier.get("steps") or []
    step_bit = ""
    if steps:
        preview = "; ".join(f"{s.get('order')}. {s.get('label')}" for s in steps[:5])
        step_bit = f" Step-through: {preview}."
    return (
        f" Visual amplifier `{amplifier.get('amplifier_id')}` on Retrieval item"
        f" `{amplifier.get('item_id')}` (kind={amplifier.get('kind')})."
        f" Show Mermaid Dual Coding visual beside the quiz prompt; do not skip Retrieval."
        f"{step_bit}"
        " Lumina / concept-player film is OUT of P0."
        " Do NOT change next_due / interval_stage / Routine->Job SRS based on the amplifier."
    )


def assert_amplifier_does_not_touch_srs(module_source: Optional[str] = None) -> bool:
    """Static guard: amplifiers must not own SRS/due writes or Lumina film runtime."""
    src = module_source
    if src is None:
        import src.application.education.visual_amplifiers as mod

        src = inspect.getsource(mod)
    marker = "def assert_amplifier_does_not_touch_srs"
    if marker in src:
        before, _, rest = src.partition(marker)
        nxt = rest.find("\ndef ")
        src_wo_guard = before + (rest[nxt + 1 :] if nxt >= 0 else "")
    else:
        src_wo_guard = src
    forbidden_calls = (
        "record_education_grade",
        "next_due_after_grade",
        "list_due_education_mastery",
        "upsert_education_mastery",
        "create_job_from_catalog_resolve",
    )
    for name in forbidden_calls:
        if re.search(rf"\b{re.escape(name)}\s*\(", src_wo_guard):
            return False
    low = src_wo_guard.lower()
    banned_bits = (
        "import openai",
        "from openai",
        "ollama",
        "llm_gateway",
        "gateway.complete",
        "chat.completions",
    )
    for bit in banned_bits:
        if bit in low:
            return False
    # Lumina / concept-player film runtime is OUT of P0. Docs + lumina_film:False flags OK;
    # ban actual imports / player wiring only.
    runtime_lumina = (
        r"from\s+[\w.]*lumina",
        r"import\s+[\w.]*lumina",
        r"concept_player\s*\(",
        r"ConceptPlayer",
        r"lumina_film_player",
        r"play_lumina",
    )
    for pat in runtime_lumina:
        if re.search(pat, src_wo_guard, re.IGNORECASE):
            return False
    return True


def summarize_amplifiers(repo: Any, *, limit: int = 50) -> Dict[str, Any]:
    """List persisted amplifier attachments from memory.db."""
    facts: List[Dict[str, Any]] = []
    try:
        with repo.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, entity, attribute, value, category, is_active FROM semantic_facts "
                "WHERE category = ? AND is_active = 1 ORDER BY updated_at DESC LIMIT ?",
                (AMPLIFIER_CATEGORY, max(1, int(limit))),
            ).fetchall()
        for r in rows:
            d = dict(r) if not isinstance(r, dict) else r
            try:
                payload = json.loads(str(d.get("value") or "{}"))
            except json.JSONDecodeError:
                payload = {"raw": d.get("value")}
            facts.append({"fact_id": d.get("id"), **(payload if isinstance(payload, dict) else {"payload": payload})})
    except Exception:  # noqa: BLE001
        facts = []
    return {
        "entity": AMPLIFIER_ENTITY,
        "category": AMPLIFIER_CATEGORY,
        "amplifiers": facts,
        "count": len(facts),
        "retrieval_required": True,
        "lumina_film": False,
        "replaces_srs": False,
        "replaces_ledger": False,
    }
