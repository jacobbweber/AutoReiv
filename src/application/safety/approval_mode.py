"""Live ApprovalMode (`strict`, `balanced`, `hands_off`) and Tool Effect Tiers [CARD-701].

Adapted from Crucible (`ADR-0015` §4.6, `docs/architecture-comparison-crucible-agent-os.md` §5 & §7.1):
- Resolves `approval_mode` from persisted SQLite `settings` (`approval_mode` or `purpose_matrix.approval_mode`)
  with fallback to `AUTOREIV_APPROVAL_MODE` environment variable and default `"balanced"`.
- Classifies tools into three effect tiers (`read_only`, `state_change`, `destructive`) based on declared
  `RISK` and AST outside-access detection (`network`, `files`, `programs`, `hidden_imports`).
- Enforces the 3x3 autonomy matrix across tool/skill authoring and tool execution without server restarts:
  - `strict`: both `read_only` and `state_change` tools require operator approval to enable/run.
  - `balanced` (default): smoke-verified `read_only` tools auto-enable and mount; `state_change` and
    `destructive` tools save disabled for operator approval.
  - `hands_off`: smoke-verified `read_only` and `state_change` tools auto-enable and run without confirmation;
    `destructive` tools still gate on operator approval.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

APPROVAL_MODE_SETTING_KEY = "approval_mode"
APPROVAL_MODE_ENV = "AUTOREIV_APPROVAL_MODE"
DEFAULT_APPROVAL_MODE = "balanced"

VALID_APPROVAL_MODES: tuple[str, ...] = ("strict", "balanced", "hands_off")
VALID_TOOL_EFFECTS: tuple[str, ...] = ("read_only", "state_change", "destructive")

_MODE_ALIASES: dict[str, str] = {
    "strict": "strict",
    "ask": "strict",
    "balanced": "balanced",
    "hands_off": "hands_off",
    "hands-off": "hands_off",
    "handsoff": "hands_off",
    "autonomous": "hands_off",
    "run": "hands_off",
}


def normalize_approval_mode(raw: Any) -> str | None:
    """Normalize an approval mode string to `'strict' | 'balanced' | 'hands_off'`, or None if invalid/empty."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    if isinstance(raw, dict):
        nested = raw.get("approval_mode") or raw.get("mode")
        return normalize_approval_mode(nested)
    return _MODE_ALIASES.get(text)


def _fallback_store(store: Any = None) -> Any:
    if store is not None and hasattr(store, "get_setting"):
        return store
    from src.application.kernel import reply_limits

    return getattr(reply_limits, "_bound_store", None)


def resolve_approval_mode_info(store: Any = None) -> dict[str, Any]:
    """Return `{'approval_mode': str, 'source': 'setting'|'env'|'default', 'saved': str|None}`."""
    st = _fallback_store(store)
    saved_mode: str | None = None
    if st is not None and hasattr(st, "get_setting"):
        try:
            raw_setting = st.get_setting(APPROVAL_MODE_SETTING_KEY)
            saved_mode = normalize_approval_mode(raw_setting)
            if saved_mode is None:
                matrix_raw = st.get_setting("purpose_matrix")
                if isinstance(matrix_raw, dict):
                    saved_mode = normalize_approval_mode(matrix_raw.get("approval_mode"))
        except Exception:
            saved_mode = None

    if saved_mode is not None:
        return {
            "key": APPROVAL_MODE_SETTING_KEY,
            "mode": saved_mode,
            "approval_mode": saved_mode,
            "source": "setting",
            "saved": saved_mode,
            "valid_modes": list(VALID_APPROVAL_MODES),
        }

    env_mode = normalize_approval_mode(os.environ.get(APPROVAL_MODE_ENV))
    if env_mode is not None:
        return {
            "key": APPROVAL_MODE_SETTING_KEY,
            "mode": env_mode,
            "approval_mode": env_mode,
            "source": "env",
            "saved": None,
            "valid_modes": list(VALID_APPROVAL_MODES),
        }

    return {
        "key": APPROVAL_MODE_SETTING_KEY,
        "mode": DEFAULT_APPROVAL_MODE,
        "approval_mode": DEFAULT_APPROVAL_MODE,
        "source": "default",
        "saved": None,
        "valid_modes": list(VALID_APPROVAL_MODES),
    }


def resolve_approval_mode(store: Any = None) -> str:
    """Resolve active runtime `ApprovalMode` (`'strict' | 'balanced' | 'hands_off'`)."""
    return str(resolve_approval_mode_info(store)["approval_mode"])


def save_approval_mode(store: Any, mode: Any) -> dict[str, Any]:
    """Persist or clear the runtime `approval_mode` setting in SQLite (`None` or `''` clears override)."""
    st = _fallback_store(store)
    if st is None or not hasattr(st, "set_setting"):
        raise RuntimeError("No state store available to persist approval_mode.")

    raw_str = "" if mode is None else str(mode).strip()
    if not raw_str:
        st.set_setting(APPROVAL_MODE_SETTING_KEY, None)
        matrix_raw = st.get_setting("purpose_matrix")
        if isinstance(matrix_raw, dict) and "approval_mode" in matrix_raw:
            updated = dict(matrix_raw)
            updated.pop("approval_mode", None)
            st.set_setting("purpose_matrix", updated)
        return resolve_approval_mode_info(st)

    normalized = normalize_approval_mode(raw_str)
    if normalized is None:
        raise ValueError(
            f"Invalid approval_mode '{raw_str}'. Must be one of: {', '.join(VALID_APPROVAL_MODES)}."
        )

    st.set_setting(APPROVAL_MODE_SETTING_KEY, normalized)
    matrix_raw = st.get_setting("purpose_matrix")
    if isinstance(matrix_raw, dict):
        updated = dict(matrix_raw)
        updated["approval_mode"] = normalized
        st.set_setting("purpose_matrix", updated)
    return resolve_approval_mode_info(st)


def classify_tool_effect(*, risk: str = "read_only", access: Sequence[str] | None = None) -> str:
    """Classify a tool into `'read_only' | 'state_change' | 'destructive'`."""
    clean_risk = str(risk or "read_only").strip().lower()
    if clean_risk == "destructive":
        return "destructive"
    has_outside_access = bool(access and any(str(a).strip() for a in access))
    if clean_risk in ("write", "network", "state_change") or has_outside_access:
        return "state_change"
    return "read_only"


def should_auto_enable_tool(*, mode: str, check_passed: bool, effect: str) -> bool:
    """Return True when a newly authored/updated tool should auto-enable and mount immediately."""
    if not check_passed:
        return False
    norm_mode = normalize_approval_mode(mode) or DEFAULT_APPROVAL_MODE
    if effect == "destructive":
        return False
    if norm_mode == "strict":
        return False
    if norm_mode == "balanced":
        return effect == "read_only"
    if norm_mode == "hands_off":
        return effect in ("read_only", "state_change")
    return False
