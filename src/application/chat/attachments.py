"""
Chat attachment storage, filename sanitization, and lookup helpers [REQ-ATTACH-001, REQ-ATTACH-002, CARD-713].
"""

from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def resolve_attachments_dir(data_dir_paths: Any = None) -> Path:
    """Resolve safe attachment storage directory [REQ-ATTACH-001]."""
    if data_dir_paths and hasattr(data_dir_paths, "root"):
        p = Path(data_dir_paths.root) / "attachments"
    else:
        from src.infrastructure.data.resolver import DataDirResolver

        p = Path(DataDirResolver().resolve().root) / "attachments"
    p.mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(filename: str) -> str:
    """Sanitize attachment filename to prevent directory traversal [REQ-ATTACH-001]."""
    basename = Path(filename).name
    clean = re.sub(r"[^\w\.-]", "_", basename)
    clean = clean.lstrip("._")
    return clean or "attachment.bin"


def save_uploaded_attachment(
    attachments_dir: Path,
    *,
    raw_filename: Optional[str],
    contents: bytes,
    raw_content_type: Optional[str],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist an uploaded chat attachment and return its metadata response dict."""
    raw_name = raw_filename or "attachment.bin"
    safe_name = sanitize_filename(raw_name)
    file_id = uuid.uuid4().hex[:12]

    session_slug = sanitize_filename(session_id) if session_id else "global"
    target_dir = attachments_dir / session_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{file_id}_{safe_name}"
    target_path.write_bytes(contents)

    content_type = raw_content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

    return {
        "id": file_id,
        "filename": safe_name,
        "size_bytes": len(contents),
        "content_type": content_type,
        "url": f"/api/chat/attachments/{file_id}/{safe_name}",
        "path": str(target_path),
    }


def find_attachment_file(
    attachments_dir: Path,
    file_id: str,
    filename: str,
) -> Optional[Tuple[Path, str, str]]:
    """Locate a stored attachment file and return (file_path, content_type, safe_name)."""
    safe_file_id = re.sub(r"[^\w-]", "", file_id)
    safe_name = sanitize_filename(filename)

    matching_files = list(attachments_dir.glob(f"**/{safe_file_id}_{safe_name}"))
    if not matching_files or not matching_files[0].exists():
        return None

    file_path = matching_files[0]
    content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    return file_path, content_type, safe_name


def format_prompt_with_attachments(
    content: Optional[str],
    attachments: Optional[list[Dict[str, Any]]],
    *,
    char_budget: Optional[int] = None,
    direct: bool = False,
    attachments_dir: Any = None,
) -> str:
    """Format user prompt together with uploaded media and file attachments [CARD-143, CARD-479]."""
    from src.application.gateway.attachment_text import MIN_BUDGET_CHARS, build_attachment_prompt

    return build_attachment_prompt(
        content,
        attachments,
        char_budget=char_budget or MIN_BUDGET_CHARS,
        direct=direct,
        attachments_dir=attachments_dir,
    ).text


def format_json_deliverable_to_markdown(text: str) -> str:
    """[REQ-MOB-STREAM-004] Gracefully converts raw structured JSON deliverables into rich Markdown sections."""
    import json

    if not text or not isinstance(text, str):
        return text or ""
    clean = text.strip()
    if not clean.startswith("{") or not clean.endswith("}"):
        return text
    try:
        data = json.loads(clean)
        if not isinstance(data, dict):
            return text
        has_keys = any(
            k in data
            for k in ("goal", "action_plan", "wiki_inventory_summary", "steps", "summary", "status")
        )
        if not has_keys:
            return text

        sections: list[str] = []
        if "goal" in data:
            sections.append(f"## 🎯 Goal: {data['goal']}\n")
        if "status" in data:
            sections.append(f"**Status**: `{data['status']}`\n")
        if "wiki_inventory_summary" in data and isinstance(data["wiki_inventory_summary"], dict):
            sections.append("### 📊 Inventory Summary\n")
            for k, v in data["wiki_inventory_summary"].items():
                label = k.replace("_", " ").title()
                if isinstance(v, list):
                    sections.append(f"- **{label}**:")
                    for item in v:
                        sections.append(f"  - {item}")
                else:
                    sections.append(f"- **{label}**: `{v}`")
            sections.append("")
        if "action_plan" in data and isinstance(data["action_plan"], dict):
            ap = data["action_plan"]
            title = ap.get("title", "Action Plan")
            sections.append(f"### 📋 Action Plan: {title}\n")
            if isinstance(ap.get("steps"), list):
                for idx, s in enumerate(ap["steps"]):
                    num = s.get("step_number", idx + 1)
                    s_title = s.get("title", f"Step {num}")
                    sections.append(f"#### **Step {num}: {s_title}**")
                    if "objective" in s:
                        sections.append(f"- **Objective**: {s['objective']}")
                    if "actions" in s and isinstance(s["actions"], list):
                        sections.append("- **Actions**:")
                        for a in s["actions"]:
                            sections.append(f"  - {a}")
                    if "success_metric" in s:
                        sections.append(f"- **Success Metric**: {s['success_metric']}")
                    sections.append("")
        elif "steps" in data and isinstance(data["steps"], list):
            sections.append("### 📋 Execution Steps\n")
            for idx, s in enumerate(data["steps"]):
                num = s.get("step_number", idx + 1)
                s_title = s.get("title", f"Step {num}")
                sections.append(f"#### **Step {num}: {s_title}**")
                desc = s.get("description") or s.get("objective")
                if desc:
                    sections.append(f"- {desc}")
            sections.append("")

        handled = {"goal", "status", "wiki_inventory_summary", "action_plan", "steps"}
        for k, v in data.items():
            if k in handled:
                continue
            label = k.replace("_", " ").title()
            if isinstance(v, str):
                sections.append(f"### {label}\n\n{v}\n")
            elif isinstance(v, list):
                sections.append(f"### {label}\n")
                for item in v:
                    sections.append(f"- {json.dumps(item) if isinstance(item, dict) else item}")
                sections.append("")
        return "\n".join(sections).strip()
    except Exception:
        return text


def deduplicate_phase_deliverables(
    completed_deliverables: Any,
    final_content: str,
) -> str:
    """Deduplicate multi-phase job deliverables to prevent chat stutter [CARD-409]."""
    clean_final = (final_content or "").strip()
    if not completed_deliverables:
        return clean_final
    if not clean_final:
        return "\n\n---\n\n".join(d.strip() for d in completed_deliverables if d.strip())

    final_words = {w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}", clean_final)}
    unique_priors: list[str] = []
    for prior in completed_deliverables:
        clean_prior = prior.strip()
        if not clean_prior:
            continue
        prior_words = {w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}", clean_prior)}
        if not prior_words:
            continue
        if len(prior_words & final_words) / len(prior_words) >= 0.35:
            continue
        unique_priors.append(clean_prior)

    if unique_priors:
        return "\n\n---\n\n".join(unique_priors) + f"\n\n---\n\n{clean_final}"
    return clean_final
