"""Scenario Verify phase: Blueprint capability scenarios as done-whens (CARD-172)."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from src.application.agent_training_factory.failure_class import (
    classify_failure,
    decide_rinse_outcome,
)
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.phases.blueprint import hyperv_focus_from_brief
from src.application.agent_training_factory.registry import (
    PHASE_AUTHOR,
    PHASE_SCENARIO_VERIFY,
)
from src.application.orchestration.hyperv_tool_builders import ACTIONS
from src.domain.orchestration.factory_packets import FactoryPacket


def _latest_blueprint(ctx: PhaseContext) -> Dict[str, Any]:
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return {}
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        payload = getattr(p, "payload", None) or {}
        if role in ("blueprint", "conductor") or getattr(p, "node_id", "") == "blueprint":
            bp = payload.get("blueprint")
            if isinstance(bp, dict):
                return bp
    return {}


def _latest_author_files(ctx: PhaseContext) -> Dict[str, str]:
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return {}
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        node = getattr(p, "node_id", "") or ""
        if role not in ("author", "coder") and node not in (PHASE_AUTHOR, "coder_node"):
            continue
        payload = getattr(p, "payload", None) or {}
        files_map = payload.get("files_map") or {}
        if isinstance(files_map, dict) and files_map:
            return dict(files_map)
    return {}


def _strip_comments(code: str, path: str) -> str:
    """Remove comments/docstrings so prose-only comments cannot fake coverage.

    Does not strip `#` inside string literals (naive line `#` strip would truncate
    executable coverage anchors embedded in Python strings).
    """
    text = code or ""
    low_path = path.replace("\\", "/").lower()
    if low_path.endswith(".py"):
        text = re.sub(r'"""[\s\S]*?"""', " ", text)
        text = re.sub(r"'''[\s\S]*?'''", " ", text)
        # Full-line comments only
        text = re.sub(r"(?m)^[ \t]*#.*?$", " ", text)
    elif low_path.endswith(".ps1"):
        text = re.sub(r"<#[\s\S]*?#>", " ", text)
        text = re.sub(r"(?m)^[ \t]*#.*?$", " ", text)
    return text


def _tool_code_corpus(files_map: Dict[str, str]) -> str:
    """Corpus for coverage: executable tool sources only (.py / .ps1), comments stripped."""
    chunks: List[str] = []
    for path, code in (files_map or {}).items():
        norm = str(path).replace("\\", "/").lower()
        if not (norm.endswith(".py") or norm.endswith(".ps1")):
            continue
        if "/tools/" not in f"/{norm}" and not norm.startswith("tools/"):
            # Allow bare tools/foo.py or any *.ps1/*.py under tools
            if "tools/" not in norm:
                continue
        cleaned = _strip_comments(str(code or ""), norm)
        chunks.append(cleaned.lower())
    return "\n".join(chunks)


_KNOWN_CMDLETS = (
    "checkpoint-vm",
    "get-vmsnapshot",
    "restore-vmsnapshot",
    "remove-vmsnapshot",
    "rename-vmsnapshot",
    "get-vm",
    "new-vm",
    "start-vm",
    "stop-vm",
    "remove-vm",
    "new-vmswitch",
    "get-vmswitch",
    "remove-vmswitch",
    "add-vmnetworkadapter",
    "connect-vmnetworkadapter",
    "remove-vmnetworkadapter",
    "get-vmnetworkadapter",
)


def _required_cmdlets(scenario: str) -> List[str]:
    text = (scenario or "").lower().replace("/", "\\")
    found: List[str] = []
    for m in re.findall(r"hyper-v\\([a-z0-9]+-[a-z0-9]+)", text):
        found.append(m)
    for cmd in _KNOWN_CMDLETS:
        if cmd in text and cmd not in found:
            # only if explicitly named in scenario
            if re.search(rf"\b{re.escape(cmd)}\b", text):
                found.append(cmd)
    return found


def _scenario_list(blueprint: Dict[str, Any], ctx: PhaseContext) -> List[str]:
    raw = blueprint.get("scenarios") or blueprint.get("done_whens") or []
    out: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("done_when") or item.get("name") or "").strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text)
    if out:
        return out
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        packets = []
    for p in reversed(packets or []):
        if getattr(p, "sender_role", "") != "intent_distill":
            continue
        answers = (getattr(p, "payload", None) or {}).get("answers") or {}
        scen = str(answers.get("scenarios") or "").strip()
        if scen:
            parts = re.split(r"\s*\|\s*|\n|;", scen)
            out = [x.strip() for x in parts if x.strip()]
            if out:
                return out
        break
    return [str(o).strip() for o in (ctx.objectives or []) if str(o).strip()]


_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "via", "can",
    "must", "should", "will", "when", "done", "able", "using", "a", "an", "of",
    "to", "in", "on", "or", "by", "is", "are", "be",
}



def _brief_forbids_unattend(seed_intent: str, objectives: list) -> bool:
    combined = " ".join([seed_intent or "", *map(str, objectives or [])]).lower()
    return any(
        tok in combined
        for tok in (
            "no unattend",
            "no oscdimg",
            "no iso download",
            "without unattend",
            "native hyper-v module only",
            "hyper-v module only",
        )
    )


_ALWAYS_BANNED_TOKENS = (
    "oscdimg",
    "get-service",
    "invoke-webrequest",
    "build_autounattend",
    "build_autounattend_iso",
)


def _strip_objectives_and_negatives(code: str) -> str:
    """Remove OBJECTIVES assignments and 'no <token>' phrases so constraints are not bleed."""
    text = code or ""
    text = re.sub(r"OBJECTIVES\s*(?::\s*List\[str\])?\s*=\s*\[[\s\S]*?\]", " ", text)
    text = re.sub(
        r"\bno\s+(?:unattend|oscdimg|iso\s+download|get-service|imapi2(?:fs)?)\b[^\n.]*",
        " ",
        text,
        flags=re.I,
    )
    return text


def _action_branches_in_code(code: str) -> List[str]:
    """Exclusive action == branches only (ignore status/list compound membership)."""
    found: List[str] = []
    for m in re.finditer(r"(?:if|elif)\s+action\s*==\s*['\"]([a-z_]+)['\"]", code or ""):
        found.append(m.group(1))
    return found


def _out_of_focus_actions(code: str, allowed: set) -> List[str]:
    """Return action names that are clearly out of focus.

    `if action in ("status", "list")` is allowed when any member is allowed.
    Exclusive `elif action == "create"` is forbidden when create not allowed.
    """
    hits: List[str] = []
    for m in re.finditer(r"action\s+in\s*\(([^)]*)\)", code or ""):
        acts = set(re.findall(r"['\"]([a-z_]+)['\"]", m.group(1)))
        if acts and not acts.intersection(allowed):
            for a in sorted(acts - allowed):
                hits.append(a)
    for a in _action_branches_in_code(code):
        if a in ("status",):
            continue
        if allowed and a not in allowed:
            hits.append(a)
    # de-dupe
    out: List[str] = []
    for h in hits:
        if h not in out:
            out.append(h)
    return out


def _focus_from_tool_code(code: str, path: str, brief_focuses: set) -> str:
    m = re.search(r"""FOCUS\s*=\s*['\"]([a-z_]+)['\"]""", code or "")
    if m:
        return m.group(1)
    low = (path or "").replace("\\", "/").lower()
    if "network" in low:
        return "network"
    if "unattend" in low:
        return "unattend"
    if "template" in low:
        return "template"
    if "checkpoint" in brief_focuses:
        return "checkpoint"
    if "vm" in brief_focuses:
        return "vm"
    if brief_focuses:
        return sorted(brief_focuses)[0]
    return "full"


def _forbidden_bleed(
    files_map: Dict[str, str],
    seed_intent: str,
    objectives: list,
    agent_id: str = "hyperv",
) -> List[str]:
    """Return forbidden capability tokens / out-of-focus action branches in tool code."""
    from src.application.orchestration.tool_synthesizer import ToolSynthesizer

    if not ToolSynthesizer.is_hyperv_domain(agent_id or "hyperv", seed_intent, objectives):
        return []

    focuses = hyperv_focus_from_brief(agent_id or "hyperv", seed_intent, objectives)
    # Always enforce focus gates for Hyper-V briefs; also when brief explicitly forbids unattend.
    if not focuses and not _brief_forbids_unattend(seed_intent, objectives):
        return []

    hits: List[str] = []
    for path, code in (files_map or {}).items():
        norm = str(path).replace("\\", "/").lower()
        if not (norm.endswith(".py") or norm.endswith(".ps1")):
            continue
        if "tools/" not in norm and not norm.startswith("tools/"):
            continue
        cleaned = _strip_comments(str(code or ""), norm)
        cleaned = _strip_objectives_and_negatives(cleaned)
        focus = _focus_from_tool_code(str(code or ""), norm, focuses)
        allowed = set(ACTIONS.get(focus, ACTIONS.get("full", [])))
        # Only .py action branches (PS1 ValidateSet/switch false-positives are noisy).
        if norm.endswith(".py"):
            for branch in _out_of_focus_actions(cleaned, allowed):
                hits.append(f"action:{branch}")
        low = cleaned.lower()
        # Executable banned tokens (after scrubbing negative phrases / OBJECTIVES)
        for token in _ALWAYS_BANNED_TOKENS:
            if token in low:
                # For focuses that allow unattend actions, skip those action names.
                if focus in ("unattend", "full", "template") and token.startswith("build_autounattend"):
                    continue
                if focus not in ("unattend", "full") or token in ("oscdimg", "get-service", "invoke-webrequest"):
                    if token.startswith("build_autounattend") and focus in ("unattend", "full"):
                        continue
                    hits.append(token)
        # Cross-focus cmdlet bleed
        if focus in ("checkpoint", "network", "vm") and "new-vmswitch" in low and focus != "network":
            hits.append("New-VMSwitch")
        if focus in ("checkpoint", "network") and "checkpoint-vm" in low and focus == "network":
            hits.append("Checkpoint-VM")
        if focus == "checkpoint" and re.search(r"(?<![a-z])new-vm(?!snapshot|switch)", low):
            hits.append("New-VM")

    # de-dupe preserve order
    out: List[str] = []
    for h in hits:
        if h not in out:
            out.append(h)
    return out

def _scenario_covered(scenario: str, files_map: Dict[str, str]) -> bool:
    """Coverage against tool code only when cmdlets required; full corpus for natural language."""
    corpus = _tool_code_corpus(files_map)
    if not scenario:
        return False
    cmdlets = _required_cmdlets(scenario)
    if cmdlets:
        if not corpus:
            return False
        for cmd in cmdlets:
            # Accept Hyper-V\Cmdlet or bare Cmdlet in tool sources
            if cmd not in corpus and f"hyper-v\\{cmd}" not in corpus:
                return False
        return True
    text = scenario.lower()
    text_clean = re.sub(r"^(?:operator achieves:|done-when:|done when:)\s*", "", text).strip()
    if text in corpus or (text_clean and text_clean in corpus):
        return True
    # Check full corpus including skills for high-level done-when prose
    full_corpus = corpus
    for p, c in (files_map or {}).items():
        if str(p).replace("\\", "/").endswith(".md"):
            full_corpus += "\n" + str(c or "").lower()
    if text in full_corpus or (text_clean and text_clean in full_corpus):
        return True
    tokens = [t for t in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text_clean or text) if t not in _STOP]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in full_corpus)
    return hits >= max(2, (len(tokens) + 1) // 2)


def _persist_rinse_fields(ctx: PhaseContext, **fields: Any) -> None:
    job = ctx.job
    for k, v in fields.items():
        setattr(job, k, v)
    try:
        ctx.repo.update_job_status(
            job.id,
            job.status if job.status in ("queued", "running") else "running",
            **fields,
        )
    except TypeError:
        try:
            ctx.repo.save_job(job)
        except Exception:
            pass
    except Exception:
        try:
            ctx.repo.save_job(job)
        except Exception:
            pass


class ScenarioVerifyPhase:
    id = PHASE_SCENARIO_VERIFY
    label = "Scenario Verify"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        blueprint = _latest_blueprint(ctx)
        scenarios = _scenario_list(blueprint, ctx)
        files_map = _latest_author_files(ctx)

        missing: List[str] = []
        for scen in scenarios:
            if not _scenario_covered(scen, files_map):
                missing.append(scen)

        forbidden = _forbidden_bleed(
            files_map,
            job.seed_intent,
            list(ctx.objectives or job.objectives or []),
            agent_id=job.target_agent_id,
        )
        if forbidden:
            missing.append(
                "FORBIDDEN_BLEED: tool code contains " + ", ".join(forbidden)
                + " (out of focus / forbidden capability)"
            )

        from src.application.orchestration.tool_synthesizer import ToolSynthesizer

        if ToolSynthesizer.is_hyperv_domain(
            job.target_agent_id, job.seed_intent, list(ctx.objectives or job.objectives or [])
        ):
            focuses = hyperv_focus_from_brief(
                job.target_agent_id, job.seed_intent, list(ctx.objectives or job.objectives or [])
            )
            brief_l = f"{job.seed_intent} {' '.join(map(str, ctx.objectives or job.objectives or []))}".lower()
            if "checkpoint cmdlets only" in brief_l or (
                "checkpoint" in focuses and ("no network" in brief_l or "no networking" in brief_l or "no virtual switch" in brief_l)
            ):
                focuses = {"checkpoint"}
            if focuses:
                allowed_tool_frags = set()
                if "checkpoint" in focuses or "vm" in focuses:
                    allowed_tool_frags.add("manage_hyperv_vm")
                if "network" in focuses:
                    allowed_tool_frags.add("manage_hyperv_network")
                if "unattend" in focuses:
                    allowed_tool_frags.add("manage_hyperv_unattend")
                if "template" in focuses:
                    allowed_tool_frags.add("manage_hyperv_template")
                if allowed_tool_frags:
                    for path in files_map or {}:
                        norm = str(path).replace("\\", "/").lower()
                        if "/tools/" in f"/{norm}" or norm.startswith("tools/"):
                            if not any(frag in norm for frag in allowed_tool_frags):
                                missing.append(
                                    f"OUT_OF_SCOPE_FILES: {path} not permitted for focuses {sorted(focuses)}"
                                )

        passed = len(missing) == 0
        rinse_count = int(getattr(job, "verify_rinse_count", 0) or 0)
        max_rinses = int(getattr(job, "max_verify_rinses", 3) or 3)
        outer_count = int(getattr(job, "outer_rinse_count", 0) or 0)
        max_outer = int(getattr(job, "max_outer_rinses", 2) or 2)

        if passed:
            message = (
                f"Scenario Verify PASSED ({len(scenarios)} scenario(s) covered)."
                if scenarios
                else "Scenario Verify PASSED (no scenarios claimed)."
            )
            packet = FactoryPacket(
                job_id=job.id,
                packet_type="eval",
                sender_role="scenario_verify",
                recipient_role="verify",
                node_id=PHASE_SCENARIO_VERIFY,
                payload={
                    "message": message,
                    "passed": True,
                    "scenarios": scenarios,
                    "missing_scenarios": [],
                    "phase": PHASE_SCENARIO_VERIFY,
                    "rinse_kind": None,
                },
            )
            ctx.repo.save_packet(packet)
            return PhaseResult(
                outcome="ok",
                message=message,
                artifacts={
                    "passed": True,
                    "scenarios": scenarios,
                    "missing_scenarios": [],
                    "files_map": files_map,
                },
            )

        critic_notes = "Scenario Verify FAILED: missing coverage for: " + "; ".join(missing)
        fclass = classify_failure(critic_notes, scenario_misses=missing)
        outcome = decide_rinse_outcome(
            failure_class=fclass,
            verify_rinse_count=rinse_count,
            max_verify_rinses=max_rinses,
            outer_rinse_count=outer_count,
            max_outer_rinses=max_outer,
        )

        updates: Dict[str, Any] = {"failure_class": fclass}
        rinse_kind = "inner"
        recipient = "author"
        terminal = False
        if outcome == "outer":
            outer_count += 1
            updates["outer_rinse_count"] = outer_count
            rinse_kind = "outer"
            recipient = "intent_distill"
            updates["verify_rinse_count"] = 0
            rinse_count = 0
        elif outcome == "fail":
            rinse_count += 1
            updates["verify_rinse_count"] = rinse_count
            rinse_kind = "inner"
            recipient = "author"
        else:
            terminal = True
            if fclass == "sop_how":
                outer_count += 1
                updates["outer_rinse_count"] = outer_count
                rinse_kind = "outer"
            else:
                rinse_count += 1
                updates["verify_rinse_count"] = rinse_count
                rinse_kind = "inner"
            recipient = "orchestrator"

        _persist_rinse_fields(ctx, **updates)

        short = critic_notes if len(critic_notes) <= 180 else critic_notes[:177] + "..."
        if terminal:
            message = (
                f"Scenario Verify FAILED - {rinse_kind} rinse exhausted "
                f"(outer {outer_count}/{max_outer}, inner {rinse_count}/{max_rinses}). "
                f"Reason: {short}"
            )
        elif rinse_kind == "outer":
            message = (
                f"Scenario Verify FAILED - outer rinse ({outer_count}/{max_outer}) "
                f"[{fclass}]. Reason: {short}"
            )
        else:
            message = (
                f"Scenario Verify FAILED - inner rinse ({rinse_count}/{max_rinses}) "
                f"[{fclass}]. Reason: {short}"
            )

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="eval",
            sender_role="scenario_verify",
            recipient_role=recipient,
            node_id=PHASE_SCENARIO_VERIFY,
            payload={
                "message": message,
                "passed": False,
                "scenarios": scenarios,
                "missing_scenarios": missing,
                "critic_notes": critic_notes,
                "failure_class": fclass,
                "rinse_kind": rinse_kind,
                "verify_rinse_count": rinse_count,
                "max_verify_rinses": max_rinses,
                "outer_rinse_count": outer_count,
                "max_outer_rinses": max_outer,
                "terminal_fail": terminal,
                "phase": PHASE_SCENARIO_VERIFY,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome=outcome,
            message=message,
            artifacts={
                "passed": False,
                "missing_scenarios": missing,
                "scenarios": scenarios,
                "critic_notes": critic_notes,
                "failure_class": fclass,
                "rinse_kind": rinse_kind,
                "terminal_fail": terminal,
                "files_map": files_map,
            },
        )
