"""Blueprint phase: Wiki notes + pack inventory → skill list + tools-per-skill (CARD-171)."""

from __future__ import annotations

import json
import logging
from typing import List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_BLUEPRINT
from src.application.agent_training_factory.wiki_frontmatter import filter_factory_notes
from src.application.orchestration.capability_graph import ToolConsolidationGate
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)


class BlueprintPhase:
    id = PHASE_BLUEPRINT
    label = "Blueprint"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()

        wiki_slice = _read_grounding(ctx)
        manifest = {}
        if job.environment_manifest_json:
            try:
                manifest = json.loads(job.environment_manifest_json)
            except Exception:
                manifest = {}

        fallback_skills = [
            {
                "id": clean_slug,
                "name": f"{job.target_agent_id.replace('-', ' ').title()} Skill",
                "description": job.seed_intent[:200],
                "tools": [f"manage_{clean_slug}"],
            }
        ]
        fallback_tools = [
            {
                "name": f"manage_{clean_slug}",
                "target_entity": clean_slug,
                "actions": ["status", "start", "stop", "restart", "list"],
                "description": f"Dispatcher tool to manage {job.target_agent_id}.",
            }
        ]

        llm_data = await phase_llm_json(
            ctx.gateway,
            system=(
                "You are the Blueprint phase of the Agent Training Factory. "
                "Using Wiki grounding notes and the environment manifest, design a non-overlapping "
                "skill list and tools-per-skill plan. Return ONLY JSON with keys: "
                "skills (list of {id,name,description,tools}), "
                "tools (list of {name,target_entity,actions,description}), "
                "rationale (string)."
            ),
            user=(
                f"Agent: {job.target_agent_id}\n"
                f"Intent: {job.seed_intent}\n"
                f"Objectives: {json.dumps(ctx.objectives)}\n"
                f"Manifest: {json.dumps(manifest)[:2000]}\n"
                f"Wiki grounding excerpts:\n{wiki_slice[:3000]}\n"
                "Avoid overlapping tools. Prefer one consolidated dispatcher per entity."
            ),
            fallback={"skills": fallback_skills, "tools": fallback_tools, "rationale": "heuristic"},
        )

        tools = list(llm_data.get("tools") or fallback_tools)
        skills = list(llm_data.get("skills") or fallback_skills)

        gate = ToolConsolidationGate()
        consolidation = gate.evaluate(
            [
                {
                    "name": t.get("name", ""),
                    "target_entity": t.get("target_entity") or clean_slug,
                    "verb": (t.get("actions") or ["manage"])[0]
                    if isinstance(t.get("actions"), list)
                    else "manage",
                }
                for t in tools
            ]
        )
        if consolidation.get("should_consolidate"):
            tools = [
                {
                    "name": consolidation.get("suggested_tool_name") or f"manage_{clean_slug}",
                    "target_entity": consolidation.get("target_entity") or clean_slug,
                    "actions": consolidation.get("actions") or ["status", "list"],
                    "description": consolidation.get("reason")
                    or f"Consolidated dispatcher for {job.target_agent_id}",
                }
            ]
            if skills:
                skills[0]["tools"] = [tools[0]["name"]]

        blueprint = {
            "skills": skills,
            "tools": tools,
            "rationale": llm_data.get("rationale") or "",
            "wiki_excerpt_chars": len(wiki_slice),
        }

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id=PHASE_BLUEPRINT,
            payload={
                "message": (
                    f"Blueprint formulated: {len(skills)} skill(s), {len(tools)} tool(s) "
                    f"for {job.target_agent_id}."
                ),
                "blueprint": blueprint,
                "proposed_tool": tools[0] if tools else {},
                "phase": PHASE_BLUEPRINT,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={"blueprint": blueprint},
        )


def _read_grounding(ctx: PhaseContext) -> str:
    if ctx.wiki is None:
        return ""
    chunks: List[str] = []
    try:
        notes = ctx.wiki.list_notes(domain="agent-training-factory", topic=ctx.agent_id) or []
        factory_notes = filter_factory_notes(notes, agent_id=ctx.agent_id, factory_job_id=ctx.job_id)
        if not factory_notes:
            factory_notes = filter_factory_notes(notes, agent_id=ctx.agent_id)
        for note in factory_notes[:6]:
            body = note.get("content") or note.get("body") or ""
            title = note.get("title") or ""
            chunks.append(f"## {title}\n{body[:1500]}")
        if not chunks:
            # Fallback: search
            hits = ctx.wiki.search(ctx.agent_id, limit=5) or []
            for h in hits:
                chunks.append(str(h.get("content") or h.get("snippet") or h)[:800])
    except Exception as exc:
        logger.warning("Blueprint Wiki read failed: %s", exc)
    return "\n\n".join(chunks)
