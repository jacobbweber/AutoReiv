"""CARD-425 operator contract: user-modified developer allowlist and legacy pack tools.

REQ-425-001: a user_modified developer gains native-tool-engineering plus
register_native_tool / plan_native_folder without a prompt rewrite or allowlist wipe.
REQ-425-002: packs/<id>/tools/*.py stays an in-process legacy loader and is not
catalogued as Native custom (source native_custom).

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import os
from pathlib import Path

NATIVE_SKILL = "native-tool-engineering"
NATIVE_TOOLS = ("register_native_tool", "plan_native_folder")
KEPT_TOOL = "operator_keep_tool"
REMOVED_TOOL = "cli_exec"
MCP_NAME = "desk-425"
PROMPT_MARK = "OPERATOR PROMPT CARD-425"


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


def _names(servers) -> list[str]:
    found = []
    for server in servers or []:
        found.append(server.name if hasattr(server, "name") else server.get("name"))
    return found




