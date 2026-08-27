"""
Sandboxed Subprocess Worker [REQ-SAFE-002, REQ-SANDBOX-001, REQ-SANDBOX-002].
Executes subprocesses and scripts within an isolated ephemeral temporary directory
with sensitive environment variable scrubbing, file workspace provisioning, and stream capping.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SENSITIVE_ENV_KEYWORDS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "AUTH",
    "CREDENTIAL",
    "PRIVATE",
)

SAFE_PASSTHROUGH_ENV_KEYS = (
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "PYTHONPATH",
    "LANG",
    "LC_ALL",
    "HOME",
    "USERPROFILE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
)


@dataclass
class SubprocessResult:
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    error: Optional[str] = None
    output_files: Dict[str, str] = field(default_factory=dict)
    truncated: bool = False


class SandboxedSubprocessWorker:
    """Runs commands in an isolated temporary working directory with resource limits."""

    @classmethod
    def sanitize_environment(
        cls,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Produce a sanitized environment dict stripping sensitive host keys [REQ-SANDBOX-002].
        """
        clean_env: Dict[str, str] = {}
        for key, val in os.environ.items():
            upper_key = key.upper()
            if upper_key in SAFE_PASSTHROUGH_ENV_KEYS:
                clean_env[key] = val
            elif not any(keyword in upper_key for keyword in SENSITIVE_ENV_KEYWORDS):
                clean_env[key] = val

        if env_overrides:
            clean_env.update(env_overrides)

        return clean_env

    @classmethod
    async def run_sandboxed(
        cls,
        args: List[str],
        timeout_seconds: float = 30.0,
        env_overrides: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, str]] = None,
        read_outputs: Optional[List[str]] = None,
        max_output_bytes: int = 1_000_000,
    ) -> SubprocessResult:
        """
        Execute command inside a fresh TemporaryDirectory [REQ-SANDBOX-001, REQ-SANDBOX-002, REQ-GUARD-002].
        """
        # Security safety guardrail evaluation [REQ-GUARD-002]
        from src.application.safety.command_guardrail import CommandGuardrail

        cmd_str = " ".join(args)
        safety_report = CommandGuardrail.evaluate(cmd_str)
        if not safety_report.is_safe:
            violation = safety_report.violations[0] if safety_report.violations else None
            reason = violation.reason if violation else "Unsafe command pattern detected"
            return SubprocessResult(
                stdout="",
                stderr=f"Security Alert: Command execution blocked ({safety_report.highest_risk.value.upper()}) - {reason}",
                exit_code=-1,
                success=False,
                error=f"Security violation: {reason}",
                output_files={},
                truncated=False,
            )

        temp_dir = tempfile.mkdtemp(prefix="autoreiv_sandbox_")
        env = cls.sanitize_environment(env_overrides)
        output_files: Dict[str, str] = {}
        is_truncated = False

        try:
            # 1. Provision workspace files [REQ-SANDBOX-001]
            if files:
                for rel_path, content in files.items():
                    target_file = os.path.join(temp_dir, rel_path)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(content)

            # 2. Spawn isolated subprocess
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)

                # Cap output streams to prevent memory explosion [REQ-SANDBOX-002]
                if len(stdout_bytes) > max_output_bytes:
                    stdout_bytes = stdout_bytes[:max_output_bytes]
                    is_truncated = True
                    stdout_suffix = "\n... [stdout truncated]"
                else:
                    stdout_suffix = ""

                if len(stderr_bytes) > max_output_bytes:
                    stderr_bytes = stderr_bytes[:max_output_bytes]
                    is_truncated = True
                    stderr_suffix = "\n... [stderr truncated]"
                else:
                    stderr_suffix = ""

                stdout = stdout_bytes.decode("utf-8", errors="replace") + stdout_suffix
                stderr = stderr_bytes.decode("utf-8", errors="replace") + stderr_suffix
                exit_code = proc.returncode if proc.returncode is not None else -1

                # 3. Read requested output artifacts [REQ-SANDBOX-001]
                if read_outputs:
                    for out_rel in read_outputs:
                        out_path = os.path.join(temp_dir, out_rel)
                        if os.path.isfile(out_path):
                            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                                output_files[out_rel] = f.read()

                return SubprocessResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    success=(exit_code == 0),
                    error=stderr if exit_code != 0 else None,
                    output_files=output_files,
                    truncated=is_truncated,
                )

            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                return SubprocessResult(
                    stdout="",
                    stderr="Execution timed out",
                    exit_code=-1,
                    success=False,
                    error=f"Process timed out after {timeout_seconds} seconds.",
                    output_files={},
                    truncated=False,
                )

        except Exception as e:
            return SubprocessResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
                error=f"Subprocess launch error: {e}",
                output_files={},
                truncated=False,
            )

        finally:
            # Hermetically clean up temp directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    @classmethod
    async def run_python_code(
        cls,
        code: str,
        timeout_seconds: float = 30.0,
        files: Optional[Dict[str, str]] = None,
        read_outputs: Optional[List[str]] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> SubprocessResult:
        """Execute inline Python code in the sandbox [REQ-SANDBOX-001]."""
        return await cls.run_sandboxed(
            [sys.executable, "-c", code],
            timeout_seconds=timeout_seconds,
            files=files,
            read_outputs=read_outputs,
            env_overrides=env_overrides,
        )
