"""
Companion SKILL.md runbook authoring for mounted MCP servers [CARD-392 / REQ-392-004].
When an external or federated AutoReiv MCP server is mounted, automatically author
a Matt Pocock compliant SKILL.md runbook in $DATA_DIR/skills/<slug>/SKILL.md to govern
the discovered tools.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

from src.domain.gateway.models import ToolDefinition

logger = logging.getLogger(__name__)


def author_mcp_companion_skill(
    server_name: str,
    tools: List[ToolDefinition],
    url: Optional[str] = None,
    data_dir: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """
    Author a companion SKILL.md runbook for a mounted MCP server [REQ-392-004].

    Args:
        server_name: The name of the mounted MCP server (e.g. 'homelab', 'cluster').
        tools: Discovered tools from tools/list.
        url: Optional remote URL if connected over HTTP/SSE.
        data_dir: Optional custom data directory. If None, resolves default live data root.

    Returns:
        Path to the authored SKILL.md file, or None if skipped/errored.
    """
    if not tools:
        return None

    clean_name = server_name.strip().replace(" ", "-").lower()
    skill_slug = f"mcp-{clean_name}"
    display_title = server_name.replace("_", " ").replace("-", " ").title()

    # Resolve target directory
    if data_dir:
        base_dir = Path(data_dir) / "skills" / skill_slug
    else:
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            base_dir = Path(DataDirResolver().resolve().root) / "skills" / skill_slug
        except Exception:
            base_dir = Path("user_data") / "skills" / skill_slug

    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        skill_file = base_dir / "SKILL.md"

        tool_lines = []
        for t in tools:
            desc = t.description or "No description provided."
            tool_lines.append(f"- `{t.name}`: {desc}")

        tools_block = "\n".join(tool_lines)
        transport_desc = f"endpoint '{url}'" if url else "stdio subprocess"

        content = f"""---
name: {display_title} Remote MCP Capabilities
description: Federated tools and agent dispatchers mounted from MCP server '{server_name}' ({transport_desc}).
---

# {display_title} Remote MCP Capabilities

Federated capabilities and remote dispatch tools hosted on MCP server `{server_name}` ({transport_desc}).

## Available Tools

{tools_block}

## Workflow Order

1. Review required arguments and parameters before invoking remote tools.
2. For agent dispatch tools (`mcp_{server_name}_ask_*`), supply explicit context and instructions in the prompt.
3. Handle remote failures gracefully and present verified output to the operator.

## Pitfalls

- Remote network timeouts: allow adequate execution duration for deep agent turns.
- Guard high-risk actions: remote agent turns execute with server-side governance.

## Done-when

- Target remote operations have executed and structured responses have been returned.
"""
        skill_file.write_text(content, encoding="utf-8")
        logger.info("Authored companion MCP SKILL.md at %s", skill_file)
        return skill_file
    except Exception as exc:
        logger.warning("Failed to author companion MCP skill for '%s': %s", server_name, exc)
        return None
