"""Verify phase: code verification battery; inner/outer rinse (CARD-171/172)."""

from __future__ import annotations

from src.application.agent_training_factory.failure_class import (
    classify_failure,
    decide_rinse_outcome,
)
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_VERIFY
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.application.orchestration.verification_battery import (
    VerificationBatteryService,
)
from src.domain.orchestration.factory_packets import FactoryEvalRun, FactoryPacket


class VerifyPhase:
    id = PHASE_VERIFY
    label = "Code Verify"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        clean_slug = job.target_agent_id.replace("-", "_").lower()
        tool_name = f"manage_{clean_slug}"

        packets = ctx.repo.list_packets(job.id)
        author_pkts = [
            p
            for p in packets
            if p.sender_role in ("author", "coder")
            or p.node_id in (PHASE_AUTHOR, "coder_node")
        ]
        tool_code = ""
        skill_content = ""
        files_map = {}
        if author_pkts and author_pkts[-1].payload:
            payload = author_pkts[-1].payload
            files_map = payload.get("files_map", {}) or {}
            tool_name = payload.get("tool_name", tool_name)
            tool_names = list(payload.get("tool_names") or []) or [tool_name]
            exact_tool_key = f"tools/{tool_name}.py"
            if exact_tool_key in files_map:
                tool_code = files_map[exact_tool_key]
            else:
                for fpath, code in files_map.items():
                    norm = fpath.replace("\\", "/")
                    if norm.endswith(f"/{tool_name}.py") or norm == exact_tool_key:
                        tool_code = code
                        break
            skill_candidates = []
            for fpath, code in files_map.items():
                norm = fpath.replace("\\", "/")
                if norm.endswith("SKILL.md") and "skills/" in norm:
                    skill_candidates.append((norm, code))
            for _norm, code in skill_candidates:
                if tool_name.lower() in (code or "").lower():
                    skill_content = code
                    break
            if not skill_content and skill_candidates:
                skill_content = skill_candidates[0][1]
        has_mcp_server = "mcp/server.py" in files_map
        is_skill_only = (
            getattr(job, "deliverable_type", "") == "skill"
            or (
                author_pkts
                and author_pkts[-1].payload
                and author_pkts[-1].payload.get("deliverable_type") == "skill"
            )
            or (
                not has_mcp_server
                and not any(k.startswith("tools/") for k in files_map)
                and any(k.startswith("skills/") for k in files_map)
            )
        )

        if not is_skill_only:
            if not has_mcp_server and (not tool_code or not skill_content):
                syn = ToolSynthesizer.synthesize_tool(
                    agent_id=job.target_agent_id,
                    seed_intent=job.seed_intent,
                    objectives=list(ctx.objectives),
                    tool_name=tool_name,
                )
                tool_code = tool_code or syn.get(f"tools/{tool_name}.py", "")
                skill_content = skill_content or syn.get(f"skills/{clean_slug}/SKILL.md", "")
                files_map = {**syn, **files_map}
            elif has_mcp_server and not skill_content:
                syn = ToolSynthesizer.synthesize_tool(
                    agent_id=job.target_agent_id,
                    seed_intent=job.seed_intent,
                    objectives=list(ctx.objectives),
                    tool_name=tool_name,
                )
                skill_content = syn.get(f"skills/{clean_slug}/SKILL.md", "")
                for sk_k, sk_v in syn.items():
                    if sk_k.startswith("skills/"):
                        files_map.setdefault(sk_k, sk_v)

        if has_mcp_server:
            files_map = {k: v for k, v in files_map.items() if not k.startswith("tools/") and "/tools/" not in k.replace("\\", "/")}

        battery = ctx.battery or VerificationBatteryService()
        active_tool_names = (
            locals().get("tool_names")
            or (author_pkts[-1].payload.get("tool_names") if author_pkts and author_pkts[-1].payload else None)
            or ([tool_name] if not is_skill_only else [])
        )
        if is_skill_only:
            from src.domain.orchestration.factory_packets import EvalPacket

            skill_errors = []
            for sk_path, sk_text in skill_candidates:
                low = (sk_text or "").lower()
                if "---" not in (sk_text or ""):
                    skill_errors.append(f"{sk_path}: missing YAML frontmatter")
                if "## purpose" not in low:
                    skill_errors.append(f"{sk_path}: missing Purpose section")
                if "objective" not in low:
                    skill_errors.append(f"{sk_path}: missing Objectives section")
                if "standard operating procedure" not in low:
                    skill_errors.append(f"{sk_path}: missing SOP section")

            passed_eval = len(skill_errors) == 0
            eval_pkt = EvalPacket(
                passed=passed_eval,
                stage_1_functional=passed_eval,
                stage_2_safety=True,
                stage_3_idempotency=True,
                stage_4_critic=passed_eval,
                critic_notes="; ".join(skill_errors) if skill_errors else "All procedural skill runbooks validated.",
                duration_ms=10.0,
            )
        elif has_mcp_server:
            eval_pkt = await battery.run_mcp_battery(
                server_code=files_map["mcp/server.py"],
                expected_tools=active_tool_names,
                tool_code=tool_code,
                skill_content=skill_content,
                seed_intent=job.seed_intent or "",
                objectives=list(ctx.objectives),
                extra_files=files_map,
                repeats=3,
            )
        else:
            test_code = ToolSynthesizer.generate_verification_test(tool_name)
            eval_pkt = await battery.run_battery(
                tool_code=tool_code,
                test_code=test_code,
                skill_content=skill_content,
                repeats=3,
                seed_intent=job.seed_intent or "",
                objectives=list(ctx.objectives),
            )

        eval_run = FactoryEvalRun(
            job_id=job.id,
            tool_name="procedural_skills" if is_skill_only else (f"{tool_name}_mcp" if has_mcp_server else tool_name),
            stage_1_functional=eval_pkt.stage_1_functional,
            stage_2_safety=eval_pkt.stage_2_safety,
            stage_3_idempotency=eval_pkt.stage_3_idempotency,
            stage_4_critic=eval_pkt.stage_4_critic,
            stdout_log=eval_pkt.stdout,
            stderr_log=eval_pkt.stderr,
            critic_notes=getattr(eval_pkt, "critic_notes", "") or "",
            duration_ms=eval_pkt.duration_ms,
            overall_passed=bool(eval_pkt.passed),
        )
        ctx.repo.save_eval_run(eval_run)

        passed = bool(eval_pkt.passed)
        critic_notes = getattr(eval_pkt, "critic_notes", "") or ""
        rinse_count = int(getattr(job, "verify_rinse_count", 0) or 0)
        max_rinses = int(getattr(job, "max_verify_rinses", 3) or 3)
        outer_count = int(getattr(job, "outer_rinse_count", 0) or 0)
        max_outer = int(getattr(job, "max_outer_rinses", 2) or 2)
        terminal_fail = False
        outcome = "ok"
        recipient = "optimize"
        failure_class = None
        rinse_kind = None

        tools_summary = ", ".join(active_tool_names) if active_tool_names else tool_name
        if passed:
            if is_skill_only:
                message = f"Verify battery PASSED for {len(skill_candidates)} procedural skill runbook(s)."
            elif has_mcp_server:
                message = f"Verify battery PASSED for {tools_summary} (MCP Server deliverable)."
            else:
                message = f"Verify battery PASSED for {tools_summary}."

        else:
            failure_class = classify_failure(critic_notes)
            outcome = decide_rinse_outcome(
                failure_class=failure_class,
                verify_rinse_count=rinse_count,
                max_verify_rinses=max_rinses,
                outer_rinse_count=outer_count,
                max_outer_rinses=max_outer,
            )
            updates = {"failure_class": failure_class}
            if outcome == "outer":
                outer_count += 1
                updates["outer_rinse_count"] = outer_count
                updates["verify_rinse_count"] = 0
                rinse_count = 0
                rinse_kind = "outer"
                recipient = "intent_distill"
            elif outcome == "fail":
                rinse_count += 1
                updates["verify_rinse_count"] = rinse_count
                rinse_kind = "inner"
                recipient = "author"
            else:
                terminal_fail = True
                if failure_class == "sop_how":
                    outer_count += 1
                    updates["outer_rinse_count"] = outer_count
                    rinse_kind = "outer"
                else:
                    rinse_count += 1
                    updates["verify_rinse_count"] = rinse_count
                    rinse_kind = "inner"
                recipient = "orchestrator"

            short_reason = critic_notes.strip().replace("\n", " ")
            if len(short_reason) > 180:
                short_reason = short_reason[:177] + "..."
            if terminal_fail:
                message = (
                    f"Verify battery FAILED - {rinse_kind} rinse exhausted for {tool_name} "
                    f"(outer {outer_count}/{max_outer}, inner {rinse_count}/{max_rinses}). "
                    f"Reason: {short_reason}"
                )
            elif rinse_kind == "outer":
                message = (
                    f"Verify battery FAILED - outer rinse ({outer_count}/{max_outer}) for {tool_name} "
                    f"[{failure_class}]. Reason: {short_reason}"
                )
            else:
                message = (
                    f"Verify battery FAILED - inner rinse ({rinse_count}/{max_rinses}) for {tool_name} "
                    f"[{failure_class}]. Reason: {short_reason}"
                )

            for k, v in updates.items():
                setattr(job, k, v)
            try:
                ctx.repo.update_job_status(
                    job.id,
                    job.status if job.status in ("queued", "running") else "running",
                    **{
                        k: v
                        for k, v in updates.items()
                        if k
                        in (
                            "verify_rinse_count",
                            "max_verify_rinses",
                            "outer_rinse_count",
                            "max_outer_rinses",
                            "failure_class",
                        )
                    },
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

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="eval",
            sender_role="verify",
            recipient_role=recipient,
            node_id=PHASE_VERIFY,
            payload={
                "message": message,
                "passed": passed,
                "stages": [
                    "stage_1_functional",
                    "stage_2_safety",
                    "stage_3_idempotency",
                    "stage_4_critic",
                ],
                "tool_name": tool_name,
                "files_map": files_map,
                "critic_notes": critic_notes,
                "verify_rinse_count": rinse_count,
                "max_verify_rinses": max_rinses,
                "outer_rinse_count": outer_count,
                "max_outer_rinses": max_outer,
                "failure_class": failure_class,
                "rinse_kind": rinse_kind,
                "terminal_fail": terminal_fail,
                "phase": PHASE_VERIFY,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome=outcome,
            message=packet.payload["message"],
            artifacts={
                "passed": passed,
                "tool_name": tool_name,
                "files_map": files_map,
                "critic_notes": critic_notes,
                "verify_rinse_count": rinse_count,
                "outer_rinse_count": outer_count,
                "failure_class": failure_class,
                "rinse_kind": rinse_kind,
                "terminal_fail": terminal_fail,
            },
        )
