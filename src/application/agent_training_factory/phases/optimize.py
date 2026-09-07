"""Optimize phase: merge/split/regroup plan (or no-op) after green Verify (CARD-171)."""

from __future__ import annotations

import json

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_OPTIMIZE
from src.application.orchestration.capability_graph import AgentSplitPolicy, ToolConsolidationGate
from src.domain.orchestration.factory_packets import FactoryPacket


class OptimizePhase:
    id = PHASE_OPTIMIZE
    label = "Optimize"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        packets = ctx.repo.list_packets(job.id)
        files_map = {}
        tool_name = None
        # Prefer latest Author files_map (domain-corrected seed) over stale Verify/Optimize copies.
        for p in reversed(packets):
            if not (p.payload and p.payload.get("files_map")):
                continue
            if (getattr(p, "sender_role", "") == "author") or (getattr(p, "node_id", "") == "author"):
                files_map = dict(p.payload["files_map"])
                tool_name = p.payload.get("tool_name") or tool_name
                break
        if not files_map:
            for p in reversed(packets):
                if p.payload and p.payload.get("files_map"):
                    files_map = dict(p.payload["files_map"])
                    tool_name = p.payload.get("tool_name") or tool_name
                    break

        tools_meta = []
        for path in files_map:
            if path.endswith(".py") and "tools/" in path.replace("\\", "/"):
                name = path.rsplit("/", 1)[-1].replace(".py", "")
                tools_meta.append({"name": name, "target_entity": job.target_agent_id.replace("-", "_"), "verb": "manage", "domain": "default"})

        gate = ToolConsolidationGate().evaluate(tools_meta or [{"name": "x", "target_entity": "y", "verb": "z"}])
        split = AgentSplitPolicy().evaluate_split(job.target_agent_id, tools_meta)

        llm_data = await phase_llm_json(
            ctx.gateway,
            system=(
                "You are the Optimize phase of the Agent Training Factory. "
                "Review the authored pack and verification history. "
                "Return ONLY JSON with keys: action (noop|merge|split|regroup), plan (string), changes (list)."
            ),
            user=(
                f"Agent: {job.target_agent_id}\n"
                f"Tools: {json.dumps(tools_meta)}\n"
                f"Consolidation: {json.dumps(gate)}\n"
                f"Split policy: {json.dumps(split)}\n"
                "Prefer noop unless clear bloat or sprawl."
            ),
            fallback={"action": "noop", "plan": "No structural changes required.", "changes": []},
        )

        action = str(llm_data.get("action") or "noop")
        plan = str(llm_data.get("plan") or "No-op")

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="promote",
            sender_role="optimize",
            recipient_role="promote",
            node_id=PHASE_OPTIMIZE,
            payload={
                "message": f"Optimize complete ({action}): {plan}",
                "optimize_action": action,
                "optimize_plan": plan,
                "changes": llm_data.get("changes") or [],
                "tool_name": tool_name,
                "files_map": files_map,
                "critic_verdict": "approved",
                "phase": PHASE_OPTIMIZE,
            },
        )
        ctx.repo.save_packet(packet)

        # Notify AutoReiv session that certification is ready for HITL
        _notify_autoreiv(ctx, job)

        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={"action": action, "files_map": files_map, "tool_name": tool_name},
        )


def _notify_autoreiv(ctx: PhaseContext, job) -> None:
    if not ctx.store:
        return
    from src.domain.gateway.models import ChatMessage, Role

    session_id = job.session_id
    session = ctx.store.get_session(session_id)
    if not session:
        autoreiv_sessions = ctx.store.list_sessions(agent_id="autoreiv")
        if autoreiv_sessions:
            session_id = autoreiv_sessions[0].id
        else:
            new_sess = ctx.store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
            session_id = new_sess.id
        job.session_id = session_id
        ctx.repo.save_job(job)

    clean_name = job.target_agent_id.replace("-", " ").title()
    msg_text = (
        f"**Agent Training Factory — Certification Complete**\n\n"
        f"Training for agent **{clean_name}** (`{job.target_agent_id}`) has passed Verify "
        f"and Optimize. Ready for Promote (HITL deploy).\n\n"
        f"**Action Required**: Review and approve deployment to activate `{job.target_agent_id}`."
    )
    try:
        ctx.store.save_message(
            session_id=session_id,
            agent_id="autoreiv",
            message=ChatMessage(role=Role.ASSISTANT, content=msg_text),
        )
    except Exception:
        pass
