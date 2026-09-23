"""Legacy in-process loader for ``packs/<id>/tools/*.py`` [CARD-425 / REQ-425-002].

This is an explicit legacy path. It imports a callable from each module and
registers it on the tool registry with origin ``legacy_pack_tool``.

It is not the CARD-423 native custom lane:

- it does not write the ``native_custom_tools`` setting
- it does not run ``SandboxedSubprocessWorker``
- it does not go through ToolPolicyGate HITL
- catalog origin is **Legacy pack tool**, never **Native custom**
  (``source`` must not be ``native_custom``)

New custom tools belong in ``register_native_tool`` or an MCP server.
This loader stays so existing pack modules keep working.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LEGACY_PACK_TOOL_ORIGIN = "legacy_pack_tool"


def load_legacy_pack_tools(packs_dir: Path, tool_registry: object) -> list[str]:
    """Import ``packs/<id>/tools/*.py`` and register them in-process.

    Returns the tool names registered on this call. Names already in the
    registry are left alone. A module that fails to import still gets an
    in-process stub with the same legacy origin, not a native-custom record.
    """
    loaded: list[str] = []
    root = Path(packs_dir)
    if not root.is_dir() or tool_registry is None or not hasattr(tool_registry, "register_tool"):
        return loaded

    for pack_folder in root.iterdir():
        if not pack_folder.is_dir():
            continue
        tools_dir = pack_folder / "tools"
        if not tools_dir.is_dir():
            continue
        for tool_file in sorted(tools_dir.glob("*.py")):
            if tool_file.name.startswith("__"):
                continue
            tool_name = tool_file.stem
            if tool_name in tool_registry:
                continue
            loaded_handler = _import_handler(tool_file, tool_name)
            handler = loaded_handler or _stub_handler(tool_name, pack_folder.name)
            description = f"Legacy in-process pack tool for {pack_folder.name}."
            if loaded_handler and getattr(loaded_handler, "__doc__", None):
                lines = [line.strip() for line in loaded_handler.__doc__.strip().split("\n") if line.strip()]
                if lines:
                    description = lines[0]
            tool_registry.register_tool(
                name=tool_name,
                description=description,
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform (e.g. status, list, create)",
                        },
                    },
                },
                handler=handler,
                origin=LEGACY_PACK_TOOL_ORIGIN,
            )
            loaded.append(tool_name)
            logger.info(
                "Loaded legacy in-process pack tool %s from %s (origin=%s; not native custom)",
                tool_name,
                tool_file,
                LEGACY_PACK_TOOL_ORIGIN,
            )
    return loaded


def _import_handler(tool_file: Path, tool_name: str):
    try:
        spec = importlib.util.spec_from_file_location(f"pack_tool_{tool_name}", str(tool_file))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, tool_name):
                return getattr(module, tool_name)
    except Exception as exc:
        logger.warning("Failed to load legacy pack tool %s: %s", tool_file, exc)
    return None


def _stub_handler(tool_id: str, agent_id: str):
    def _handler(action: str = "status", **kwargs):
        return {
            "success": True,
            "action": action,
            "agent": agent_id,
            "tool": tool_id,
            "details": kwargs,
            "origin": LEGACY_PACK_TOOL_ORIGIN,
        }

    return _handler
