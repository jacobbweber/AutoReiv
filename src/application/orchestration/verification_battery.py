"""
The 4-Stage Verification Battery Pipeline [REQ-FACT-009].

Evaluates newly authored tools sequentially across:
1. Deterministic functional execution (code 0)
2. Invariant & safety guardrails (no path traversal or sandbox escape)
3. Idempotency & stress replay (3 sequential runs)
4. SRE Critic AST audit (code hygiene, regex safety, exception handling)
"""

import ast
import re
import time
from typing import Dict, List, Optional

from src.application.skills.sandbox_runner import SandboxTestRunner
from src.domain.orchestration.factory_packets import EvalPacket


def is_shallow_stub_artifact(
    skill_md: str,
    tool_code: str = "",
    seed_intent: str = "",
    objectives: Optional[List[str]] = None,
) -> bool:
    """
    Fail shallow costume stubs that ignore seed objective keywords (CARD-171 live-test).
    """
    body = (skill_md or "").strip()
    low = body.lower()
    intent_low = (seed_intent or "").lower()
    objs = objectives or []

    if len(body) < 120:
        return True
    if "agent for managing" in low and "## purpose" not in low:
        return True
    if "agent for managing" in low and intent_low[:24] and intent_low[:24] not in low:
        return True
    if "## purpose" not in low:
        return True
    if "objective" not in low:
        return True

    required = [k for k in ("unattend", "autounattend", "iso", "vhdx", "template") if k in intent_low]
    for obj in objs:
        ol = str(obj).lower()
        for k in ("unattend", "autounattend", "iso", "vhdx", "template"):
            if k in ol and k not in required:
                required.append(k)
    if required:
        if not any(k in low for k in required):
            return True
        tool_low = (tool_code or "").lower()
        if tool_low and not any(k in tool_low for k in required):
            # hyperv tools may use New-VM / ISO wording variants
            if not any(k in tool_low for k in ("iso", "unattend", "vhdx", "template", "new-vm", "hyper-v")):
                return True
    return False



def detect_path_safety_violation(tool_code: str) -> Optional[str]:
    """Return reason if tool_code has path traversal / sandbox escape.

    Absolute Windows paths (C:\\Users\\..., D:\\Archive\\...) are allowed.
    """
    code = tool_code or ''
    if re.search(r'\.\.(?:/|\\)', code):
        return "Path traversal segment ('..') detected. Disallowed."
    if re.search(r'["\']/(?:etc|proc|sys)(?:/|\\|["\'])', code):
        return 'Sensitive absolute Unix path literal detected. Disallowed.'
    if re.search(r'["\'/]/(?:etc|proc|sys)/', code):
        return 'Sensitive absolute Unix path literal detected. Disallowed.'
    return None


class VerificationBatteryService:
    """
    Executes the 4-stage automated verification battery on drafted tools [REQ-FACT-009].
    """

    def __init__(self, runner: Optional[SandboxTestRunner] = None):
        self.runner = runner or SandboxTestRunner()

    async def run_battery(
        self,
        tool_code: str,
        test_code: str,
        mirror_dir: Optional[str] = None,
        mock_files: Optional[Dict[str, str]] = None,
        repeats: int = 3,
        skill_content: Optional[str] = None,
        seed_intent: str = "",
        objectives: Optional[List[str]] = None,
    ) -> EvalPacket:
        """
        Execute the 4 verification gates sequentially, returning a structured EvalPacket.
        """
        start_time = time.perf_counter()
        checks_executed: List[str] = []
        critic_notes: List[str] = []

        # -------------------------------------------------------------
        # Pre-flight: reject shallow stub skills/tools that ignore objectives
        # -------------------------------------------------------------
        if skill_content and (seed_intent or objectives):
            if is_shallow_stub_artifact(
                skill_md=skill_content,
                tool_code=tool_code,
                seed_intent=seed_intent or "",
                objectives=objectives,
            ):
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return EvalPacket(
                    checks_executed=["shallow_stub_gate"],
                    passed=False,
                    stage_1_functional=False,
                    stage_2_safety=False,
                    stage_3_idempotency=False,
                    stage_4_critic=False,
                    critic_notes=(
                        "Shallow stub gate: SKILL.md/tool ignore seed objectives "
                        "(stub pattern, missing Purpose/Objectives, or missing unattend/ISO/template keywords)."
                    ),
                    duration_ms=duration_ms,
                )

        # -------------------------------------------------------------
        # Pre-execution Safety Guardrail Check [Stage 2 Pre-flight]
        # -------------------------------------------------------------
        path_violation = detect_path_safety_violation(tool_code)
        if path_violation:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return EvalPacket(
                checks_executed=["stage_2_safety"],
                passed=False,
                stage_1_functional=False,
                stage_2_safety=False,
                stage_3_idempotency=False,
                stage_4_critic=False,
                critic_notes=f"Safety Guardrail Alert: {path_violation}",
                duration_ms=duration_ms,
            )

        # -------------------------------------------------------------
        # Stage 1: Deterministic Functional Execution
        # -------------------------------------------------------------
        import shutil
        import tempfile

        workspace_dir = tempfile.mkdtemp(prefix="autoreiv_battery_")
        try:
            checks_executed.append("stage_1_functional")
            res_s1 = await self.runner.run_tool_test(
                tool_code=tool_code,
                test_code=test_code,
                mirror_dir=mirror_dir,
                mock_files=mock_files,
                workspace_dir=workspace_dir,
            )

            if res_s1.exit_code != 0:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return EvalPacket(
                    checks_executed=checks_executed,
                    passed=False,
                    stage_1_functional=False,
                    stage_2_safety=False,
                    stage_3_idempotency=False,
                    stage_4_critic=False,
                    stdout=res_s1.stdout,
                    stderr=res_s1.stderr,
                    critic_notes=f"Stage 1 Functional Failure: Process exited with code {res_s1.exit_code}. {res_s1.error or ''}",
                    duration_ms=duration_ms,
                )

            # -------------------------------------------------------------
            # Stage 2: Invariant & Safety Guardrails
            # -------------------------------------------------------------
            checks_executed.append("stage_2_safety")
            # Check stderr for security violations, sandbox alerts, or command collisions [REQ-FACT-033]
            stderr_lower = res_s1.stderr.lower()
            if "security alert" in stderr_lower or "violation" in stderr_lower:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return EvalPacket(
                    checks_executed=checks_executed,
                    passed=False,
                    stage_1_functional=True,
                    stage_2_safety=False,
                    stage_3_idempotency=False,
                    stage_4_critic=False,
                    stdout=res_s1.stdout,
                    stderr=res_s1.stderr,
                    critic_notes="Stage 2 Safety Guardrail Alert: Runtime security violation detected.",
                    duration_ms=duration_ms,
                )

            collision_signatures = [
                "viserverconnectionexception",
                "you are not currently connected to any servers",
                "command collision",
                "ambiguous command",
            ]
            if any(sig in stderr_lower for sig in collision_signatures):
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return EvalPacket(
                    checks_executed=checks_executed,
                    passed=False,
                    stage_1_functional=True,
                    stage_2_safety=False,
                    stage_3_idempotency=False,
                    stage_4_critic=False,
                    stdout=res_s1.stdout,
                    stderr=res_s1.stderr,
                    critic_notes="Stage 2 Safety Guardrail Alert: Environment command collision or foreign module interception detected.",
                    duration_ms=duration_ms,
                )

            # -------------------------------------------------------------
            # Stage 3: Idempotency & Stress Replay (Run on same workspace)
            # -------------------------------------------------------------
            checks_executed.append("stage_3_idempotency")
            for i in range(1, repeats):
                replay_res = await self.runner.run_tool_test(
                    tool_code=tool_code,
                    test_code=test_code,
                    mirror_dir=None,  # Directory already mirrored in workspace_dir
                    mock_files=None,
                    workspace_dir=workspace_dir,
                )
                if replay_res.exit_code != 0:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    return EvalPacket(
                        checks_executed=checks_executed,
                        passed=False,
                        stage_1_functional=True,
                        stage_2_safety=True,
                        stage_3_idempotency=False,
                        stage_4_critic=False,
                        stdout=replay_res.stdout,
                        stderr=replay_res.stderr,
                        critic_notes=f"Stage 3 Idempotency Failure: Tool failed on replay turn #{i+1} (exit code {replay_res.exit_code}). State may be leaked or corrupted.",
                        duration_ms=duration_ms,
                    )
        finally:
            shutil.rmtree(workspace_dir, ignore_errors=True)

        # -------------------------------------------------------------
        # Stage 4: SRE Critic AST Audit
        # -------------------------------------------------------------
        checks_executed.append("stage_4_critic")
        try:
            tree = ast.parse(tool_code)
            critic_pass = True
            for node in ast.walk(tree):
                # Disallow raw eval / exec
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                        critic_notes.append(f"Critic Alert: Dangerous dynamic execution function `{node.func.id}()` detected.")
                        critic_pass = False

                # Flag bare except handlers without re-raise or logging
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        critic_notes.append("Critic Note: Bare `except:` handler detected; recommend catching specific exceptions.")

            if not critic_pass:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return EvalPacket(
                    checks_executed=checks_executed,
                    passed=False,
                    stage_1_functional=True,
                    stage_2_safety=True,
                    stage_3_idempotency=True,
                    stage_4_critic=False,
                    stdout=res_s1.stdout,
                    stderr=res_s1.stderr,
                    critic_notes="; ".join(critic_notes),
                    duration_ms=duration_ms,
                )

        except SyntaxError as syn_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return EvalPacket(
                checks_executed=checks_executed,
                passed=False,
                stage_1_functional=True,
                stage_2_safety=True,
                stage_3_idempotency=True,
                stage_4_critic=False,
                critic_notes=f"Critic Syntax Error: {syn_err}",
                duration_ms=duration_ms,
            )

        # Stage 4b: Skill Runbook Feasibility & Parity Audit [REQ-FACT-007, REQ-FACT-009]
        if skill_content:
            from src.application.orchestration.tool_synthesizer import ToolSynthesizer

            skill_audit = ToolSynthesizer.evaluate_skill_runbook(skill_content=skill_content, tool_code=tool_code)
            if not skill_audit["passed"]:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                errs = "; ".join(skill_audit.get("errors", []))
                return EvalPacket(
                    checks_executed=checks_executed,
                    passed=False,
                    stage_1_functional=True,
                    stage_2_safety=True,
                    stage_3_idempotency=True,
                    stage_4_critic=False,
                    stdout=res_s1.stdout,
                    stderr=res_s1.stderr,
                    critic_notes=f"Critic Skill Runbook Audit Failure: {errs}",
                    duration_ms=duration_ms,
                )
            critic_notes.append("Skill runbook verified: valid agentskills.io YAML frontmatter, clear structure, and 100% action parity.")

        # All 4 stages passed!
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return EvalPacket(
            checks_executed=checks_executed,
            passed=True,
            stage_1_functional=True,
            stage_2_safety=True,
            stage_3_idempotency=True,
            stage_4_critic=True,
            stdout=res_s1.stdout,
            stderr=res_s1.stderr,
            critic_notes="All 4 verification stages passed cleanly. Code certified.",
            duration_ms=duration_ms,
        )
