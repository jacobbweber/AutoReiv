"""Author phase: LLM + Wiki grounding (+ synthesizer seed) -> SKILL.md + tool code (CARD-171)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_BLUEPRINT
from src.application.agent_training_factory.wiki_frontmatter import filter_factory_notes
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)


class AuthorPhase:
    id = PHASE_AUTHOR
    label = "Author"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()

        blueprint = _latest_blueprint(ctx)
        tool_spec = (blueprint.get("tools") or [{}])[0] if blueprint else {}
        tool_name = tool_spec.get("name") or f"manage_{clean_slug}"

        seed_files = ToolSynthesizer.synthesize_tool(
            agent_id=job.target_agent_id,
            seed_intent=job.seed_intent,
            objectives=ctx.objectives,
            tool_name=tool_name,
        )
        seed_tool = seed_files.get(f"tools/{tool_name}.py", "")
        seed_skill = seed_files.get(f"skills/{clean_slug}/SKILL.md", "")

        wiki_slice = _wiki_slice(ctx)
        manifest = {}
        if job.environment_manifest_json:
            try:
                manifest = json.loads(job.environment_manifest_json)
            except Exception:
                pass

        llm_data = await phase_llm_json(
            ctx.gateway,
            system=(
                "You are the Author phase of the Agent Training Factory. "
                "Improve the seed tool and SKILL.md using Wiki grounding and the blueprint. "
                "Return ONLY JSON with keys: tool_code (python source), skill_md (markdown), "
                "notes (string). Keep the Python tool importable with a callable named like the tool. "
                "Do not invent third-party product brand names."
            ),
            user=(
                f"Agent: {job.target_agent_id}\n"
                f"Tool name: {tool_name}\n"
                f"Intent: {job.seed_intent}\n"
                f"Manifest: {json.dumps(manifest)[:1500]}\n"
                f"Blueprint: {json.dumps(blueprint)[:1500]}\n"
                f"Wiki:\n{wiki_slice[:2500]}\n\n"
                f"SEED TOOL CODE:\n{seed_tool[:3500]}\n\n"
                f"SEED SKILL.md:\n{seed_skill[:2000]}\n"
            ),
            fallback={"tool_code": seed_tool, "skill_md": seed_skill, "notes": "seed"},
            max_tokens=3500,
            timeout=90.0,
        )

        tool_code = str(llm_data.get("tool_code") or seed_tool)
        skill_md = str(llm_data.get("skill_md") or seed_skill)
        if len(tool_code.strip()) < 40:
            tool_code = seed_tool
        if len(skill_md.strip()) < 40:
            skill_md = seed_skill

        files_map = {
            f"tools/{tool_name}.py": tool_code,
            f"skills/{clean_slug}/SKILL.md": skill_md,
        }
        for k, v in seed_files.items():
            files_map.setdefault(k, v)

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id=PHASE_AUTHOR,
            payload={
                "message": f"Author produced '{tool_name}' and runbook for {job.target_agent_id}.",
                "tool_name": tool_name,
                "authored_files": list(files_map.keys()),
                "files_map": files_map,
                "phase": PHASE_AUTHOR,
                "author_notes": llm_data.get("notes") or "",
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={"files_map": files_map, "tool_name": tool_name},
        )


def _latest_blueprint(ctx: PhaseContext) -> Dict[str, Any]:
    packets = ctx.repo.list_packets(ctx.job_id)
    for p in reversed(packets):
        if p.node_id in (PHASE_BLUEPRINT, "architecture_blueprint") and p.payload:
            bp = p.payload.get("blueprint")
            if bp:
                return bp
            prop = p.payload.get("proposed_tool")
            if prop:
                return {"tools": [prop], "skills": []}
    return {}


def _wiki_slice(ctx: PhaseContext) -> str:
    if ctx.wiki is None:
        return ""
    chunks: List[str] = []
    try:
        notes = ctx.wiki.list_notes(domain="agent-training-factory", topic=ctx.agent_id) or []
        for note in filter_factory_notes(notes, agent_id=ctx.agent_id)[:4]:
            chunks.append(str(note.get("content") or "")[:1200])
    except Exception as exc:
        logger.warning("Author Wiki read failed: %s", exc)
    return "\n".join(chunks)
