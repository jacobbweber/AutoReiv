"""Education Environment: study-session delivery profiles [CARD-248].

Tone / timer / ADHD bite-size shape Ask + quiz *presentation* only.
Mastery ledger + Routine->Job SRS remain the sole source of truth for
due/resurface. Delivery profiles never rewrite next_due or invent a
second tutor due engine.
"""

from __future__ import annotations

import copy
import inspect
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

ENVIRONMENT_ENTITY = "education_environment"
ENVIRONMENT_CATEGORY = "education_environment"
ACTIVE_PROFILE_FACT_ID = "edu_env_active_profile"
ACTIVE_PROFILE_ATTRIBUTE = "active_delivery_profile"

# Built-in delivery profiles (presentation knobs only).
PROFILE_DEFAULT = "default"
PROFILE_CALM_FOCUS = "calm_focus"
PROFILE_ADHD_BITE = "adhd_bite"
PROFILE_POMODORO = "pomodoro"

DELIVERY_PROFILES: Dict[str, Dict[str, Any]] = {
    PROFILE_DEFAULT: {
        "id": PROFILE_DEFAULT,
        "label": "Default",
        "tone": "clear_stepwise",
        "tone_instruction": "Clear, stepwise explanation with one concrete example.",
        "timer_seconds": None,
        "bite_size": False,
        "max_prompt_chars": None,
        "max_items_per_wave": None,
        "research_note": "Neutral delivery; ledger/SRS unchanged.",
    },
    PROFILE_CALM_FOCUS: {
        "id": PROFILE_CALM_FOCUS,
        "label": "Calm focus",
        "tone": "calm_encouraging",
        "tone_instruction": "Calm, encouraging tone; one idea at a time; no urgency language.",
        "timer_seconds": 600,
        "bite_size": False,
        "max_prompt_chars": None,
        "max_items_per_wave": None,
        "research_note": "Session timer hint only; does not change due intervals.",
    },
    PROFILE_ADHD_BITE: {
        "id": PROFILE_ADHD_BITE,
        "label": "ADHD bite-size",
        "tone": "short_supportive",
        "tone_instruction": (
            "Short supportive tone; one micro-prompt at a time; celebrate small wins; "
            "never dump long multi-part quizzes in one wave."
        ),
        "timer_seconds": 120,
        "bite_size": True,
        "max_prompt_chars": 160,
        "max_items_per_wave": 1,
        "research_note": (
            "ADHD bite-size is delivery-only research styling - never replaces "
            "1-3-7-30 SRS or mastery ledger due/resurface."
        ),
    },
    PROFILE_POMODORO: {
        "id": PROFILE_POMODORO,
        "label": "Pomodoro",
        "tone": "focused",
        "tone_instruction": "Focused tone; protect the block; concise prompts; break when timer ends.",
        "timer_seconds": 1500,
        "bite_size": False,
        "max_prompt_chars": None,
        "max_items_per_wave": None,
        "research_note": "Pomodoro timer is presentation only; SRS due dates stay on the ledger.",
    },
}


def list_delivery_profiles() -> List[Dict[str, Any]]:
    """Return built-in study-session delivery profiles."""
    return [copy.deepcopy(DELIVERY_PROFILES[k]) for k in DELIVERY_PROFILES]


def get_delivery_profile(profile_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve a profile id; unknown/empty falls back to default."""
    pid = (profile_id or PROFILE_DEFAULT).strip().casefold()
    if pid not in DELIVERY_PROFILES:
        pid = PROFILE_DEFAULT
    return copy.deepcopy(DELIVERY_PROFILES[pid])


def _iso_now(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upsert_fact(
    repo: Any,
    *,
    fact_id: str,
    attribute: str,
    value: str,
    confidence: float = 1.0,
) -> str:
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
                    (value, ENVIRONMENT_CATEGORY, confidence, fact_id),
                )
            return fact_id
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=ENVIRONMENT_ENTITY,
            attribute=attribute,
            value=value,
            category=ENVIRONMENT_CATEGORY,
            confidence=confidence,
            decay_half_life_days=365.0,
            fact_id=fact_id,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fact_id,
                value=value,
                category=ENVIRONMENT_CATEGORY,
                confidence=confidence,
            )
        except Exception:  # noqa: BLE001
            pass
        return fact_id


def select_delivery_profile(
    repo: Any,
    profile_id: str,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Persist active delivery profile preference in memory.db (not SRS)."""
    profile = get_delivery_profile(profile_id)
    stamp = _iso_now(now)
    value = (
        f"active_delivery_profile id={profile['id']} tone={profile['tone']} "
        f"timer_seconds={profile['timer_seconds']} bite_size={profile['bite_size']} "
        f"at={stamp} - delivery preference only; ledger/SRS unchanged"
    )
    _upsert_fact(
        repo,
        fact_id=ACTIVE_PROFILE_FACT_ID,
        attribute=ACTIVE_PROFILE_ATTRIBUTE,
        value=value,
        confidence=1.0,
    )
    return {
        "profile": profile,
        "fact_id": ACTIVE_PROFILE_FACT_ID,
        "selected": True,
        "replaces_srs": False,
        "replaces_ledger": False,
    }


def get_active_delivery_profile(repo: Any) -> Dict[str, Any]:
    """Read active profile preference from memory.db; default if unset."""
    try:
        fact = repo.get_semantic_fact(ACTIVE_PROFILE_FACT_ID)
    except Exception:  # noqa: BLE001
        fact = None
    if not fact or int(fact.get("is_active") or 0) != 1:
        return get_delivery_profile(PROFILE_DEFAULT)
    val = str(fact.get("value") or "")
    m = re.search(r"\bid=([a-z0-9_]+)", val)
    pid = m.group(1) if m else PROFILE_DEFAULT
    return get_delivery_profile(pid)


def shape_prompt_for_profile(prompt: str, profile: Dict[str, Any]) -> str:
    """Truncate / wrap a single prompt for bite-size presentation (display only)."""
    text = (prompt or "").strip()
    max_chars = profile.get("max_prompt_chars")
    if not profile.get("bite_size") or not max_chars:
        return text
    limit = int(max_chars)
    if len(text) <= limit:
        return text
    cut = text[: max(1, limit - 1)].rstrip()
    return cut + "…"


def shape_quiz_presentation(
    items: Sequence[Dict[str, Any]],
    profile_id: Optional[str] = None,
    *,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Attach delivery presentation metadata to quiz items without mutating ledger fields.

    Returns shaped *copies*. Underlying mastery rows / next_due are never rewritten.
    Bite-size may limit how many items are *presented* in the wave; the full due set
    remains ledger-sourced for SRS / retention.
    """
    prof = profile or get_delivery_profile(profile_id)
    source = list(items or [])
    # Preserve ledger fields on copies; only add presentation_* keys.
    shaped: List[Dict[str, Any]] = []
    for row in source:
        copy_row = dict(row)
        original_prompt = str(copy_row.get("prompt") or "")
        presented = shape_prompt_for_profile(original_prompt, prof)
        copy_row["presentation_prompt"] = presented
        copy_row["presentation_tone"] = prof.get("tone")
        copy_row["delivery_profile_id"] = prof.get("id")
        # Never strip ledger truth from the copy
        shaped.append(copy_row)

    wave_cap = prof.get("max_items_per_wave")
    presented_items = list(shaped)
    if wave_cap is not None:
        cap = max(1, int(wave_cap))
        presented_items = shaped[:cap]

    return {
        "profile": prof,
        "items": presented_items,
        "all_items": shaped,
        "presented_count": len(presented_items),
        "ledger_count": len(shaped),
        "timer_seconds": prof.get("timer_seconds"),
        "tone": prof.get("tone"),
        "bite_size": bool(prof.get("bite_size")),
        "replaces_srs": False,
        "replaces_ledger": False,
        "due_source": "mastery_ledger_srs",
    }


def build_environment_ask_clause(profile: Optional[Dict[str, Any]] = None) -> str:
    """Ask clause that applies delivery tone/timer without touching due/SRS."""
    prof = profile or get_delivery_profile(PROFILE_DEFAULT)
    timer = prof.get("timer_seconds")
    timer_bit = (
        f" Session timer hint: {int(timer)} seconds (presentation only)."
        if timer
        else " No session timer."
    )
    bite = ""
    if prof.get("bite_size"):
        bite = (
            " ADHD bite-size delivery: one micro-prompt per wave; keep language short;"
            " never replace mastery ledger due/resurface or 1-3-7-30 SRS."
        )
    return (
        f" Delivery profile `{prof.get('id')}` (tone={prof.get('tone')})."
        f" How to present: {prof.get('tone_instruction')}"
        f"{timer_bit}{bite}"
        " Do NOT change next_due / interval_stage / Routine->Job SRS based on this profile."
    )


def apply_delivery_to_ask(
    ask_text: str,
    profile_id: Optional[str] = None,
    *,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Shape an Ask string with delivery clause; returns presentation metadata."""
    prof = profile or get_delivery_profile(profile_id)
    clause = build_environment_ask_clause(prof)
    base = (ask_text or "").rstrip()
    shaped = f"{base}{clause}" if base else clause.strip()
    return {
        "ask": shaped,
        "profile": prof,
        "timer_seconds": prof.get("timer_seconds"),
        "tone": prof.get("tone"),
        "bite_size": bool(prof.get("bite_size")),
        "replaces_srs": False,
        "replaces_ledger": False,
    }


def assert_profile_does_not_touch_srs(module_source: Optional[str] = None) -> bool:
    """Static guard used by tests: environment module must not own SRS/due writes."""
    src = module_source
    if src is None:
        import src.application.education.environment as mod

        src = inspect.getsource(mod)
    marker = "def assert_profile_does_not_touch_srs"
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
    return True

def summarize_environment(repo: Any) -> Dict[str, Any]:
    active = get_active_delivery_profile(repo)
    return {
        "entity": ENVIRONMENT_ENTITY,
        "category": ENVIRONMENT_CATEGORY,
        "active_profile": active,
        "profiles": list_delivery_profiles(),
        "replaces_srs": False,
        "replaces_ledger": False,
        "due_source": "mastery_ledger_srs",
    }
