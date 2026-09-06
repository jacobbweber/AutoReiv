"""Ground phase: research role brief -> Wiki operating manual + medium map (CARD-171)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_GROUND
from src.application.agent_training_factory.wiki_frontmatter import build_factory_frontmatter
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)


class GroundPhase:
    id = PHASE_GROUND
    label = "Ground"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        objectives = ctx.objectives
        combined = f"{job.target_agent_id} {job.seed_intent} {' '.join(objectives)}".lower()

        fallback_medium = _heuristic_medium(combined)
        fallback_manifest = _heuristic_manifest(job, clean_slug, fallback_medium, combined)
        rich_manual = _build_operating_manual(job, fallback_medium, objectives, fallback_manifest)

        llm_data = await phase_llm_json(
            ctx.gateway,
            system=(
                "You are the Ground phase of the Agent Training Factory. "
                "Research the target agent role and produce grounding facts for later phases. "
                "Return ONLY JSON with keys: "
                "target_medium (cli|api|database|filesystem|computation), "
                "discovered_binaries (list), discovered_modules (list), "
                "namespace_isolation (object), operating_manual (markdown string), "
                "medium_map (object describing how tools should talk to the medium)."
            ),
            user=(
                f"Agent id: {job.target_agent_id}\n"
                f"Seed intent: {job.seed_intent}\n"
                f"Objectives: {json.dumps(objectives)}\n"
                f"Target host: {job.target_host or 'localhost'}\n"
                "Write an operating manual and medium map suitable for Wiki storage."
            ),
            fallback={
                "target_medium": fallback_manifest["target_medium"],
                "discovered_binaries": fallback_manifest["discovered_binaries"],
                "discovered_modules": fallback_manifest["discovered_modules"],
                "namespace_isolation": fallback_manifest["namespace_isolation"],
                "operating_manual": rich_manual,
                "medium_map": {
                    "medium": fallback_manifest["target_medium"],
                    "binaries": fallback_manifest["discovered_binaries"],
                    "modules": fallback_manifest["discovered_modules"],
                },
            },
        )

        # Prefer heuristic medium/modules when intent keywords clearly match.
        force_heuristic = _is_hyperv_or_cli_intent(combined) and fallback_medium == "cli"
        llm_medium = str(llm_data.get("target_medium") or "").strip().lower()
        if force_heuristic:
            medium = fallback_medium
            binaries = list(fallback_manifest["discovered_binaries"])
            modules = list(fallback_manifest["discovered_modules"])
            isolation = dict(fallback_manifest["namespace_isolation"])
        else:
            medium = llm_medium or fallback_medium
            binaries = list(
                llm_data.get("discovered_binaries") or fallback_manifest["discovered_binaries"]
            )
            modules = list(
                llm_data.get("discovered_modules") or fallback_manifest["discovered_modules"]
            )
            isolation = dict(
                llm_data.get("namespace_isolation") or fallback_manifest["namespace_isolation"]
            )

        llm_manual = str(llm_data.get("operating_manual") or "").strip()
        if len(llm_manual) < 80 or (job.seed_intent[:32] and job.seed_intent[:32] not in llm_manual):
            manual = rich_manual
            if llm_manual and llm_manual not in manual:
                manual = manual + "\n\n## LLM enrichment notes\n" + llm_manual
        else:
            manual = llm_manual
            for token in ("unattend", "iso", "vhdx", "template"):
                if token in combined and token not in manual.lower():
                    manual = rich_manual
                    break

        medium_map = llm_data.get("medium_map") if isinstance(llm_data.get("medium_map"), dict) else {}
        if force_heuristic or not medium_map:
            medium_map = {
                "medium": medium,
                "binaries": binaries,
                "modules": modules,
            }

        manifest_payload: Dict[str, Any] = {
            "target_agent_id": job.target_agent_id,
            "target_host": job.target_host or "localhost",
            "os_type": "windows",
            "target_medium": medium,
            "discovered_binaries": binaries,
            "discovered_modules": modules,
            "namespace_isolation": isolation,
            "inspected_endpoints": [],
            "status": "verified_read_only",
            "medium_map": medium_map,
        }

        job.environment_manifest_json = json.dumps(manifest_payload)
        ctx.repo.save_job(job)

        wiki_paths: List[str] = []
        if ctx.wiki is not None:
            try:
                fm = build_factory_frontmatter(
                    agent_id=job.target_agent_id,
                    medium=medium,
                    factory_job_id=job.id,
                    status="grounded",
                    extra={"document_type": "factory-grounding"},
                )
                medium_md = (
                    f"# Medium Map - {job.target_agent_id}\n\n"
                    f"```json\n{json.dumps(manifest_payload.get('medium_map') or manifest_payload, indent=2)}\n```\n"
                )
                note1 = ctx.wiki.create_note(
                    title=f"Factory Grounding - {job.target_agent_id} Operating Manual",
                    content=manual,
                    domain="agent-training-factory",
                    topic=job.target_agent_id,
                    category="notes",
                    document_type="factory-grounding",
                    tags=["agent-training-factory", "grounding", job.target_agent_id],
                    summary=f"Grounding operating manual for {job.target_agent_id}",
                    status="active",
                    extra_meta=fm,
                )
                note2 = ctx.wiki.create_note(
                    title=f"Factory Grounding - {job.target_agent_id} Medium Map",
                    content=medium_md,
                    domain="agent-training-factory",
                    topic=job.target_agent_id,
                    category="notes",
                    document_type="factory-grounding",
                    tags=["agent-training-factory", "medium-map", job.target_agent_id],
                    summary=f"Medium map for {job.target_agent_id}",
                    status="active",
                    extra_meta=fm,
                )
                for n in (note1, note2):
                    path = n.get("path") or n.get("relative_path") or ""
                    if path:
                        wiki_paths.append(path)
            except Exception as exc:
                logger.warning("Ground phase Wiki write failed: %s", exc)

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="ground",
            recipient_role="blueprint",
            node_id=PHASE_GROUND,
            payload={
                "message": (
                    f"Ground completed for {job.target_agent_id} "
                    f"(medium: {medium}). Wiki notes: {len(wiki_paths)}."
                ),
                "manifest": manifest_payload,
                "wiki_paths": wiki_paths,
                "phase": PHASE_GROUND,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=packet.payload["message"],
            artifacts={"manifest": manifest_payload, "wiki_paths": wiki_paths, "operating_manual": manual},
        )


def _is_hyperv_or_cli_intent(combined: str) -> bool:
    keywords = [
        "hyper-v",
        "hyperv",
        "unattend",
        "autounattend",
        "iso",
        "vhdx",
        "template",
        "vm",
        "virtual machine",
        "powershell",
        "cmdlet",
        "active directory",
        "sysadmin",
    ]
    return any(w in combined for w in keywords)


def _build_operating_manual(job: Any, medium: str, objectives: list, manifest: Dict[str, Any]) -> str:
    objs = objectives or []
    obj_lines = "\n".join(f"- {o}" for o in objs) if objs else "- (none provided)"
    hay = f"{job.seed_intent} {' '.join(str(o) for o in objs)}"
    paths: List[str] = []
    for m in re.finditer(r"[A-Za-z]:\\[^\s\"']+|/[\\w./-]+\\.(?:iso|vhdx|vhd|wim)", hay, re.IGNORECASE):
        paths.append(m.group(0))
    # Also catch simple *.ISO tokens
    for m in re.finditer(r"\b[\w./\\-]+\.iso\b", hay, re.IGNORECASE):
        paths.append(m.group(0))
    uniq_paths = list(dict.fromkeys(paths))
    path_block = "\n".join(f"- `{p}`" for p in uniq_paths) if uniq_paths else "- (none detected in brief)"
    return (
        f"# Operating Manual - {job.target_agent_id}\n\n"
        f"## Purpose\n{job.seed_intent}\n\n"
        f"## Objectives\n{obj_lines}\n\n"
        f"## Paths referenced\n{path_block}\n\n"
        f"## Medium\n{medium}\n\n"
        f"## Discovered binaries\n{', '.join(manifest.get('discovered_binaries') or []) or '(none)'}\n\n"
        f"## Discovered modules\n{', '.join(manifest.get('discovered_modules') or []) or '(none)'}\n"
    )


def _heuristic_medium(combined: str) -> str:
    if _is_hyperv_or_cli_intent(combined):
        return "cli"
    if any(w in combined for w in ["api", "http", "rest", "endpoint", "webhook", "curl"]):
        return "api"
    if any(w in combined for w in ["sql", "database", "sqlite", "postgres", "table", "query"]):
        return "database"
    if any(w in combined for w in ["file", "csv", "json", "pdf", "image", "media", "folder"]):
        return "filesystem"
    return "computation"


def _heuristic_manifest(job: Any, clean_slug: str, medium: str, combined: str) -> Dict[str, Any]:
    binaries: List[str] = []
    modules: List[str] = []
    isolation: Dict[str, Any] = {}
    if medium == "cli":
        binaries = ["powershell.exe"]
        hypervish = any(
            w in combined
            for w in [
                "hyper-v",
                "hyperv",
                "vm",
                "virtual machine",
                "vhdx",
                "unattend",
                "autounattend",
                "iso",
                "template",
            ]
        ) or "hyperv" in str(getattr(job, "target_agent_id", "")).lower()
        if hypervish:
            modules.append("Hyper-V")
            isolation = {
                "cmdlet_prefix": "Hyper-V\\",
                "import_module": "Hyper-V",
                "collision_guard": True,
            }
    elif medium == "api":
        binaries = ["curl.exe"]
    elif medium == "database":
        binaries = ["sqlite3.exe"]
    return {
        "target_medium": medium,
        "discovered_binaries": binaries or [f"{clean_slug}-cli"],
        "discovered_modules": modules,
        "namespace_isolation": isolation,
    }
