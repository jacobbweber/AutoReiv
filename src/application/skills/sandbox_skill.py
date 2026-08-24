"""
Sandbox Execution Skill [REQ-SANDBOX-003].
Exposes agent tools to execute Python and shell scripts inside an isolated ephemeral subprocess sandbox.
"""

from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sandbox_worker import SandboxedSubprocessWorker
from src.domain.gateway.models import ToolDefinition


class SandboxExecutionSkill:
    """Agent skill providing safe, isolated code execution inside an ephemeral subprocess sandbox."""

    def __init__(self, default_timeout_seconds: float = 30.0):
        self.default_timeout_seconds = default_timeout_seconds

    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Return the JSON schema tool definitions for agent discovery [REQ-SANDBOX-003]."""
        return [
            ToolDefinition(
                name="execute_code",
                description=(
                    "Execute Python code safely inside an isolated ephemeral subprocess sandbox. "
                    "Supports provisioning input files and collecting generated output artifacts."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "enum": ["python"],
                            "description": "Programming language to execute (currently 'python').",
                            "default": "python",
                        },
                        "code": {
                            "type": "string",
                            "description": "The Python source code script to execute.",
                        },
                        "timeout_seconds": {
                            "type": "number",
                            "description": "Maximum execution time in seconds before terminating (default: 30.0).",
                            "default": 30.0,
                        },
                        "files": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Optional mapping of relative file paths to content to write into the sandbox workspace.",
                        },
                        "read_outputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of relative file paths to read and return after execution.",
                        },
                    },
                    "required": ["code"],
                },
            )
        ]

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register the sandbox execution tool with the tool registry [REQ-SANDBOX-003]."""
        for tool_def in self.get_tool_definitions():
            registry.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                parameters=tool_def.parameters,
                handler=self.execute_code,
            )


    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout_seconds: Optional[float] = None,
        files: Optional[Dict[str, str]] = None,
        read_outputs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute code in the ephemeral sandbox and return structured execution telemetry [REQ-SANDBOX-003].
        """
        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds

        if language.lower() != "python":
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Unsupported execution language '{language}'. Supported: 'python'.",
                "exit_code": -1,
                "output_files": {},
                "truncated": False,
            }

        res = await SandboxedSubprocessWorker.run_python_code(
            code=code,
            timeout_seconds=timeout,
            files=files,
            read_outputs=read_outputs,
        )

        return {
            "success": res.success,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.exit_code,
            "error": res.error,
            "output_files": res.output_files,
            "truncated": res.truncated,
        }
