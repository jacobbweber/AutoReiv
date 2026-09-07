"""Promote phase: HITL gate — holds until approved, then pack write happens in API (CARD-171)."""

from __future__ import annotations

from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_PROMOTE
from src.domain.orchestration.factory_packets import FactoryPacket


class PromotePhase:
    id = PHASE_PROMOTE
    label = "Promote"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        # Enter waiting_approval; actual pack write is performed by the promote API
        # after human approval (HITL), keeping surfaces working.
        # Check if this job delivers an MCP server [CARD-185]
        is_mcp = getattr(job, "deliverable_type", "") == "mcp"
        if not is_mcp and ctx.repo:
            for p in ctx.repo.list_packets(job.id):
                payload = getattr(p, "payload", None) or {}
                if isinstance(payload, dict):
                    if payload.get("deliverable_type") == "mcp":
                        is_mcp = True
                        break
                    files = payload.get("files_map") or {}
                    if "mcp/server.py" in files:
                        is_mcp = True
                        break

        rebuild_hint = (
            f" If using Docker, rebuild: docker build -t autoreiv-{job.target_agent_id}-mcp:latest packs/{job.target_agent_id}/mcp"
            if is_mcp
            else ""
        )
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="promote",
            sender_role="promote",
            recipient_role="hitl",
            node_id=PHASE_PROMOTE,
            payload={
                "message": (
                    f"Promote gate: waiting for human approval to deploy "
                    f"{job.target_agent_id} to packs/.{rebuild_hint}"
                ),
                "phase": PHASE_PROMOTE,
                "awaiting": "hitl_approval",
                "container_build_cmd": (
                    f"docker build -t autoreiv-{job.target_agent_id}-mcp:latest packs/{job.target_agent_id}/mcp"
                    if is_mcp
                    else None
                ),
            },
        )

        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            waiting=True,
            artifacts={},
        )
