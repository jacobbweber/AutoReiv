"""
Isolated Sandbox Test Runner for Factory Capability Loop [REQ-FACT-008].

Executes newly authored Python tools against isolated sandbox mocks, directory mirrors,
and multi-stage verification harnesses with strict credential scrubbing and timeout enforcement.
"""

import sys
from typing import Dict, Optional

from src.application.skills.sandbox_worker import SandboxedSubprocessWorker, SubprocessResult


class SandboxTestRunner:
    """
    Executes newly authored Python tools against sandbox mocks and verification test harnesses.
    """

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout

    async def run_tool_test(
        self,
        tool_code: str,
        test_code: str,
        mirror_dir: Optional[str] = None,
        mock_files: Optional[Dict[str, str]] = None,
        stubs: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[float] = None,
        workspace_dir: Optional[str] = None,
    ) -> SubprocessResult:
        """
        Provisions tool.py and test_runner.py inside an ephemeral sandbox,
        mirrors target directory if provided, scrubs host credentials, and executes
        python test_runner.py with timeout and memory guards.
        """
        files = {
            "tool.py": tool_code,
            "test_runner.py": test_code,
        }
        if mock_files:
            files.update(mock_files)

        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout
        args = [sys.executable, "test_runner.py"]

        return await SandboxedSubprocessWorker.run_sandboxed(
            args=args,
            timeout_seconds=timeout,
            files=files,
            mirror_dir=mirror_dir,
            stubs=stubs,
            workspace_dir=workspace_dir,
        )
