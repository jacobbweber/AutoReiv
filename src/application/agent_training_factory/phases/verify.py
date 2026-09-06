"""Verify phase: run verification battery; fail rinses to Author (CARD-171)."""

from __future__ import annotations

from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_VERIFY
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.application.orchestration.verification_battery import (
    VerificationBatteryService,
)
from src.domain.orchestration.factory_packets import FactoryEvalRun, FactoryPacket


class VerifyPhase:
    id = PHASE_VERIFY
    label = "Verify"

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
            _ = tool_names
        if not tool_code or not skill_content:
            syn = ToolSynthesizer.synthesize_tool(
                agent_id=job.target_agent_id,
                seed_intent=job.seed_intent,
                objectives=list(ctx.objectives),
                tool_name=tool_name,
            )
            tool_code = tool_code or syn.get(f"tools/{tool_name}.py", "")
            skill_content = skill_content or syn.get(f"skills/{clean_slug}/SKILL.md", "")
            files_map = {**syn, **files_map}

        battery = ctx.battery or VerificationBatteryService()
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
            tool_name=tool_name,
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
        terminal_fail = False
        outcome = "ok"
        recipient = "optimize"

        if passed:
            message = f"Verify battery PASSED for {tool_name}."
        else:
            rinse_count += 1
            terminal_fail = rinse_count >= max_rinses
            short_reason = critic_notes.strip().replace("\n", " ")
            if len(short_reason) > 180:
                short_reason = short_reason[:177] + "..."
            if terminal_fail:
                outcome = "exhausted"
                recipient = "orchestrator"
                message = (
                    f"Verify battery FAILED ({rinse_count}/{max_rinses}) for {tool_name}; "
                    f"max rinses reached - job failed. Reason: {short_reason}"
                )
            else:
                outcome = "fail"
                recipient = "author"
                message = (
                    f"Verify battery FAILED ({rinse_count}/{max_rinses}) for {tool_name}. "
                    f"Reason: {short_reason}"
                )
            try:
                ctx.repo.update_job_status(
                    job.id,
                    job.status if job.status in ("queued", "running") else "running",
                    verify_rinse_count=rinse_count,
                )
                job.verify_rinse_count = rinse_count
            except TypeError:
                job.verify_rinse_count = rinse_count
                ctx.repo.save_job(job)
            except Exception:
                job.verify_rinse_count = rinse_count
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
                "terminal_fail": terminal_fail,
            },
        )
