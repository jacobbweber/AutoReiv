"""
propose_skill / propose_tool / propose_workflow HITL drafts [REQ-BUILD-001 - REQ-BUILD-008].

Creates a proposals row (kind skill|tool|workflow, status draft) and a pending_approvals
park. Does not write SKILL.md, Python under src/, or job-template YAML.
Approve marks approved without UserSkillCatalog.save_pack. Reject marks rejected.
Disk commit of packs is CARD-107 commit_skill_pack.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.domain.agents.profiles import get_builtin_profile
from src.domain.orchestration.errors import InvalidProposalStatusError
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus

PROPOSE_SKILL_TOOL = "propose_skill"
PROPOSE_TOOL_TOOL = "propose_tool"
PROPOSE_WORKFLOW_TOOL = "propose_workflow"
SKILL_PROPOSAL_TOOLS = frozenset(
    {PROPOSE_SKILL_TOOL, PROPOSE_TOOL_TOOL, PROPOSE_WORKFLOW_TOOL}
)

# Same threshold as Forge FORGE_ALLOWLIST_WARN_AT (CARD-078).
ALLOWLIST_WARN_AT = 12
PYTHON_BUILTIN_NOTE = "requires human/code card"


def _new_proposal_id() -> str:
    return f"prop_{uuid.uuid4().hex[:12]}"


def _require_text(name: str, value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{name} is required.")
    return text


def jail_where(where: str, data_dir: Union[str, Path]) -> str:
    """
    Return a $DATA_DIR-relative path jailed under $DATA_DIR/skills.
    Rejects traversal and extra roots. Does not create directories or files.
    """
    raw = _require_text("where", where)
    data_root = Path(data_dir).expanduser().resolve()
    skills_root = (data_root / "skills").resolve()
    normalized = raw.replace("\\", "/")

    data_posix = data_root.as_posix().rstrip("/")
    prefixes = (
        data_posix + "/",
        data_posix,
        "$DATA_DIR/",
        "$DATA_DIR",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix) or normalized.lower().startswith(prefix.lower()):
            normalized = normalized[len(prefix) :].lstrip("/")
            break

    # Drive-absolute (Windows) or POSIX absolute that was not stripped.
    as_path = Path(normalized)
    if as_path.is_absolute():
        candidate = as_path.expanduser()
    else:
        if ".." in Path(normalized).parts:
            raise ValueError("Path traversal rejected.")
        candidate = data_root / normalized

    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise ValueError(str(exc)) from exc

    try:
        resolved.relative_to(skills_root)
    except ValueError as exc:
        raise ValueError("where must be jailed under $DATA_DIR/skills.") from exc

    return resolved.relative_to(data_root).as_posix()


def _pack_id_from_where(rel_where: str, pack_id: Optional[str]) -> Optional[str]:
    explicit = (pack_id or "").strip() or None
    if explicit:
        return explicit
    parts = Path(rel_where).parts
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def _looks_like_python_builtin(where: str, how: str, tool_json: Any) -> bool:
    blob = f"{where}\n{how}\n{json.dumps(tool_json) if tool_json is not None else ''}".lower()
    normalized = blob.replace("\\", "/")
    has_src = "src/" in normalized
    has_py = ".py" in normalized
    has_handler = isinstance(tool_json, dict) and bool(
        tool_json.get("handler") or tool_json.get("module") or tool_json.get("python")
    )
    negated = "not a python builtin" in normalized or "not an executable python" in normalized
    if negated and not (has_src or has_py or has_handler):
        return False
    if has_src or has_py:
        return True
    if "builtinskill" in normalized.replace(" ", ""):
        return True
    if "python module" in normalized:
        return True
    return has_handler


def _allowlist_len(agent_registry: Any, agent_id: str) -> Optional[int]:
    aid = (agent_id or "").strip()
    if not aid:
        return None
    profile = None
    if agent_registry is not None:
        getter = getattr(agent_registry, "get_agent", None) or getattr(
            agent_registry, "get_profile", None
        )
        if callable(getter):
            profile = getter(aid)
    if profile is None:
        profile = get_builtin_profile(aid)
    if profile is None:
        return None
    names = getattr(profile, "allowed_tool_names", None) or []
    return len(list(names))


def sprawl_warning_text(
    *,
    agent_registry: Any = None,
    prefer_existing_agent_id: Optional[str] = None,
    new_agent_id: Optional[str] = None,
    kind: ProposalKind = ProposalKind.SKILL,
    threshold: int = ALLOWLIST_WARN_AT,
) -> Optional[str]:
    """Soft CARD-078 warning. Never blocks the draft."""
    specialist = (prefer_existing_agent_id or "").strip() or None
    new_id = (new_agent_id or "").strip() or None
    extra = 1 if kind == ProposalKind.TOOL else 0

    if specialist:
        count = _allowlist_len(agent_registry, specialist)
        if count is not None:
            projected = count + extra
            if projected >= threshold:
                return (
                    f"Allowlist for specialist '{specialist}' would be {projected} "
                    f"(>= {threshold}). Prefer adding tools/skills on that specialist "
                    "instead of creating a new agent. This is a warning, not a block."
                )
        if new_id:
            return (
                f"Prefer adding tools/skills on existing specialist '{specialist}' "
                f"instead of creating a new agent '{new_id}'. This is a warning, not a block."
            )
        return None

    if new_id:
        return (
            "Prefer adding tools/skills on an existing specialist instead of "
            f"creating a new agent '{new_id}'. This is a warning, not a block."
        )
    return None


def propose_pack_draft(
    store: Any,
    *,
    kind: ProposalKind,
    what: str,
    why: str,
    how: str,
    where: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    pack_id: Optional[str] = None,
    tool_json: Any = None,
    prefer_existing_agent_id: Optional[str] = None,
    new_agent_id: Optional[str] = None,
    requested_by_job_id: Optional[str] = None,
    agent_registry: Any = None,
) -> Dict[str, Any]:
    """
    Persist a skill|tool|workflow draft + HITL park. No disk write. No Job auto-run.
    """
    if store is None:
        raise ValueError("proposal store is unavailable. The draft was not created.")
    if kind not in {ProposalKind.SKILL, ProposalKind.TOOL, ProposalKind.WORKFLOW}:
        raise ValueError(f"Unsupported proposal kind {kind!r}.")

    what_text = _require_text("what", what)
    why_text = _require_text("why", why)
    how_text = _require_text("how", how)
    session = _require_text("session_id", session_id)
    agent = _require_text("agent_id", agent_id)
    jailed = jail_where(where, data_dir)

    parsed_tool: Any = tool_json
    if isinstance(tool_json, str) and tool_json.strip():
        try:
            parsed_tool = json.loads(tool_json)
        except json.JSONDecodeError as exc:
            raise ValueError("tool_json must be a JSON object.") from exc

    if kind == ProposalKind.TOOL:
        if not isinstance(parsed_tool, dict) or not parsed_tool:
            raise ValueError("propose_tool requires tool_json (name, description, parameters).")
        if not str(parsed_tool.get("name") or "").strip():
            raise ValueError("tool_json.name is required.")

    target_pack = _pack_id_from_where(jailed, pack_id)
    python_note = None
    if kind == ProposalKind.TOOL and _looks_like_python_builtin(jailed, how_text, parsed_tool):
        python_note = PYTHON_BUILTIN_NOTE

    warning = sprawl_warning_text(
        agent_registry=agent_registry,
        prefer_existing_agent_id=prefer_existing_agent_id,
        new_agent_id=new_agent_id,
        kind=kind,
    )

    payload: Dict[str, Any] = {
        "what": what_text,
        "why": why_text,
        "how": how_text,
        "where": jailed,
        "kind": kind.value,
        "sprawl_warning": warning,
        "prefer_existing_agent_id": (prefer_existing_agent_id or "").strip() or None,
        "target_pack_id": target_pack,
        "requested_by_agent_id": agent,
        "requested_by_session_id": session,
    }
    if new_agent_id and str(new_agent_id).strip():
        payload["new_agent_id"] = str(new_agent_id).strip()
    if kind == ProposalKind.TOOL:
        payload["tool_json"] = parsed_tool
        payload["apply_note"] = python_note or "draft-only; JSON stub merge is CARD-107"
    if python_note:
        payload["python_builtin_note"] = python_note

    proposal = store.create_proposal(
        Proposal(
            id=_new_proposal_id(),
            kind=kind,
            payload_json=json.dumps(payload),
            status=ProposalStatus.DRAFT,
            requested_by_job_id=(requested_by_job_id or "").strip() or None,
        )
    )

    tool_name = {
        ProposalKind.SKILL: PROPOSE_SKILL_TOOL,
        ProposalKind.TOOL: PROPOSE_TOOL_TOOL,
        ProposalKind.WORKFLOW: PROPOSE_WORKFLOW_TOOL,
    }[kind]

    approval_args: Dict[str, Any] = {
        "proposal_id": proposal.id,
        "kind": kind.value,
        "what": what_text,
        "why": why_text,
        "how": how_text,
        "where": jailed,
        "sprawl_warning": warning,
        "target_pack_id": target_pack,
        "auto_run": False,
    }
    if python_note:
        approval_args["python_builtin_note"] = python_note

    approval_id = store.create_approval(
        session_id=session,
        agent_id=agent,
        tool_name=tool_name,
        arguments=approval_args,
    )

    return {
        "proposal_id": proposal.id,
        "approval_id": approval_id,
        "kind": kind.value,
        "status": ProposalStatus.DRAFT.value,
        "what": what_text,
        "why": why_text,
        "how": how_text,
        "where": jailed,
        "sprawl_warning": warning,
        "target_pack_id": target_pack,
        "requested_by_agent_id": agent,
        "requested_by_session_id": session,
        "auto_run": False,
        "disk_written": False,
        "python_builtin_note": python_note,
        "apply_on_approve": False,
    }


def propose_skill(
    store: Any,
    *,
    what: str,
    why: str,
    how: str,
    where: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    pack_id: Optional[str] = None,
    prefer_existing_agent_id: Optional[str] = None,
    new_agent_id: Optional[str] = None,
    requested_by_job_id: Optional[str] = None,
    agent_registry: Any = None,
) -> Dict[str, Any]:
    return propose_pack_draft(
        store,
        kind=ProposalKind.SKILL,
        what=what,
        why=why,
        how=how,
        where=where,
        data_dir=data_dir,
        session_id=session_id,
        agent_id=agent_id,
        pack_id=pack_id,
        prefer_existing_agent_id=prefer_existing_agent_id,
        new_agent_id=new_agent_id,
        requested_by_job_id=requested_by_job_id,
        agent_registry=agent_registry,
    )


def propose_tool(
    store: Any,
    *,
    what: str,
    why: str,
    how: str,
    where: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    pack_id: str,
    tool_json: Any,
    prefer_existing_agent_id: Optional[str] = None,
    new_agent_id: Optional[str] = None,
    requested_by_job_id: Optional[str] = None,
    agent_registry: Any = None,
) -> Dict[str, Any]:
    return propose_pack_draft(
        store,
        kind=ProposalKind.TOOL,
        what=what,
        why=why,
        how=how,
        where=where,
        data_dir=data_dir,
        session_id=session_id,
        agent_id=agent_id,
        pack_id=pack_id,
        tool_json=tool_json,
        prefer_existing_agent_id=prefer_existing_agent_id,
        new_agent_id=new_agent_id,
        requested_by_job_id=requested_by_job_id,
        agent_registry=agent_registry,
    )


def propose_workflow(
    store: Any,
    *,
    what: str,
    why: str,
    how: str,
    where: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    pack_id: Optional[str] = None,
    prefer_existing_agent_id: Optional[str] = None,
    new_agent_id: Optional[str] = None,
    requested_by_job_id: Optional[str] = None,
    agent_registry: Any = None,
) -> Dict[str, Any]:
    return propose_pack_draft(
        store,
        kind=ProposalKind.WORKFLOW,
        what=what,
        why=why,
        how=how,
        where=where,
        data_dir=data_dir,
        session_id=session_id,
        agent_id=agent_id,
        pack_id=pack_id,
        prefer_existing_agent_id=prefer_existing_agent_id,
        new_agent_id=new_agent_id,
        requested_by_job_id=requested_by_job_id,
        agent_registry=agent_registry,
    )


def apply_skill_proposal_decision(
    store: Any,
    *,
    proposal_id: Optional[str],
    decision: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approve: proposal approved, disk unchanged, no save_pack, no Job auto-run.
    Reject: proposal rejected, disk unchanged.
    Idempotent on already-decided proposals.
    """
    decision_norm = (decision or "").strip().lower()
    if decision_norm in {"approved", "approve"}:
        target_status = ProposalStatus.APPROVED
    elif decision_norm in {"rejected", "reject"}:
        target_status = ProposalStatus.REJECTED
    else:
        raise InvalidProposalStatusError(
            f"Invalid skill/tool/workflow decision {decision!r}. Allowed: approved|rejected."
        )

    pid = (proposal_id or "").strip() or None
    if not pid:
        raise InvalidProposalStatusError("Decision requires proposal_id.")

    proposal = store.get_proposal(pid)
    if proposal.kind not in {ProposalKind.SKILL, ProposalKind.TOOL, ProposalKind.WORKFLOW}:
        raise InvalidProposalStatusError(
            f"Proposal {pid} kind {proposal.kind.value} is not skill|tool|workflow."
        )

    if proposal.status != ProposalStatus.DRAFT:
        return {
            "proposal_id": proposal.id,
            "kind": proposal.kind.value,
            "status": proposal.status.value,
            "disk_written": False,
            "started": False,
            "reason": reason,
        }

    updated = store.update_proposal_status(proposal.id, target_status.value)
    return {
        "proposal_id": updated.id,
        "kind": updated.kind.value,
        "status": updated.status.value,
        "disk_written": False,
        "started": False,
        "reason": reason,
    }
