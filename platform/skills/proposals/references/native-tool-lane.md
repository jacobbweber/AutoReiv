# Standalone Native Tool Lane (`proposals` / `native-tool-lane.md`)

Prefer authoring co-located Agora skill tools (`$DATA_DIR/skills/<skill-id>/tools/<tool_name>.py`) with `write_skill_file`. Use the standalone native-tool lane (`register_native_tool`, `view_native_tool`, `plan_native_folder`) only when registering or inspecting a standalone runtime tool under `$DATA_DIR/tools/`.

## Available Tools
- `register_native_tool`: Save and check a standalone Python tool (`def run(...) -> dict:`) with `sample_arguments`.
- `view_native_tool`: Inspect the source code and check status of an existing standalone native tool.
- `plan_native_folder`: Plan a multi-file native tool package layout.

## Safety & Verification Rules
1. `ToolCheckService` scans source code statically before any execution:
   - Pure code with zero network, filesystem, subprocess, or dynamic-import access runs in the sandbox with `sample_arguments`. If it raises or fails, registration is refused with `Not registered:`.
   - Code that uses the network, files, external programs, or dynamic imports is **not run at all** during the check and is saved as **disabled** (`not_run_review`) for operator review.
2. Standalone native tools require no folder picker and no MCP server; they execute through `ToolPolicyGate` once enabled by the operator in **Capabilities Studio** (`#view-capabilities`).
