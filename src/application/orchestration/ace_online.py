"""
Online ACE playbook deltas (CARD-110) [REQ-IMPROVE-001 - REQ-IMPROVE-006] [REQ-IMPROVE-016].

Generator is existing AgentKernel. Reflector + Curator are in-process functions.
Not a second builder, ReAct loop, LangGraph graph, or ACE GitHub vendor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.orchestration.skill_proposals import (
    PYTHON_BUILTIN_NOTE,
    _looks_like_python_builtin,
    propose_skill,
    propose_tool,
)
from src.application.skills.user_catalog import UserSkillCatalog

# Generator role is the existing kernel; do not instantiate a second one here.
GENERATOR_ROLE = "AgentKernel"
MAX_INSIGHT_CHARS = 400
ONLINE_SOURCE = "online-ace"


def _catalog_for(data_dir: Union[str, Path], catalog: Any = None) -> UserSkillCatalog:
    if catalog is not None:
        return catalog
    return UserSkillCatalog(skills_dir=Path(data_dir) / "skills")


def reflect_failed_turn(
    *,
    pack_id: str,
    error_message: Optional[str] = None,
    tool_errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """Cheap Reflector: one tiny insight from trajectory errors. No LLM, no full playbook."""
    errors = list(tool_errors or [])
    tool_bits = []
    for item in errors:
        name = str(item.get("tool_name") or "tool").strip() or "tool"
        err = str(item.get("error") or "failed").strip() or "failed"
        tool_bits.append(f"{name}: {err}")
    evidence_parts = [p for p in [error_message, "; ".join(tool_bits)] if p]
    evidence = " | ".join(evidence_parts) if evidence_parts else "turn failed"
    evidence = evidence.replace("\r\n", "\n").strip()
    if len(evidence) > MAX_INSIGHT_CHARS:
        evidence = evidence[: MAX_INSIGHT_CHARS - 1].rstrip() + "…"

    if tool_bits:
        insight = (
            f"Tool error in pack '{pack_id}': {tool_bits[0]}. "
            "Record the failure mode in the SOP; do not treat stubs as live APIs."
        )
    elif error_message:
        insight = f"Failed turn for pack '{pack_id}': {error_message.strip()}"
    else:
        insight = f"Failed turn for pack '{pack_id}'; capture the miss as one SOP bullet."
    insight = insight.replace("\r\n", " ").strip()
    if len(insight) > MAX_INSIGHT_CHARS:
        insight = insight[: MAX_INSIGHT_CHARS - 1].rstrip() + "…"
    return {"insight": insight, "evidence": evidence, "pack_id": pack_id}


def _python_shaped(insight: str, evidence: str, tool_errors: List[Dict[str, Any]]) -> bool:
    blob_how = f"{insight}\n{evidence}"
    if _looks_like_python_builtin("skills/x/SKILL.md", blob_how, None):
        return True
    for item in tool_errors:
        err = str(item.get("error") or "")
        if _looks_like_python_builtin(err, err, item):
            return True
    lowered = f"{insight} {evidence}".lower()
    return "src/" in lowered.replace("\\", "/") and ".py" in lowered


def record_sidecar_note(
    *,
    pack_id: str,
    data_dir: Union[str, Path],
    insight: str,
    evidence: Optional[str] = None,
    session_id: Optional[str] = None,
    turn_span_id: Optional[str] = None,
    catalog: Any = None,
) -> Dict[str, Any]:
    """Append-only PLAYBOOK_NOTES sidecar. Does not modify SKILL.md [REQ-IMPROVE-006]."""
    cat = _catalog_for(data_dir, catalog)
    return cat.append_playbook_note(
        pack_id,
        insight=insight,
        evidence=evidence,
        session_id=session_id,
        turn_span_id=turn_span_id,
        source=ONLINE_SOURCE,
    )


def propose_notes_into_skill(
    store: Any,
    *,
    pack_id: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    catalog: Any = None,
    agent_registry: Any = None,
) -> Dict[str, Any]:
    """Promotion of sidecar notes into SKILL.md is still propose_skill HITL [REQ-IMPROVE-005]."""
    cat = _catalog_for(data_dir, catalog)
    notes_path = cat.pack_dir(pack_id) / "PLAYBOOK_NOTES.md"
    body = ""
    if notes_path.is_file():
        body = notes_path.read_text(encoding="utf-8")
    how = (
        "Patch SKILL.md SOP with the sidecar bullets below; no Python. "
        "Do not rewrite the whole playbook.\n\n"
        + (body.strip() or "(no sidecar notes yet)")
    )
    snap = cat.snapshot_pack(pack_id)
    if not snap.get("success"):
        return {
            "success": False,
            "error": snap.get("error") or "Snapshot failed; proposal was not created.",
            "disk_written": False,
            "status": None,
            "nightly_enqueued": False,
        }
    result = propose_skill(
        store,
        what=f"Promote ACE sidecar notes into {pack_id} SOP",
        why="Sidecar breadcrumbs should become a durable playbook bullet after HITL.",
        how=how,
        where=f"skills/{pack_id}/SKILL.md",
        data_dir=data_dir,
        session_id=session_id,
        agent_id=agent_id,
        pack_id=pack_id,
        agent_registry=agent_registry,
        extra_payload={
            "ace_delta": True,
            "snapshot_id": snap.get("snapshot_id"),
            "source": ONLINE_SOURCE,
            "sidecar_promotion": True,
        },
    )
    result["nightly_enqueued"] = False
    result["skill_md_written"] = False
    return result


def record_failed_turn_delta(
    store: Any,
    *,
    pack_id: str,
    data_dir: Union[str, Path],
    session_id: str,
    agent_id: str,
    insight: Optional[str] = None,
    error_message: Optional[str] = None,
    tool_errors: Optional[List[Dict[str, Any]]] = None,
    turn_span_id: Optional[str] = None,
    catalog: Any = None,
    agent_registry: Any = None,
    mode: str = "propose_skill",
) -> Dict[str, Any]:
    """
    Curator for one failed turn: snapshot, then either HITL propose_skill or sidecar append.

    Never writes SKILL.md live. Never writes src/. Does not enqueue nightly [REQ-IMPROVE-016].
    """
    errors = list(tool_errors or [])
    reflected = reflect_failed_turn(pack_id=pack_id, error_message=error_message, tool_errors=errors)
    note = (insight or reflected["insight"]).strip()
    evidence = reflected["evidence"]
    cat = _catalog_for(data_dir, catalog)

    snap = cat.snapshot_pack(pack_id)
    if not snap.get("success"):
        return {
            "success": False,
            "error": snap.get("error") or "Snapshot failed; delta was not applied.",
            "disk_written": False,
            "src_written": False,
            "skill_md_written": False,
            "status": None,
            "deltas": 0,
            "nightly_enqueued": False,
        }

    mode_norm = (mode or "propose_skill").strip().lower()
    if mode_norm in {"sidecar", "notes", "playbook_notes"}:
        appended = cat.append_playbook_note(
            pack_id,
            insight=note,
            evidence=evidence,
            session_id=session_id,
            turn_span_id=turn_span_id,
            source=ONLINE_SOURCE,
            snapshot_first=False,
        )
        skill_path = cat.resolve_skill_md(pack_id)
        skill_after = skill_path.read_bytes() if skill_path.is_file() else b""
        return {
            "success": bool(appended.get("success")),
            "mode": "sidecar",
            "pack_id": pack_id,
            "insight": note,
            "snapshot_id": snap.get("snapshot_id"),
            "disk_written": bool(appended.get("success")),
            "src_written": False,
            "skill_md_written": False,
            "skill_md_bytes": len(skill_after),
            "deltas": 1 if appended.get("success") else 0,
            "nightly_enqueued": False,
            "error": appended.get("error"),
        }

    where = f"skills/{pack_id}/SKILL.md"
    extra = {
        "ace_delta": True,
        "snapshot_id": snap.get("snapshot_id"),
        "source": ONLINE_SOURCE,
        "turn_span_id": turn_span_id,
        "evidence": evidence,
    }

    if _python_shaped(note, evidence, errors):
        tool_name = str((errors[0] or {}).get("tool_name") or "python_delta") if errors else "python_delta"
        drafted = propose_tool(
            store,
            what=f"Python-shaped ACE delta for {pack_id} stays draft-only",
            why=note,
            how=(
                f"{PYTHON_BUILTIN_NOTE}. Do not write a Python BuiltinSkill module under src/. "
                f"Evidence: {evidence}"
            ),
            where=where,
            data_dir=data_dir,
            session_id=session_id,
            agent_id=agent_id,
            pack_id=pack_id,
            tool_json={
                "name": tool_name,
                "description": note,
                "parameters": {"type": "object", "properties": {}},
                "handler": "src.application.skills.forbidden_live_codegen.handler",
            },
            agent_registry=agent_registry,
            extra_payload=extra,
        )
        drafted["mode"] = "propose_tool"
        drafted["python_shaped"] = True
    else:
        drafted = propose_skill(
            store,
            what=f"Append ACE insight to {pack_id} SOP",
            why=note,
            how=f"Patch SKILL.md SOP with one bullet; no Python.\n\n- {note}",
            where=where,
            data_dir=data_dir,
            session_id=session_id,
            agent_id=agent_id,
            pack_id=pack_id,
            agent_registry=agent_registry,
            extra_payload=extra,
        )
        drafted["mode"] = "propose_skill"
        drafted["python_shaped"] = False

    skill_path = cat.resolve_skill_md(pack_id)
    drafted["success"] = drafted.get("status") == "draft"
    drafted["src_written"] = False
    drafted["skill_md_written"] = False
    drafted["skill_md_exists"] = skill_path.is_file()
    drafted["deltas"] = 1
    drafted["nightly_enqueued"] = False
    drafted["snapshot_id"] = snap.get("snapshot_id")
    drafted["insight"] = note
    drafted["pack_id"] = pack_id
    return drafted
