"""
Sandboxed Subprocess Worker [REQ-SAFE-002].
Executes subprocesses and Python scripts within an isolated ephemeral temporary directory.
"""

import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SubprocessResult:
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    error: Optional[str] = None


class SandboxedSubprocessWorker:
    """Runs commands in an isolated temporary working directory with resource limits."""

    @classmethod
    async def run_sandboxed(
        cls,
        args: List[str],
        timeout_seconds: float = 30.0,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> SubprocessResult:
        """Execute command inside a fresh TemporaryDirectory."""
        temp_dir = tempfile.mkdtemp(prefix="autoreiv_sandbox_")
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=env,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = proc.returncode if proc.returncode is not None else -1
                return SubprocessResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    success=(exit_code == 0),
                    error=stderr if exit_code != 0 else None,
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
                )
        except Exception as e:
            return SubprocessResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
                error=f"Subprocess launch error: {e}",
            )
        finally:
            # Clean up temp directory safely
            try:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    @classmethod
    async def run_python_code(
        cls,
        code: str,
        timeout_seconds: float = 30.0,
    ) -> SubprocessResult:
        """Execute inline Python code in the sandbox."""
        return await cls.run_sandboxed(
            [sys.executable, "-c", code],
            timeout_seconds=timeout_seconds,
        )
