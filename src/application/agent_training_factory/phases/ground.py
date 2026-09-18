"""Ground phase: research role brief -> Wiki operating manual + medium map (CARD-171)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.prompt_registry import get_phase_system_prompt
from src.application.agent_training_factory.registry import PHASE_GROUND
from src.application.agent_training_factory.sop_rubric import ensure_structured_sop, sop_is_structured
from src.application.agent_training_factory.wiki_frontmatter import build_factory_frontmatter
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)

_manual_has_structured_sop = sop_is_structured



def _latest_intent_distill(ctx: PhaseContext) -> Dict[str, Any]:
    try:
        packets = ctx.repo.list_packets(ctx.job_id) if ctx.repo else []
    except Exception:
        return {}
    for p in reversed(packets or []):
        if getattr(p, "sender_role", "") != "intent_distill":
            continue
        payload = getattr(p, "payload", None) or {}
        if isinstance(payload, dict):
            return payload
    return {}


class GroundPhase:
    id = PHASE_GROUND
    label = "Ground"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        objectives = ctx.objectives
        distill = _latest_intent_distill(ctx)
        answers = distill.get("answers") if isinstance(distill.get("answers"), dict) else {}
        lessons = distill.get("lessons") if isinstance(distill.get("lessons"), list) else []
        shape_changed = bool(distill.get("shape_changed", True))
        outer = int(getattr(job, "outer_rinse_count", 0) or 0)
        combined = f"{job.target_agent_id} {job.seed_intent} {' '.join(objectives)}".lower()
        if answers:
            combined = (
                f"{combined} {answers.get('outcome','')} {answers.get('medium','')} "
                f"{answers.get('professional_sop','')} {answers.get('scenarios','')}"
            ).lower()

        fallback_medium = _heuristic_medium(combined)

        target_dir = getattr(ctx, "target_directory", None)
        inspection_data: Dict[str, Any] = {}
        files_tree: List[Dict[str, Any]] = []
        if target_dir:
            from pathlib import Path
            p = Path(target_dir)
            if p.exists() and p.is_dir():
                try:
                    from src.application.skills.environment_inspection import EnvironmentInspectionSkill
                    inspector = EnvironmentInspectionSkill()
                    inspection_data = inspector.compile_manifest(str(p))
                    files_tree = inspection_data.get("files_tree", [])
                except Exception as ex:
                    logger.warning("Environment inspection failed on %s: %s", target_dir, ex)

        fallback_manifest = _heuristic_manifest(job, clean_slug, fallback_medium, combined)
        if files_tree:
            extra_bins = []
            extra_mods = []
            for f in files_tree:
                rpath = str(f.get("relative_path", "")).lower()
                fmt = f.get("format")
                if fmt == "opentofu" or rpath.endswith(".tf"):
                    if "tofu.exe" not in extra_bins and "tofu" not in extra_bins:
                        extra_bins.append("tofu.exe")
                    if "OpenTofu" not in extra_mods:
                        extra_mods.append("OpenTofu")
                if "ansible" in rpath or rpath.endswith((".yml", ".yaml")):
                    if "ansible-playbook" not in extra_bins:
                        extra_bins.append("ansible-playbook")
                if rpath.endswith((".ps1", ".psm1")):
                    if "powershell.exe" not in extra_bins:
                        extra_bins.append("powershell.exe")
                if rpath.endswith(".py"):
                    if "python.exe" not in extra_bins:
                        extra_bins.append("python.exe")
            for b in extra_bins:
                if b not in fallback_manifest["discovered_binaries"]:
                    fallback_manifest["discovered_binaries"].append(b)
            for m in extra_mods:
                if m not in fallback_manifest["discovered_modules"]:
                    fallback_manifest["discovered_modules"].append(m)
            if extra_bins and fallback_medium in ("computation", "api"):
                fallback_medium = "cli"
                fallback_manifest["target_medium"] = "cli"

            script_exts = (".tf", ".hcl", ".yml", ".yaml", ".ps1", ".psm1", ".py", ".sh", ".bat", ".cmd")
            script_files = [
                f for f in files_tree
                if any(str(f.get("relative_path", "")).lower().endswith(ext) for ext in script_exts)
            ]
            other_files = [f for f in files_tree if f not in script_files]
            files_tree = script_files + other_files
            fallback_manifest["script_files"] = [f.get("relative_path") for f in script_files]

        fallback_manifest["files_tree"] = files_tree
        rich_manual = _build_operating_manual(
            job, fallback_medium, objectives, fallback_manifest, target_directory=target_dir or "", files_tree=files_tree
        )

        files_summary = "\n".join(
            f"- {f.get('relative_path')} ({f.get('format')})" for f in files_tree[:35]
        ) if files_tree else "(none)"

        system_prompt = get_phase_system_prompt(self.id, ctx.db_path)
        llm_data = await phase_llm_json(
            ctx.gateway,
            system=system_prompt,
            user=(
                f"Agent id: {job.target_agent_id}\n"
                f"Seed intent: {job.seed_intent}\n"
                f"Objectives: {json.dumps(objectives)}\n"
                f"Target host: {job.target_host or 'localhost'}\n"
                f"Target directory: {target_dir or 'None'}\n"
                f"Project assets:\n{files_summary[:1500]}\n"
                f"Intent Distill answers: {json.dumps(answers)[:2500]}\n"
                f"Reflexion lessons: {json.dumps(lessons)[:1500]}\n"
                "Write an operating manual and medium map suitable for Wiki storage. "
                "If Reflexion lessons are present, append a Reflexion Lessons section."
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
        distill_medium = str(answers.get("medium") or "").strip().lower()
        if distill_medium in ("cli", "api", "database", "filesystem", "computation"):
            if not force_heuristic:
                fallback_medium = distill_medium
            elif distill_medium == "cli":
                fallback_medium = distill_medium
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

        if not _manual_has_structured_sop(manual):
            manual = ensure_structured_sop(
                manual,
                seed_intent=str(job.seed_intent or ""),
                objectives=list(objectives or []),
                title=str(job.target_agent_id or "agent"),
            )
            if "## Paths referenced" not in manual and "## Medium" not in manual:
                # Prefer full rich manual when LLM echo failed the rubric.
                manual = rich_manual

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
            "target_directory": str(Path(target_dir).resolve()) if target_dir else None,
            "os_type": "windows",
            "target_medium": medium,
            "discovered_binaries": binaries,
            "discovered_modules": modules,
            "namespace_isolation": isolation,
            "files_tree": files_tree,
            "script_files": fallback_manifest.get("script_files", []),
            "detected_formats": inspection_data.get("detected_formats", []),
            "domain_sops": inspection_data.get("domain_sops", []),
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
                if lessons:
                    lesson_block = "\n\n## Reflexion lessons\n" + "\n".join(
                        f"- {x}" for x in lessons if str(x).strip()
                    )
                    if "## Reflexion lessons" not in manual:
                        manual = manual + lesson_block
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

        outcome = "ok"
        recipient = "blueprint"
        msg = (
            f"Ground completed for {job.target_agent_id} "
            f"(medium: {medium}). Wiki notes: {len(wiki_paths)}."
        )
        # Outer rinse: skip Blueprint when distill says skill/tool shape unchanged
        if outer > 0 and not shape_changed:
            outcome = "skip_blueprint"
            recipient = "author"
            msg = msg + " (skip Blueprint: shape unchanged)."
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="ground",
            recipient_role=recipient,
            node_id=PHASE_GROUND,
            payload={
                "message": msg,
                "manifest": manifest_payload,
                "wiki_paths": wiki_paths,
                "phase": PHASE_GROUND,
                "skip_blueprint": outcome == "skip_blueprint",
                "shape_changed": shape_changed,
                "lessons": lessons,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome=outcome,
            message=msg,
            artifacts={
                "manifest": manifest_payload,
                "wiki_paths": wiki_paths,
                "operating_manual": manual,
                "shape_changed": shape_changed,
                "answers": answers,
                "lessons": lessons,
            },
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


def _build_operating_manual(
    job: Any,
    medium: str,
    objectives: list,
    manifest: Dict[str, Any],
    target_directory: str = "",
    files_tree: Optional[List[Dict[str, Any]]] = None,
) -> str:
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

    files_block = ""
    if files_tree:
        flines = "\n".join(
            f"- `{f.get('relative_path')}` ({f.get('format', 'unknown')})"
            for f in files_tree[:30]
        )
        files_block = f"\n\n## Project Files & Scripts\nTarget directory: `{target_directory}`\n{flines}"

    return (
        f"# Operating Manual - {job.target_agent_id}\n\n"
        f"## Purpose\n{job.seed_intent}\n\n"
        f"## Objectives\n{obj_lines}\n\n"
        f"## Paths referenced\n{path_block}"
        f"{files_block}\n\n"
        f"## Medium\n{medium}\n\n"
        f"## Discovered binaries\n{', '.join(manifest.get('discovered_binaries') or []) or '(none)'}\n\n"
        f"## Discovered modules\n{', '.join(manifest.get('discovered_modules') or []) or '(none)'}\n\n"
        f"## Steps\n"
        f"1. Confirm target medium access and prerequisites.\n"
        f"2. Execute brief-scoped actions only (no out-of-focus capabilities).\n"
        f"3. Capture outputs for verification.\n\n"
        f"## Verify\n"
        f"- Each objective / DONE-WHEN is true on the live medium.\n"
        f"- Tool surface matches the brief focus.\n\n"
        f"## Rollback\n"
        f"- Undo the last mutating action when safe; restore prior state if needed.\n"
        f"- Stop and request approval when policy requires it.\n"
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
