"""Author phase: LLM + Wiki grounding (+ synthesizer seed) -> SKILL.md + tool code (CARD-171)."""

from __future__ import annotations

import ast
import json
import logging
from typing import Any, Dict, List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_BLUEPRINT, PHASE_VERIFY
from src.application.agent_training_factory.wiki_frontmatter import filter_factory_notes
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)

_STUB_PATTERNS = (
    "agent for managing",
    "managing tasks",
)



def _latest_verify_failure_notes(ctx: PhaseContext) -> str:
    """Surface the last Verify critic_notes so Author can adapt (not blind retry)."""
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return ""
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        node = getattr(p, "node_id", "") or ""
        payload = getattr(p, "payload", None) or {}
        if role not in ("verify", "sandbox_runner") and node not in (PHASE_VERIFY, "sandbox_battery_node"):
            continue
        if payload.get("passed") is True:
            continue
        notes = str(payload.get("critic_notes") or "").strip()
        if notes:
            return notes
        msg = str(payload.get("message") or "").strip()
        if msg:
            return msg
    return ""


class AuthorPhase:
    id = PHASE_AUTHOR
    label = "Author"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        objectives = list(ctx.objectives)

        blueprint = _latest_blueprint(ctx)
        tool_specs = list((blueprint or {}).get("tools") or [])
        skill_specs = list((blueprint or {}).get("skills") or [])
        if not tool_specs:
            tool_specs = [{"name": f"manage_{clean_slug}", "skill_id": clean_slug}]
        if not skill_specs:
            skill_specs = [
                {
                    "id": clean_slug,
                    "name": f"{job.target_agent_id} Skill",
                    "tools": [tool_specs[0].get("name") or f"manage_{clean_slug}"],
                }
            ]

        # Map tool -> skill_id from blueprint
        tool_to_skill: Dict[str, str] = {}
        for sk in skill_specs:
            sid = sk.get("id") or clean_slug
            for tn in sk.get("tools") or []:
                tool_to_skill[str(tn)] = str(sid)
        for t in tool_specs:
            tn = str(t.get("name") or "")
            if tn and tn not in tool_to_skill:
                tool_to_skill[tn] = str(t.get("skill_id") or clean_slug)

        wiki_slice = _wiki_slice(ctx)
        manifest = {}
        if job.environment_manifest_json:
            try:
                manifest = json.loads(job.environment_manifest_json)
            except Exception:
                pass

        last_fail = _latest_verify_failure_notes(ctx)
        fail_block = (
            f"LAST VERIFY FAILURE (adapt - do not blind-retry the same mistake):\n{last_fail[:2000]}\n\n"
            if last_fail
            else ""
        )

        files_map: Dict[str, str] = {}
        authored_tool_names: List[str] = []
        author_notes: List[str] = []

        # Fast path: Hyper-V multi-skill blueprints already have durable synthesizer seeds.
        # Skipping per-tool LLM avoids 4x90s hangs and docstring escape regressions (CARD-171).
        use_seed_only = len(tool_specs) >= 3 and any(
            str(t.get("name") or "").startswith("manage_hyperv_") for t in tool_specs
        )

        # Author every blueprint tool/skill (multi-skill packs must not collapse to tools[0]).
        for tool_spec in tool_specs:
            tool_name = tool_spec.get("name") or f"manage_{clean_slug}"
            skill_id = tool_to_skill.get(tool_name) or tool_spec.get("skill_id") or clean_slug
            focus_objectives = list(tool_spec.get("actions") or []) + list(objectives)
            seed_files = ToolSynthesizer.synthesize_tool(
                agent_id=job.target_agent_id,
                seed_intent=job.seed_intent,
                objectives=focus_objectives or objectives,
                tool_name=tool_name,
                skill_id=skill_id,
            )
            seed_tool = seed_files.get(f"tools/{tool_name}.py", "")
            seed_skill = (
                seed_files.get(f"skills/{skill_id}/SKILL.md")
                or seed_files.get(f"skills/{clean_slug}/SKILL.md")
                or ""
            )

            if use_seed_only:
                llm_data = {"tool_code": seed_tool, "skill_md": seed_skill, "notes": "seed-only-multi-skill"}
            else:
                llm_data = await phase_llm_json(
                    ctx.gateway,
                    system=(
                        "You are the Author phase of the Agent Training Factory. "
                        "Improve the seed tool and SKILL.md using Wiki grounding and the blueprint. "
                        "Return ONLY JSON with keys: tool_code (python source), skill_md (markdown), "
                        "notes (string). Keep the Python tool importable with a callable named like the tool. "
                        "SKILL.md MUST include Purpose and Objectives sections that quote the seed brief. "
                        "When the brief mentions unattend/ISO/template/VHDX, encode those concerns in the skill and tool. "
                        "Tools must call real Hyper-V\\ cmdlets for Hyper-V work — never Windows Get-Service bleed. "
                        "Do not invent third-party product brand names. "
                        "Never return a one-line stub like 'Agent for managing ... tasks'. "
                        "If LAST VERIFY FAILURE notes are present, fix that failure explicitly."
                    ),
                    user=(
                        f"Agent: {job.target_agent_id}\n"
                        f"Tool name: {tool_name}\n"
                        f"Skill id: {skill_id}\n"
                        f"Intent: {job.seed_intent}\n"
                        f"Objectives: {json.dumps(objectives)}\n"
                        f"Manifest: {json.dumps(manifest)[:1500]}\n"
                        f"Blueprint tool: {json.dumps(tool_spec)[:800]}\n"
                        f"Wiki:\n{wiki_slice[:2000]}\n\n"
                        f"{fail_block}"
                        f"SEED TOOL CODE:\n{seed_tool[:3000]}\n\n"
                        f"SEED SKILL.md:\n{seed_skill[:1600]}\n"
                    ),
                    fallback={"tool_code": seed_tool, "skill_md": seed_skill, "notes": "seed"},
                    max_tokens=3500,
                    timeout=90.0,
                )

            tool_code = str(llm_data.get("tool_code") or seed_tool)
            skill_md = str(llm_data.get("skill_md") or seed_skill)
            # Reject non-importable LLM tool code (e.g. docstring Windows path escapes).
            try:
                ast.parse(tool_code)
            except SyntaxError as syn_exc:
                logger.warning("Author LLM tool_code SyntaxError for %s: %s; using seed", tool_name, syn_exc)
                tool_code = seed_tool or tool_code
            if len(tool_code.strip()) < 40:
                tool_code = seed_tool
            if len(skill_md.strip()) < 40:
                skill_md = seed_skill

            domain_bleed = _tool_mismatches_domain(
                tool_code, job.seed_intent, objectives, job.target_agent_id
            ) or _skill_mismatches_domain(skill_md, job.seed_intent, objectives, job.target_agent_id)
            if _is_stub_skill(skill_md, job.seed_intent, objectives) or domain_bleed:
                if domain_bleed:
                    logger.warning("Author output mismatched domain for %s; restoring seed", tool_name)
                else:
                    logger.warning("Author skill failed quality gate for %s; restoring seed", tool_name)
                skill_md = _enrich_skill_with_brief(
                    seed_skill or skill_md, job.seed_intent, objectives, job.target_agent_id
                )
                tool_code = seed_tool or tool_code
            else:
                skill_md = _enrich_skill_with_brief(
                    skill_md, job.seed_intent, objectives, job.target_agent_id
                )
                if not _tool_covers_intent(tool_code, job.seed_intent):
                    tool_code = seed_tool or tool_code

            files_map[f"tools/{tool_name}.py"] = tool_code
            # Keep companion .ps1 from synthesizer when present
            ps1_key = f"tools/{tool_name}.ps1"
            if ps1_key in seed_files:
                files_map.setdefault(ps1_key, seed_files[ps1_key])
            files_map[f"skills/{skill_id}/SKILL.md"] = skill_md
            for k, v in seed_files.items():
                files_map.setdefault(k, v)
            authored_tool_names.append(tool_name)
            if llm_data.get("notes"):
                author_notes.append(str(llm_data.get("notes")))

        primary_tool = authored_tool_names[0] if authored_tool_names else f"manage_{clean_slug}"
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id=PHASE_AUTHOR,
            payload={
                "message": (
                    f"Author produced {len(authored_tool_names)} tool(s) and "
                    f"{len([k for k in files_map if k.endswith('SKILL.md')])} skill(s) "
                    f"for {job.target_agent_id}."
                ),
                "tool_name": primary_tool,
                "tool_names": authored_tool_names,
                "blueprint_skills": skill_specs,
                "authored_files": list(files_map.keys()),
                "files_map": files_map,
                "phase": PHASE_AUTHOR,
                "author_notes": " | ".join(author_notes),
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={
                "files_map": files_map,
                "tool_name": primary_tool,
                "tool_names": authored_tool_names,
            },
        )



def _is_services_brief(seed_intent: str, objectives: list, agent_id: str = "") -> bool:
    import re

    combined = f"{agent_id} {seed_intent} {' '.join(str(o) for o in (objectives or []))}".lower()
    if ToolSynthesizer.is_hyperv_domain(agent_id or "x", seed_intent, objectives):
        return False
    return (
        re.search(r"\bwindows?\s*services?\b|\bget-service\b|\bsysadmin\b", combined) is not None
    )


def _tool_mismatches_domain(
    tool_code: str,
    seed_intent: str,
    objectives: list,
    agent_id: str = "",
) -> bool:
    """True when authored tool clearly belongs to the wrong execution domain."""
    low = (tool_code or "").lower()
    if not low.strip():
        return False
    services = _is_services_brief(seed_intent, objectives, agent_id)
    hypervish = ToolSynthesizer.is_hyperv_domain(agent_id or "x", seed_intent, objectives)
    norm = low.replace(chr(92)+chr(92), chr(92))
    looks_hyperv = ("get-vm" in norm) or ("new-vm" in norm) or ("import-module hyper-v" in norm)
    looks_services = ("get-service" in norm) or ("start-service" in norm)
    if services and looks_hyperv and not looks_services:
        return True
    if hypervish and looks_services and not looks_hyperv:
        return True
    return False


def _skill_mismatches_domain(
    skill_md: str,
    seed_intent: str,
    objectives: list,
    agent_id: str = "",
) -> bool:
    low = (skill_md or "").lower()
    if not low.strip():
        return False
    if _is_services_brief(seed_intent, objectives, agent_id):
        if "virtual machine" in low or "vhdx" in low or "list_switches" in low:
            return True
    return False


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
