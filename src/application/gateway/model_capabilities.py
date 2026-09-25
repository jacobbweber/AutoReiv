"""Which models can view images [CARD-475, REQ-475-003].

Resolution order for one model:
1. Operator override from Settings (the per-model "Can view images" checkbox).
2. Runtime learning: the provider rejected an image turn as "not multimodal".
3. Provider metadata saved on Refresh Models (Ollama ``capabilities``; a gateway
   ``description`` that says multimodal/vision/image/omni).
4. The model-name guess.
5. Otherwise text-only.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

OVERRIDES_SETTING = "model_vision_overrides"
METADATA_SETTING = "model_vision_metadata"

_NAME_HINTS = ("vision", "llava", "4o", "-vl", "vl-", "multimodal", "omni")
_DESCRIPTION_RE = re.compile(r"multi-?modal|vision|image|omni|\bvl\b", re.IGNORECASE)
_REJECTION_RE = re.compile(
    r"not a multimodal model|does not support (image|vision|multimodal)|"
    r"image input is not supported|cannot (accept|process) images|no vision support",
    re.IGNORECASE,
)

SettingsGetter = Callable[..., Any]


def looks_like_vision_name(model_id: str) -> bool:
    """Name-only guess, kept from the pre-CARD-475 adapters and widened a little."""
    name = (model_id or "").lower().split("/", 1)[-1]
    return any(h in name for h in _NAME_HINTS)


def description_says_vision(text: Optional[str]) -> bool:
    return bool(text and _DESCRIPTION_RE.search(text))


def is_multimodal_rejection(error: BaseException) -> bool:
    """True when a provider error says the model cannot take images."""
    return bool(_REJECTION_RE.search(str(error) or ""))


def _candidates(model_id: str) -> List[str]:
    clean = (model_id or "").strip()
    out = [clean]
    if "/" in clean:
        out.append(clean.split("/", 1)[1])
    return out


def _lookup(mapping: Dict[str, Any], model_id: str) -> Any:
    """Exact key first, then a provider-prefixed key whose bare name matches."""
    if not isinstance(mapping, dict) or not mapping:
        return None
    for key in _candidates(model_id):
        if key in mapping:
            return mapping[key]
    bare = _candidates(model_id)[-1]
    for key, value in mapping.items():
        if isinstance(key, str) and "/" in key and key.split("/", 1)[1] == bare:
            return value
    return None


class ModelCapabilityResolver:
    """Answers "can this model view images?" from Settings plus runtime learning."""

    def __init__(self, settings_getter: Optional[SettingsGetter] = None):
        self._get = settings_getter
        self._rejected: Set[str] = set()

    def _setting(self, key: str) -> Dict[str, Any]:
        if self._get is None:
            return {}
        try:
            value = self._get(key, None)
        except Exception as e:  # settings store unavailable: fall back to guesses
            logger.debug("model capability settings read failed: %s", e)
            return {}
        return value if isinstance(value, dict) else {}

    def vision_source(self, model_id: str) -> str:
        override = _lookup(self._setting(OVERRIDES_SETTING), model_id)
        if isinstance(override, bool):
            return "override"
        if any(c in self._rejected for c in _candidates(model_id)):
            return "provider_rejected"
        meta = _lookup(self._setting(METADATA_SETTING), model_id)
        if isinstance(meta, dict) and meta.get("vision") is True:
            return "provider"
        if looks_like_vision_name(model_id):
            return "name"
        return "default"

    def can_view_images(self, model_id: str) -> bool:
        source = self.vision_source(model_id)
        if source == "override":
            return bool(_lookup(self._setting(OVERRIDES_SETTING), model_id))
        return source in ("provider", "name")

    def mark_text_only(self, model_id: str) -> None:
        """Remember for this process that the provider refused images for this model."""
        for c in _candidates(model_id):
            if c:
                self._rejected.add(c)


def merge_vision_metadata(existing: Any, models: Iterable[Any]) -> Dict[str, Dict[str, bool]]:
    """Fold discovered ``is_multimodal`` flags into the saved metadata map (True entries only)."""
    merged: Dict[str, Dict[str, bool]] = dict(existing) if isinstance(existing, dict) else {}
    for m in models:
        model_id = getattr(m, "id", None)
        if not model_id:
            continue
        if getattr(m, "is_multimodal", False):
            merged[model_id] = {"vision": True}
        else:
            merged.pop(model_id, None)
    return merged
