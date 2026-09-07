"""Blueprint phase: Wiki notes + pack inventory → skill list + tools-per-skill (CARD-171)."""

from __future__ import annotations

import json
import logging
import re
from typing import List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_BLUEPRINT
from src.application.agent_training_factory.wiki_frontmatter import filter_factory_notes
from src.application.orchestration.capability_graph import ToolConsolidationGate
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)


def _scrub_negated_phrases(text: str) -> str:
    """Remove 'no X' / 'without X' / 'not X' spans so exclusions do not add focuses."""
    body = text or ""
    # Multi-word exclusions first (longest first).
    multi = (
        r"virtual\s+switch",
        r"iso\s+download",
        r"switch\s*/\s*nic",
        r"network\s+adapter",
        r"get-service",
        r"new-vm",
        r"start-vm",
        r"stop-vm",
        r"remove-vm",
        r"networking",
        r"checkpoints?",
        r"unattend",
        r"oscdimg",
        r"switch",
        r"nic",
    )
    for phrase in multi:
        body = re.sub(rf"\b(?:no|not|without)\s+{phrase}\b", " ", body, flags=re.I)
    # Single token exclusions (do not cross commas).
    body = re.sub(
        r"\b(?:no|not|without)\s+[\w.-]+",
        " ",
        body,
        flags=re.I,
    )
    return body


def classify_deliverable_type(
    agent_id: str,
    seed_intent: str = "",
    objectives: list | None = None,
    requested_type: Optional[str] = None,
) -> str:
    """Classify capability deliverable architecture: 'mcp' vs 'native_tool' [CARD-176, ADR 0049]."""
    req = (requested_type or "auto").strip().lower()
    if req in ("mcp", "native_tool"):
        return req

    from src.application.orchestration.tool_synthesizer import ToolSynthesizer

    # 1. System, PowerShell, Hyper-V, or Docker/OS domains -> MCP Server (subprocess isolation)
    if ToolSynthesizer.is_powershell_or_system_domain(agent_id, seed_intent, objectives):
        return "mcp"
    if ToolSynthesizer.is_hyperv_domain(agent_id, seed_intent, objectives):
        return "mcp"

    combined = f"{agent_id} {seed_intent} {' '.join(str(o) for o in (objectives or []))}".lower()
    mcp_infra_patterns = (
        "docker", "kubernetes", "k8s", "proxmox", "hyperv", "vmware", "virtualbox",
        "ssh", "powershell", "cmdlet", "systemctl", "sysadmin", "aws", "azure", "gcp",
        "network", "vlan", "switch", "router", "firewall", "rest api", "daemon",
    )
    if any(p in combined for p in mcp_infra_patterns):
        return "mcp"

    # 2. Local data, sqlite, finance, text -> Native In-Process Python Tools
    return "native_tool"


def hyperv_focus_from_brief(
    agent_id: str,
    seed_intent: str = "",
    objectives: list | None = None,
) -> set[str]:
    """Derive which Hyper-V lifecycle skill buckets the brief actually asks for.

    Respects explicit exclusions (no unattend / no ISO download / no switch) so a
    checkpoint-only train does not force unattend/network/template theater.
    Checkpoint-only briefs map to focus "checkpoint" (not full VM create/start/stop).
    """
    from src.application.orchestration.tool_synthesizer import ToolSynthesizer

    if not ToolSynthesizer.is_hyperv_domain(agent_id, seed_intent, objectives):
        return set()

    raw = f"{seed_intent} {' '.join(str(o) for o in (objectives or []))}".lower()
    no_unattend = any(
        tok in raw
        for tok in (
            "no unattend",
            "no oscdimg",
            "no iso download",
            "without unattend",
            "not unattend",
        )
    )
    combined = _scrub_negated_phrases(raw)
    focuses: set[str] = set()
    checkpoint_markers = (
        "checkpoint",
        "snapshot",
        "restore-vmsnapshot",
        "get-vmsnapshot",
        "remove-vmsnapshot",
        "checkpoint-vm",
        "list_checkpoints",
        "restore_checkpoint",
        "remove_checkpoint",
    )
    vm_lifecycle_markers = (
        "new-vm",
        "start-vm",
        "stop-vm",
        "remove-vm",
        "vm lifecycle",
        "create vm",
        "provision vm",
        "virtual machines",
    )
    net_markers = (
        "switch",
        "vmswitch",
        "nic",
        "network adapter",
        "new-vmswitch",
        "get-vmswitch",
        "add-vmnetworkadapter",
        "connect-vmnetworkadapter",
    )
    unattend_markers = ("unattend", "autounattend", "oscdimg", "answer-file", "answer file", "answer iso")
    template_markers = ("template maintenance", "patch template", "export_template", "gold image")

    def _has(marker: str) -> bool:
        # Word-ish boundary so "new-vm" does not match inside "new-vmswitch".
        return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", combined) is not None

    wants_checkpoint = any(_has(m) for m in checkpoint_markers)
    wants_vm_lifecycle = any(_has(m) for m in vm_lifecycle_markers)
    if wants_checkpoint and not wants_vm_lifecycle:
        focuses.add("checkpoint")
    elif wants_checkpoint or wants_vm_lifecycle:
        focuses.add("vm")
    if any(_has(m) for m in net_markers):
        focuses.add("network")
    if any(m in combined for m in unattend_markers) and not no_unattend:
        if "unattend" in combined or "autounattend" in combined or "oscdimg" in combined:
            focuses.add("unattend")
    if any(m in combined for m in template_markers) and not no_unattend:
        focuses.add("template")
    if no_unattend:
        focuses.discard("unattend")
        focuses.discard("template")
    if focuses:
        return focuses
    if agent_id.replace("-", "").lower() == "hyperv":
        return {"vm", "network", "unattend", "template"}
    return set()



def hyperv_lifecycle_blueprint(
    agent_id: str,
    seed_intent: str = "",
    objectives: list | None = None,
    focuses: set[str] | None = None,
) -> dict:
    """Deterministic Hyper-V blueprint (CARD-171/172).

    One action-dispatcher tool per lifecycle skill - never a single fat manage_hyperv.
    When focuses is provided (or derived from brief), only those skills/tools are emitted.
    """
    _ = agent_id
    if focuses is None:
        focuses = hyperv_focus_from_brief(agent_id, seed_intent, objectives)
    all_skills = [
        {
            "id": "hyperv-vm-lifecycle",
            "name": "Hyper-V Checkpoint Lifecycle",
            "description": "Create/list/restore/remove VM checkpoints via Hyper-V cmdlets only.",
            "tools": ["manage_hyperv_vm"],
            "_focus": "checkpoint",
        },
        {
            "id": "hyperv-vm-lifecycle",
            "name": "Hyper-V VM Lifecycle",
            "description": "Create/start/stop/checkpoint/restore/remove VMs and checkpoints via Hyper-V cmdlets.",
            "tools": ["manage_hyperv_vm"],
            "_focus": "vm",
        },
        {
            "id": "hyperv-networking",
            "name": "Hyper-V Networking",
            "description": "Virtual switch lifecycle and NIC attachment for Hyper-V VMs.",
            "tools": ["manage_hyperv_network"],
            "_focus": "network",
        },
        {
            "id": "hyperv-unattend-templates",
            "name": "Hyper-V Unattend Templates",
            "description": "Autounattend answer files, answer-file ISO, OS ISO mount, reusable template VMs.",
            "tools": ["manage_hyperv_unattend"],
            "_focus": "unattend",
        },
        {
            "id": "hyperv-template-maintenance",
            "name": "Hyper-V Template Maintenance",
            "description": "Routine patching and maintenance of Hyper-V template VMs.",
            "tools": ["manage_hyperv_template"],
            "_focus": "template",
        },
    ]
    all_tools = [
        {
            "name": "manage_hyperv_vm",
            "target_entity": "hyperv_vm",
            "actions": [
                "status",
                "checkpoint",
                "list_checkpoints",
                "restore_checkpoint",
                "remove_checkpoint",
            ],
            "description": (
                "Checkpoint dispatcher using Hyper-V\\Checkpoint-VM/Get-VMSnapshot/"
                "Restore-VMSnapshot/Remove-VMSnapshot only."
            ),
            "skill_id": "hyperv-vm-lifecycle",
            "_focus": "checkpoint",
        },
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
                "list_checkpoints",
                "restore_checkpoint",
                "remove_checkpoint",
                "remove",
            ],
            "description": (
                "VM + checkpoint dispatcher using Hyper-V\\Get-VM/New-VM/Start-VM/Stop-VM/"
                "Checkpoint-VM/Get-VMSnapshot/Restore-VMSnapshot/Remove-VMSnapshot/Remove-VM."
            ),
            "skill_id": "hyperv-vm-lifecycle",
            "_focus": "vm",
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
            "_focus": "network",
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
            "_focus": "unattend",
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
            "_focus": "template",
        },
    ]
    skills = [{k: v for k, v in s.items() if k != "_focus"} for s in all_skills if s["_focus"] in focuses]
    tools = [{k: v for k, v in t.items() if k != "_focus"} for t in all_tools if t["_focus"] in focuses]
    return {
        "skills": skills,
        "tools": tools,
        "rationale": f"Hyper-V focused blueprint for {sorted(focuses)}: one skill+dispatcher per concern.",
        "focuses": sorted(focuses),
    }


def wants_hyperv_multi_skill(agent_id: str, seed_intent: str, objectives: list | None) -> bool:
    """True when Hyper-V domain brief should use the deterministic lifecycle blueprint."""
    from src.application.orchestration.tool_synthesizer import ToolSynthesizer

    if not ToolSynthesizer.is_hyperv_domain(agent_id, seed_intent, objectives):
        return False
    focuses = hyperv_focus_from_brief(agent_id, seed_intent, objectives)
    return len(focuses) >= 1


class BlueprintPhase:
    id = PHASE_BLUEPRINT
    label = "Blueprint"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()

        wiki_slice = _read_grounding(ctx)

        # Classify deliverable architecture (CARD-176, ADR 0049)
        requested_deliv = getattr(job, "deliverable_type", None)
        if not requested_deliv and ctx.repo:
            for p in ctx.repo.list_packets(job.id) or []:
                payload = getattr(p, "payload", None) or {}
                if isinstance(payload, dict) and payload.get("deliverable_type"):
                    requested_deliv = payload["deliverable_type"]
                    break

        deliverable_type = classify_deliverable_type(
            agent_id=job.target_agent_id,
            seed_intent=job.seed_intent,
            objectives=ctx.objectives,
            requested_type=requested_deliv,
        )

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


        # Hyper-V briefs: ALWAYS force durable brief-focused blueprint (narrow trains stay narrow).
        if wants_hyperv_multi_skill(job.target_agent_id, job.seed_intent, ctx.objectives):
            focuses = hyperv_focus_from_brief(job.target_agent_id, job.seed_intent, ctx.objectives)
            multi = hyperv_lifecycle_blueprint(
                job.target_agent_id, job.seed_intent, ctx.objectives, focuses=focuses
            )
            skills = multi["skills"]
            tools = multi["tools"]
            llm_data["rationale"] = multi["rationale"]
            llm_data["focuses"] = sorted(focuses)

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

        for t in tools:
            if isinstance(t, dict):
                t.setdefault("deliverable_type", deliverable_type)

        blueprint = {
            "deliverable_type": deliverable_type,
            "skills": skills,
            "tools": tools,
            "scenarios": scenarios,
            "rationale": llm_data.get("rationale") or "",
            "wiki_excerpt_chars": len(wiki_slice),
            "focuses": list(llm_data.get("focuses") or []),
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
