"""
Reconcile a saved MCP enabled flag with the live mount [CARD-424].

Platform save and agent save both call this after the durable write.
Disable unmounts. Enable mounts. The returned mounted flag is the
post-action truth the HTTP response should report.
"""

from typing import Any, Optional


def _mounted_map(mcp_manager: Any) -> Optional[dict]:
    getter = getattr(mcp_manager, "get_mounted_servers", None)
    if not callable(getter):
        return None
    try:
        active = getter()
    except Exception:
        return None
    if not isinstance(active, dict):
        return None
    return active


def _tool_names(active: Optional[dict], name: str) -> list:
    if not active or name not in active:
        return []
    info = active.get(name) or {}
    tools = info.get("tools") or []
    return list(tools)


def mcp_save_http_body(name: str, outcome: dict, *, mount_error: str) -> dict:
    """HTTP body for POST save. Mount-failure shape matches the pre-424 response."""
    if outcome.get("failure") == "mount":
        return {
            "status": "saved",
            "name": name,
            "mounted": False,
            "error": f"{mount_error}: {outcome.get('exc')}",
        }
    body = {
        "status": "saved",
        "name": name,
        "mounted": bool(outcome.get("mounted")),
        "tools_count": len(outcome.get("tool_names") or []),
        "tools": list(outcome.get("tool_names") or []),
    }
    if outcome.get("failure") == "unmount":
        body["error"] = f"Configuration saved, but unmount failed: {outcome.get('exc')}"
    return body


async def reconcile_saved_mcp_server(mcp_manager: Any, req: Any) -> dict:
    """Mount when enabled, unmount when disabled.

    Returns mounted, tools (ToolDefinition list on a successful mount),
    tool_names, failure ("mount" | "unmount" | None), and exc.
    """
    enabled = bool(getattr(req, "enabled", False))
    name = getattr(req, "name", "")
    if mcp_manager is None:
        return {
            "mounted": enabled,
            "tools": [],
            "tool_names": [],
            "failure": None,
            "exc": None,
        }

    if enabled:
        try:
            tools = await mcp_manager.mount_server(
                name=name,
                command=getattr(req, "command", None),
                env=getattr(req, "env", None),
                transport=getattr(req, "transport", "stdio") or "stdio",
                url=getattr(req, "url", None),
                headers=getattr(req, "headers", None),
            )
            tool_list = list(tools or [])
            return {
                "mounted": True,
                "tools": tool_list,
                "tool_names": [tool.name for tool in tool_list],
                "failure": None,
                "exc": None,
            }
        except Exception as exc:
            return {
                "mounted": False,
                "tools": [],
                "tool_names": [],
                "failure": "mount",
                "exc": exc,
            }

    try:
        await mcp_manager.unmount_server(name)
    except Exception as exc:
        active = _mounted_map(mcp_manager)
        still = True if active is None else name in active
        return {
            "mounted": still,
            "tools": [],
            "tool_names": _tool_names(active, name),
            "failure": "unmount",
            "exc": exc,
        }

    active = _mounted_map(mcp_manager)
    still = False if active is None else name in active
    if still:
        return {
            "mounted": True,
            "tools": [],
            "tool_names": _tool_names(active, name),
            "failure": "unmount",
            "exc": RuntimeError(f"'{name}' is still mounted after unmount"),
        }
    return {
        "mounted": False,
        "tools": [],
        "tool_names": [],
        "failure": None,
        "exc": None,
    }
