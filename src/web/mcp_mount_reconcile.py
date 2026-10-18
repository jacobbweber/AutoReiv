"""
Reconcile a saved MCP enabled flag with the live mount [CARD-424].

Platform save and agent save both call this after the durable write.
Disable unmounts. Enable mounts. The returned mounted flag is the
post-action truth the HTTP response should report.
"""

import base64
from typing import Any, Optional


def _cfg_val(config: Any, key: str, default: Any = None) -> Any:
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


def lookup_mcp_credential_name(credential_id: Optional[str], store: Any = None) -> Optional[str]:
    """Return the human-readable Vault credential name for UI display without exposing the secret [CARD-717]."""
    cid = (credential_id or "").strip()
    if not cid or store is None:
        return None
    getter = getattr(store, "get_credential", None)
    if not callable(getter):
        return None
    try:
        cred = getter(cid)
        return getattr(cred, "name", None) if cred else None
    except Exception:
        return None


def resolve_mcp_server_auth(config: Any, store: Any = None) -> dict:
    """Resolve optional Vault credential_id into runtime headers or env without mutating stored config [CARD-717]."""
    raw_headers = _cfg_val(config, "headers")
    raw_env = _cfg_val(config, "env")
    headers: dict[str, str] = dict(raw_headers) if isinstance(raw_headers, dict) else {}
    env: dict[str, str] = dict(raw_env) if isinstance(raw_env, dict) else {}

    cred_id = str(_cfg_val(config, "credential_id") or "").strip()
    if cred_id and store is not None and callable(getattr(store, "get_credential", None)):
        try:
            cred = store.get_credential(cred_id)
        except Exception:
            cred = None
        secret = str(getattr(cred, "secret", "") or "").strip() if cred else ""
        if secret:
            auth_type = str(_cfg_val(config, "auth_type") or "bearer").strip().lower()
            auth_header = str(_cfg_val(config, "auth_header") or "").strip()
            if auth_type == "env":
                env[auth_header or "MCP_API_KEY"] = secret
            elif auth_type in ("header", "api_key"):
                headers[auth_header or "X-API-Key"] = secret
            elif auth_type == "basic":
                hdr_name = auth_header or "Authorization"
                if secret.lower().startswith("basic "):
                    headers[hdr_name] = secret
                elif ":" in secret:
                    b64 = base64.b64encode(secret.encode("utf-8")).decode("ascii")
                    headers[hdr_name] = f"Basic {b64}"
                else:
                    headers[hdr_name] = f"Basic {secret}"
            else:
                hdr_name = auth_header or "Authorization"
                if secret.lower().startswith("bearer "):
                    headers[hdr_name] = secret
                else:
                    headers[hdr_name] = f"Bearer {secret}"

    return {
        "headers": headers if headers else None,
        "env": env if env else None,
    }


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


def mount_errors(mcp_manager: Any) -> dict:
    """Last start error per server that failed to mount [CARD-516]. Empty when unknown."""
    getter = getattr(mcp_manager, "get_mount_errors", None)
    if not callable(getter):
        return {}
    try:
        errors = getter()
    except Exception:
        return {}
    return errors if isinstance(errors, dict) else {}


def mcp_save_http_body(name: str, outcome: dict, *, mount_error: str) -> dict:
    """HTTP body for POST save. Mount-failure shape matches the pre-424 response."""
    if outcome.get("failure") == "mount":
        return {
            "status": "saved",
            "name": name,
            "mounted": False,
            "error": f"{mount_error}: {outcome.get('exc')}",
            "last_error": str(outcome.get("exc")),  # CARD-516: the reason alone, for the badge
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


async def reconcile_saved_mcp_server(
    mcp_manager: Any,
    req: Any,
    store: Any = None,
    *,
    data_dir: Any = None,
    agent_registry: Any = None,
    agent_id: Optional[str] = None,
) -> dict:
    """Mount when enabled, unmount when disabled [CARD-424, CARD-718].

    Returns mounted, tools (ToolDefinition list on a successful mount),
    tool_names, failure ("mount" | "unmount" | None), and exc.
    """
    enabled = bool(_cfg_val(req, "enabled", False))
    name = str(_cfg_val(req, "name", "") or "")
    if mcp_manager is None:
        return {
            "mounted": enabled,
            "tools": [],
            "tool_names": [],
            "failure": None,
            "exc": None,
        }

    if enabled:
        resolved = resolve_mcp_server_auth(req, store)
        try:
            tools = await mcp_manager.mount_server(
                name=name,
                command=_cfg_val(req, "command", None),
                env=resolved["env"],
                transport=_cfg_val(req, "transport", "stdio") or "stdio",
                url=_cfg_val(req, "url", None),
                headers=resolved["headers"],
            )
            tool_list = list(tools or [])
            if tool_list and name:
                try:
                    from src.infrastructure.mcp.companion_author import (
                        author_mcp_companion_skill,
                        mcp_companion_skill_id,
                    )

                    author_mcp_companion_skill(
                        server_name=name,
                        tools=tool_list,
                        url=_cfg_val(req, "url", None),
                        data_dir=data_dir,
                    )
                    if agent_id and agent_registry is not None:
                        from src.application.agent_skills.skill_list import add_skill_to_agent

                        add_skill_to_agent(
                            store,
                            agent_registry,
                            agent_id=agent_id,
                            skill_id=mcp_companion_skill_id(name),
                        )
                except Exception:
                    pass
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

    if agent_id and agent_registry is not None and name:
        try:
            from src.application.agent_skills.skill_list import remove_skill_from_agent
            from src.infrastructure.mcp.companion_author import mcp_companion_skill_id

            remove_skill_from_agent(
                store,
                agent_registry,
                agent_id=agent_id,
                skill_id=mcp_companion_skill_id(name),
            )
        except Exception:
            pass

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
