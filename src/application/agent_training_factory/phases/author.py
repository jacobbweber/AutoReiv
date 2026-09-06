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

_STUB_PATTERNS = (
    "agent for managing",
    "managing tasks",
)


class AuthorPhase:
    id = PHASE_AUTHOR
    label = "Author"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        objectives = list(ctx.objectives)

        blueprint = _latest_blueprint(ctx)
        tool_spec = (blueprint.get("tools") or [{}])[0] if blueprint else {}
        tool_name = tool_spec.get("name") or f"manage_{clean_slug}"

        seed_files = ToolSynthesizer.synthesize_tool(
            agent_id=job.target_agent_id,
            seed_intent=job.seed_intent,
            objectives=objectives,
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
                "SKILL.md MUST include Purpose and Objectives sections that quote the seed brief. "
                "When the brief mentions unattend/ISO/template/VHDX, encode those concerns in the skill and tool. "
                "Do not invent third-party product brand names. "
                "Never return a one-line stub like 'Agent for managing ... tasks'."
            ),
            user=(
                f"Agent: {job.target_agent_id}\n"
                f"Tool name: {tool_name}\n"
                f"Intent: {job.seed_intent}\n"
                f"Objectives: {json.dumps(objectives)}\n"
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

        # Quality gate: reject costume stubs; force richer synthesizer path.
        if _is_stub_skill(skill_md, job.seed_intent, objectives):
            logger.warning("Author skill failed quality gate; restoring enriched synthesizer seed")
            skill_md = seed_skill
            skill_md = _enrich_skill_with_brief(skill_md, job.seed_intent, objectives, job.target_agent_id)
            if not _tool_covers_intent(tool_code, job.seed_intent):
                tool_code = seed_tool
                # Prefer synthesizer files wholesale when LLM ignored the brief
                for k, v in seed_files.items():
                    if k.endswith(".py") and k.endswith(f"{tool_name}.py"):
                        tool_code = v
        else:
            skill_md = _enrich_skill_with_brief(skill_md, job.seed_intent, objectives, job.target_agent_id)
            if not _tool_covers_intent(tool_code, job.seed_intent):
                tool_code = seed_tool or tool_code

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


def _is_stub_skill(skill_md: str, seed_intent: str, objectives: list) -> bool:
    """True when skill is a shallow costume stub that ignores the brief."""
    body = (skill_md or "").strip()
    low = body.lower()
    if len(body) < 120:
        return True
    if any(p in low for p in _STUB_PATTERNS):
        brief_ok = (seed_intent[:40].lower() in low) or (seed_intent[:24].lower() in low)
        if "## purpose" not in low or not brief_ok:
            return True
    if "## purpose" not in low:
        return True
    if "objective" not in low:
        return True
    required = [
        k
        for k in ("unattend", "autounattend", "iso", "vhdx", "template")
        if k in (seed_intent or "").lower()
    ]
    if required and not any(k in low for k in required):
        return True
    return False


def _enrich_skill_with_brief(skill_md: str, seed_intent: str, objectives: list, agent_id: str) -> str:
    """Ensure Purpose + Objectives quote the seed brief."""
    objs = objectives or ([seed_intent] if seed_intent else [])
    obj_lines = "\n".join(f"- {o}" for o in objs)
    purpose_block = f"## Purpose\n{seed_intent}\n\n## Objectives\n{obj_lines}\n"
    body = (skill_md or "").strip()
    if not body:
        return (
            f"---\nname: {agent_id} Automation\ndescription: {(seed_intent or '')[:120]}\n---\n\n"
            f"# {agent_id} Runbook\n\n{purpose_block}\n## Available Actions\n- status\n- list\n- create\n"
        )
    low = body.lower()
    if "## purpose" not in low:
        if body.startswith("---"):
            parts = body.split("---", 2)
            if len(parts) >= 3:
                return f"---{parts[1]}---\n\n{purpose_block}\n{parts[2].lstrip()}"
        return purpose_block + "\n" + body
    if "objective" not in low:
        return body + f"\n\n## Objectives\n{obj_lines}\n"
    required = [
        k
        for k in ("unattend", "autounattend", "iso", "vhdx", "template")
        if k in (seed_intent or "").lower()
    ]
    if required and not any(k in low for k in required):
        return body + f"\n\n## Seed Brief\n{seed_intent}\n\n## Objectives\n{obj_lines}\n"
    return body


def _tool_covers_intent(tool_code: str, seed_intent: str) -> bool:
    low = (tool_code or "").lower()
    intent_low = (seed_intent or "").lower()
    keys = [k for k in ("unattend", "autounattend", "iso", "vhdx", "template") if k in intent_low]
    if "hyperv" in intent_low or "hyper-v" in intent_low:
        keys.extend(["hyper-v", "new-vm", "get-vm", "powershell"])
    if not keys:
        return True
    return any(k in low for k in keys)


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
