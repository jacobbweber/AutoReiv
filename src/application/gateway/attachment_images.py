"""Current-turn image attachments for LLM requests [CARD-475].

Chat writes an image attachment into the user message as text
(``*(Attached Image: `name`, ..., Local Path: `path`)*``, CARD-143). Before
CARD-475 both adapters re-read every such path in the whole history and sent
the bytes on every turn, to every model. Now the gateway decides, per request:

* only the latest user message may carry images (earlier ones stay as text);
* only a vision-capable model gets the bytes;
* a text-only model gets a short note instead, and the user gets a notice.
"""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import List, Optional, Tuple

from src.domain.gateway.models import ChatMessage, Role

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
NOTICE_EVENT = "attachment_notice"

_NAMED_RE = re.compile(r"Attached Image:\s*`([^`]+)`[^\n]*?Local Path:\s*`([^`]+)`")
_PATH_RE = re.compile(r"Local Path:\s*[`\"]?([^`\"\r\n\)]+)[`\"]?")


def current_turn_images(content: str) -> List[dict]:
    """Image attachments named in one user message that still exist on disk."""
    if not content or "Local Path:" not in content:
        return []
    found: List[Tuple[str, str]] = [(n.strip(), p.strip()) for n, p in _NAMED_RE.findall(content)]
    named_paths = {p for _, p in found}
    for p in _PATH_RE.findall(content):
        p = p.strip()
        if p not in named_paths:
            found.append((Path(p).name, p))
    images: List[dict] = []
    for name, raw in found:
        try:
            path = Path(raw)
            if path.suffix.lower() not in IMAGE_SUFFIXES or not path.is_file():
                continue
            if path.stat().st_size > MAX_IMAGE_BYTES:
                continue
        except (OSError, ValueError):
            continue
        media_type = mimetypes.guess_type(path.name)[0] or "image/png"
        images.append({"path": str(path), "media_type": media_type, "filename": name})
    return images


def image_notice_text(names: List[str]) -> str:
    """User-facing notice, Jacob's D6 wording."""
    label = "file name" if len(names) == 1 else "file names"
    shown = ", ".join(f"`{n}`" for n in names)
    return (
        f"This model can't view images, so it only saw the {label} {shown}. "
        "Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures."
    )


def _model_note(names: List[str]) -> str:
    shown = ", ".join(f"`{n}`" for n in names)
    return (
        f"\n\n[Attachment note: the user attached image {shown}, but this model cannot view images. "
        "Tell the user you could not see the picture and answer from the text only.]"
    )


def prepare_image_turn(
    messages: List[ChatMessage], *, can_view_images: bool
) -> Tuple[List[ChatMessage], Optional[List[str]], bool]:
    """Return (messages, dropped_image_names, images_attached).

    Every message loses ``images`` except the latest user message, which gets the
    current turn's images when the model can view them, or a note when it cannot.
    """
    last_user = next((i for i in range(len(messages) - 1, -1, -1) if messages[i].role == Role.USER), None)
    out: List[ChatMessage] = []
    dropped: Optional[List[str]] = None
    attached = False
    for i, m in enumerate(messages):
        if i != last_user:
            out.append(m.model_copy(update={"images": None}) if m.images else m)
            continue
        images = current_turn_images(m.content or "")
        if not images:
            out.append(m.model_copy(update={"images": None}) if m.images else m)
        elif can_view_images:
            out.append(m.model_copy(update={"images": images}))
            attached = True
        else:
            dropped = [img["filename"] for img in images]
            out.append(m.model_copy(update={"images": None, "content": (m.content or "") + _model_note(dropped)}))
    return out, dropped, attached


def notice_payload(names: List[str]) -> dict:
    return {"type": NOTICE_EVENT, "message": image_notice_text(names), "files": list(names)}
