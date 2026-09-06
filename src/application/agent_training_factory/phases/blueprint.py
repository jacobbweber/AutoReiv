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



def hyperv_lifecycle_blueprint(
    agent_id: str,
    seed_intent: str = "",
    objectives: list | None = None,
) -> dict:
    """Deterministic multi-skill Hyper-V blueprint (CARD-171 / hyperv pack structure).

    One action-dispatcher tool per lifecycle skill — never a single fat manage_hyperv.
    """
    _ = (agent_id, seed_intent, objectives)  # brief retained for future heuristics
    skills = [
        {
            "id": "hyperv-vm-lifecycle",
            "name": "Hyper-V VM Lifecycle",
            "description": "Create/start/stop/checkpoint/remove VMs and report status via Hyper-V cmdlets.",
            "tools": ["manage_hyperv_vm"],
        },
        {
            "id": "hyperv-networking",
            "name": "Hyper-V Networking",
            "description": "Virtual switch lifecycle and NIC attachment for Hyper-V VMs.",
            "tools": ["manage_hyperv_network"],
        },
        {
            "id": "hyperv-unattend-templates",
            "name": "Hyper-V Unattend Templates",
            "description": "Autounattend answer files, answer-file ISO, OS ISO mount, reusable template VMs.",
            "tools": ["manage_hyperv_unattend"],
        },
        {
            "id": "hyperv-template-maintenance",
            "name": "Hyper-V Template Maintenance",
            "description": "Routine patching and maintenance of Hyper-V template VMs.",
            "tools": ["manage_hyperv_template"],
        },
    ]
    tools = [
        {
            "name": "manage_hyperv_vm",
            "target_entity": "hyperv_vm",
            "actions": [
                "status",
                "list",
                "get",
                "create",
                "start",
                "stop",
                "restart",
                "checkpoint",
                "remove",
            ],
            "description": "VM lifecycle dispatcher using Hyper-V\\Get-VM/New-VM/Start-VM/Stop-VM/Checkpoint-VM/Remove-VM.",
            "skill_id": "hyperv-vm-lifecycle",
        },
        {
            "name": "manage_hyperv_network",
            "target_entity": "hyperv_network",
            "actions": [
                "list_switches",
                "create_switch",
                "remove_switch",
                "attach_nic",
                "detach_nic",
            ],
            "description": "Switch/NIC dispatcher using Hyper-V\\Get-VMSwitch/New-VMSwitch/Remove-VMSwitch/Add-VMNetworkAdapter.",
            "skill_id": "hyperv-networking",
        },
        {
            "name": "manage_hyperv_unattend",
            "target_entity": "hyperv_unattend",
            "actions": [
                "build_autounattend",
                "build_autounattend_iso",
                "mount_os_iso",
                "mount_answer_iso",
                "create_template_vm",
            ],
            "description": "Unattend/ISO/template dispatcher (Autounattend + Set-VMDvdDrive + New-VM).",
            "skill_id": "hyperv-unattend-templates",
        },
        {
            "name": "manage_hyperv_template",
            "target_entity": "hyperv_template",
            "actions": [
                "list_templates",
                "checkpoint_template",
                "export_template",
                "start_maintenance",
                "stop_maintenance",
            ],
            "description": "Template maintenance dispatcher (checkpoint/export/start/stop for template VMs).",
            "skill_id": "hyperv-template-maintenance",
        },
    ]
    return {
        "skills": skills,
        "tools": tools,
        "rationale": "Hyper-V multi-lifecycle specialist: one skill+dispatcher per concern.",
    }


def wants_hyperv_multi_skill(agent_id: str, seed_intent: str, objectives: list | None) -> bool:
    """True when brief spans multiple Hyper-V lifecycles (or agent is hyperv with rich brief)."""
    from src.application.orchestration.tool_synthesizer import ToolSynthesizer

    if not ToolSynthesizer.is_hyperv_domain(agent_id, seed_intent, objectives):
        return False
    combined = f"{agent_id} {seed_intent} {' '.join(str(o) for o in (objectives or []))}".lower()
    markers = [
        "unattend",
        "autounattend",
        "iso",
        "template",
        "switch",
        "network",
        "lifecycle",
        "checkpoint",
        "patch",
        "maintenance",
        "new-vm",
        "vmswitch",
    ]
    hits = sum(1 for m in markers if m in combined)
    # Dedicated hyperv agent with any lifecycle language, or >=2 distinct concerns.
    if agent_id.replace("-", "").lower() == "hyperv" and hits >= 2:
        return True
    return hits >= 3


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
                "Using Wiki grounding notes and the environment manifest, design a non-overlapping multi-skill "
                "skill list and tools-per-skill plan. Return ONLY JSON with keys: "
                "skills (list of {id,name,description,tools}), "
                "tools (list of {name,target_entity,actions,description}), "
                "scenarios (list of done-when strings proving capability), "
                "rationale (string)."
            ),
            user=(
                f"Agent: {job.target_agent_id}\n"
                f"Intent: {job.seed_intent}\n"
                f"Objectives: {json.dumps(ctx.objectives)}\n"
                f"Manifest: {json.dumps(manifest)[:2000]}\n"
                f"Wiki grounding excerpts:\n{wiki_slice[:3000]}\n"
                "Avoid overlapping tools. Prefer one action-dispatcher tool PER skill/entity "
                "(e.g. VM lifecycle vs networking vs unattend templates). "
                "Do NOT collapse an entire multi-lifecycle agent into one fat manage_* tool. "
                "Give each tool a distinct target_entity."
            ),
            fallback={"skills": fallback_skills, "tools": fallback_tools, "rationale": "heuristic"},
        )

        tools = list(llm_data.get("tools") or fallback_tools)
        skills = list(llm_data.get("skills") or fallback_skills)
        scenarios = list(llm_data.get("scenarios") or [])
        if not scenarios:
            # Prefer Intent Distill scenario answers, else objectives
            try:
                for p in reversed(ctx.repo.list_packets(job.id) or []):
                    if getattr(p, "sender_role", "") != "intent_distill":
                        continue
                    ans = (getattr(p, "payload", None) or {}).get("answers") or {}
                    scen = str(ans.get("scenarios") or "").strip()
                    if scen:
                        import re as _re
                        scenarios = [x.strip() for x in _re.split(r"\s*\|\s*|\n|;", scen) if x.strip()]
                    break
            except Exception:
                scenarios = []
        if not scenarios:
            scenarios = [str(o).strip() for o in (ctx.objectives or []) if str(o).strip()]
        if not scenarios and job.seed_intent:
            scenarios = [f"Operator achieves: {job.seed_intent[:160]}"]


        # Hyper-V multi-lifecycle briefs: force durable multi-skill structure.
        if wants_hyperv_multi_skill(job.target_agent_id, job.seed_intent, ctx.objectives):
            multi = hyperv_lifecycle_blueprint(job.target_agent_id, job.seed_intent, ctx.objectives)
            # Prefer multi when LLM emitted a single fat tool or fewer than 3 skills.
            if len(skills) < 3 or len(tools) < 3 or (
                len(tools) == 1 and str(tools[0].get("name") or "").startswith("manage_")
            ):
                skills = multi["skills"]
                tools = multi["tools"]
                llm_data["rationale"] = multi["rationale"]

        gate = ToolConsolidationGate()
        consolidation = gate.evaluate(
            [
                {
                    "name": t.get("name", ""),
                    # Preserve distinct entities — never default every tool to agent slug.
                    "target_entity": t.get("target_entity")
                    or t.get("skill_id")
                    or t.get("name")
                    or clean_slug,
                    "verb": (t.get("actions") or ["manage"])[0]
                    if isinstance(t.get("actions"), list)
                    else "manage",
                }
                for t in tools
            ]
        )
        # Only consolidate accidental single-verb clones; never smash intentional multi-skill plans.
        if consolidation.get("should_consolidate") and len(skills) <= 1 and len(tools) >= 2:
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
            "scenarios": scenarios,
            "rationale": llm_data.get("rationale") or "",
            "wiki_excerpt_chars": len(wiki_slice),
        }
        # Persist scenario matrix on the job when supported
        try:
            import json as _json
            job.scenario_matrix_json = _json.dumps({"scenarios": scenarios})
            ctx.repo.save_job(job)
        except Exception:
            pass

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id=PHASE_BLUEPRINT,
            payload={
                "message": (
                    f"Blueprint formulated: {len(skills)} skill(s), {len(tools)} tool(s), "
                    f"{len(scenarios)} scenario(s) for {job.target_agent_id}."
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
