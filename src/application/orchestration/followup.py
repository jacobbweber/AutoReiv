"""
propose_followup draft jobs [REQ-ORCH-043].

Creates a proposals row (kind followup_job, status draft) and a queued Job.
Does not start a phase and does not call stream_turn / the orchestrator run loop.

Approve semantics (safer default, CARD-101):
- Approve marks the proposal `approved` and leaves the Job `queued`.
- Approve does not call start_phase or stream_turn. It does not start a second ReAct loop.
- Follow-up jobs use template_id=followup_job so latest_open_job_for_session will not
  pick them up on HITL resume. A later human start (send a new turn that explicitly
  targets the job) is required to run them.
- Reject marks the proposal `rejected` and cancels the job. It never runs.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence

from src.domain.orchestration.errors import InvalidProposalStatusError, JobNotFoundError
from src.domain.orchestration.models import (
    FOLLOWUP_JOB_KIND,
    FOLLOWUP_JOB_TEMPLATE_ID,
    HandoffPacket,
    Job,
    JobStatus,
    PhaseSpec,
    Proposal,
    ProposalKind,
    ProposalStatus,
)

PROPOSE_FOLLOWUP_TOOL = "propose_followup"


def _new_proposal_id() -> str:
    return f"prop_{uuid.uuid4().hex[:12]}"


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _payload_dict(proposal: Proposal) -> Dict[str, Any]:
    raw = proposal.payload_json or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def propose_followup_job(
    store: Any,
    orchestrator: Any,
    *,
    goal: str,
    session_id: str,
    agent_id: str,
    parent_job_id: Optional[str] = None,
    facts: Optional[Any] = None,
    constraints: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Persist a draft follow-up: proposals row + queued Job + HITL pending_approvals.
    Does not start a phase. Does not call kernel/stream_turn.
    """
    goal_text = (goal or "").strip()
    if not goal_text:
        raise ValueError("propose_followup requires a non-empty goal.")

    parent_id = (parent_job_id or "").strip() or None
    if parent_id:
        try:
            store.get_job(parent_id)
        except JobNotFoundError:
            raise
        except Exception as exc:
            raise JobNotFoundError(f"Parent job {parent_id} not found.") from exc

    fact_list = _as_str_list(facts)
    constraint_list = _as_str_list(constraints)

    job: Job = orchestrator.create_job_with_phases(
        goal=goal_text,
        session_id=session_id,
        agent_id=agent_id,
        phase_specs=[
            PhaseSpec(
                name="Follow-up",
                success_rule=goal_text,
                assigned_agent_id=agent_id,
            )
        ],
        template_id=FOLLOWUP_JOB_TEMPLATE_ID,
    )
    phases = store.list_phases_for_job(job.id)
    if phases:
        packet = HandoffPacket(
            goal=goal_text,
            facts=fact_list,
            constraints=constraint_list,
            done_when=goal_text,
            budget={
                "max_turns": phases[0].max_turns,
                "max_handoffs": job.budget_max_handoffs,
                "max_ollama_slots": job.budget_max_ollama_slots,
            },
        )
        phase = phases[0]
        phase.input_packet_json = packet.model_dump_json()
        store.update_phase(phase)

    payload = {
        "goal": goal_text,
        "facts": fact_list,
        "constraints": constraint_list,
        "parent_job_id": parent_id,
        "requested_by_agent_id": agent_id,
        "requested_by_session_id": session_id,
        "job_id": job.id,
    }
    proposal = store.create_proposal(
        Proposal(
            id=_new_proposal_id(),
            kind=ProposalKind.FOLLOWUP_JOB,
            payload_json=json.dumps(payload),
            status=ProposalStatus.DRAFT,
            requested_by_job_id=parent_id,
        )
    )

    approval_id = store.create_approval(
        session_id=session_id,
        agent_id=agent_id,
        tool_name=PROPOSE_FOLLOWUP_TOOL,
        arguments={
            "proposal_id": proposal.id,
            "job_id": job.id,
            "goal": goal_text,
            "parent_job_id": parent_id,
            "facts": fact_list,
            "constraints": constraint_list,
        },
    )

    return {
        "proposal_id": proposal.id,
        "job_id": job.id,
        "approval_id": approval_id,
        "kind": FOLLOWUP_JOB_KIND,
        "status": ProposalStatus.DRAFT.value,
        "job_status": JobStatus.QUEUED.value,
        "goal": goal_text,
        "parent_job_id": parent_id,
        "requested_by_agent_id": agent_id,
        "requested_by_session_id": session_id,
        "auto_run": False,
    }


def apply_followup_decision(
    store: Any,
    orchestrator: Any,
    *,
    proposal_id: Optional[str],
    job_id: Optional[str],
    decision: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approve: proposal approved, job stays queued, no start_phase / stream_turn.
    Reject: proposal rejected, job cancelled, never runs.
    """
    decision_norm = (decision or "").strip().lower()
    if decision_norm in {"approved", "approve"}:
        target_status = ProposalStatus.APPROVED
        cancel = False
    elif decision_norm in {"rejected", "reject"}:
        target_status = ProposalStatus.REJECTED
        cancel = True
    else:
        raise InvalidProposalStatusError(
            f"Invalid follow-up decision {decision!r}. Allowed: approved|rejected."
        )

    proposal = None
    pid = (proposal_id or "").strip() or None
    jid = (job_id or "").strip() or None
    if pid:
        proposal = store.get_proposal(pid)
        payload = _payload_dict(proposal)
        jid = jid or str(payload.get("job_id") or "").strip() or None
    if proposal is None:
        raise InvalidProposalStatusError("Follow-up decision requires proposal_id.")

    if proposal.status != ProposalStatus.DRAFT:
        # Idempotent: already decided.
        return {
            "proposal_id": proposal.id,
            "job_id": jid,
            "status": proposal.status.value,
            "job_status": None,
            "started": False,
            "reason": reason,
        }

    updated = store.update_proposal_status(proposal.id, target_status.value)
    job_status = None
    if cancel and jid:
        cancelled = orchestrator.cancel_job(jid)
        job_status = cancelled.status.value if hasattr(cancelled.status, "value") else str(cancelled.status)
    elif jid:
        job = store.get_job(jid)
        job_status = job.status.value if hasattr(job.status, "value") else str(job.status)

    return {
        "proposal_id": updated.id,
        "job_id": jid,
        "status": updated.status.value,
        "job_status": job_status,
        "started": False,
        "reason": reason,
    }
