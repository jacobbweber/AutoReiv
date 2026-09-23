"""Native custom tool packaging [CARD-423].

A native tool is registered on the AutoReiv tool registry and executed in the
existing subprocess sandbox. It does not require an MCP server. High-risk and
HITL tools still go through ToolPolicyGate before that sandbox runs.

The Tools Studio form does not call this module. The developer agent does,
via register_native_tool, or the operator does via /api/tools/native.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Optional

from src.application.skills.sandbox_worker import SandboxedSubprocessWorker
from src.domain.gateway.models import ToolCall
from src.domain.settings.models import AgentCustomization

logger = logging.getLogger(__name__)

NATIVE_CUSTOM_TOOLS_SETTING = "native_custom_tools"
TOOL_POLICY_SETTING = "tool_policy"
AUTHORING_TOOL_NAMES = frozenset({"register_native_tool", "plan_native_folder"})
SCRIPT_SUFFIXES = frozenset({".py", ".sh", ".ps1"})
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_RUN_DEF_RE = re.compile(r"def\s+run\s*\(")
_MAX_CODE_CHARS = 40_000
_RISK_LEVELS = frozenset({"low", "medium", "high"})

_RUNNER = """
import json
from pathlib import Path

args = json.loads(Path("args.json").read_text(encoding="utf-8"))
if not isinstance(args, dict):
    raise SystemExit("native tool arguments must be an object")
namespace = {"__name__": "native_tool"}
source = Path("tool.py").read_text(encoding="utf-8")
exec(compile(source, "tool.py", "exec"), namespace, namespace)
fn = namespace.get("run")
if not callable(fn):
    raise SystemExit("native tool code must define run(**kwargs)")
result = fn(**args)
Path("result.json").write_text(
    json.dumps({"ok": True, "result": result}, default=str),
    encoding="utf-8",
)
"""


class NativeToolError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def load_native_tool_names(store: Any) -> set[str]:
    rows = _read_rows(store)
    return {str(row.get("name") or "") for row in rows if row.get("name")}


def catalog_origin_label(source: str, server_name: str = "") -> str:
    """Operator-facing catalog label [REQ-423-005]."""
    kind = str(source or "").strip().lower()
    if kind in {"native_custom", "native"}:
        return "Native custom"
    if kind == "mcp":
        server = str(server_name or "").strip() or "server"
        return f"MCP · {server}"
    return "Platform"


def _read_rows(store: Any) -> list[dict[str, Any]]:
    getter = getattr(store, "get_setting", None)
    if not callable(getter):
        return []
    raw = getter(NATIVE_CUSTOM_TOOLS_SETTING)
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict) and item.get("name")]


class NativeCustomToolService:
    def __init__(
        self,
        store: Any,
        tool_registry: Any,
        agent_registry: Any = None,
        policy_gate: Any = None,
        hitl_engine: Any = None,
        kernel: Any = None,
    ) -> None:
        self.store = store
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.policy_gate = policy_gate
        self.hitl_engine = hitl_engine
        self.kernel = kernel

    def list_tools(self) -> list[dict[str, Any]]:
        return [_public_record(row) for row in _read_rows(self.store)]

    def get(self, name: str) -> Optional[dict[str, Any]]:
        key = str(name or "").strip()
        for row in _read_rows(self.store):
            if row.get("name") == key:
                return row
        return None

    def register(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        record = self._validate(raw)
        name = record["name"]
        self._reject_foreign_collision(name)
        rows = [row for row in _read_rows(self.store) if row.get("name") != name]
        rows.append(record)
        self.store.set_setting(NATIVE_CUSTOM_TOOLS_SETTING, rows)
        self._mount(record)
        self._sync_policy(name, bool(record["requires_hitl"]))
        granted = self._grant(name, list(record.get("grant_agent_ids") or []))
        logger.info("Registered native custom tool %s (hitl=%s)", name, record["requires_hitl"])
        body = _public_record(record)
        body.update(
            {
                "success": True,
                "persisted": True,
                "mounted": name in self.tool_registry,
                "packaging": "native",
                "mcp_required": False,
                "granted_agent_ids": granted,
            }
        )
        return body

    def delete(self, name: str) -> dict[str, Any]:
        key = str(name or "").strip()
        rows = _read_rows(self.store)
        if not any(row.get("name") == key for row in rows):
            raise NativeToolError(f"Native tool '{key}' was not found.", 404)
        kept = [row for row in rows if row.get("name") != key]
        self.store.set_setting(NATIVE_CUSTOM_TOOLS_SETTING, kept)
        unmount = getattr(self.tool_registry, "unmount_tool", None)
        if callable(unmount):
            unmount(key)
        self._sync_policy(key, False)
        logger.info("Removed native custom tool %s", key)
        return {"success": True, "name": key, "persisted": False, "packaging": "native", "mcp_required": False}

    def plan_folder(self, directory: str) -> dict[str, Any]:
        """One planned tool per script. Does not register anything [REQ-423-003]."""
        text = str(directory or "").strip()
        if not text:
            raise NativeToolError("directory is required")
        root = Path(text).expanduser().resolve()
        if not root.is_dir():
            raise NativeToolError(f"directory not found: {root}", 404)
        entries: list[dict[str, Any]] = []
        for path in sorted(root.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in SCRIPT_SUFFIXES:
                continue
            suggested = re.sub(r"[^a-z0-9_]+", "_", path.stem.lower()).strip("_")[:64]
            if not suggested or suggested.startswith("mcp_") or not _NAME_RE.match(suggested):
                continue
            entries.append(
                {
                    "script": str(path),
                    "suggested_tool_name": suggested,
                    "packaging_lanes": ["native", "mcp"],
                    "note": (
                        "Chat context only. The developer registers each entry. "
                        "Tools Studio has no folder picker."
                    ),
                }
            )
        return {
            "directory": str(root),
            "entries": entries,
            "registered": False,
            "folder_picker": False,
            "mcp_required": False,
        }

    def mount_persisted(self) -> list[str]:
        """Remount durable native tools. Called from serve startup."""
        mounted: list[str] = []
        for row in _read_rows(self.store):
            try:
                self._mount(row)
                self._sync_policy(str(row["name"]), bool(row.get("requires_hitl")))
                mounted.append(str(row["name"]))
            except Exception:
                logger.exception("Failed to remount native tool %s", row.get("name"))
        if mounted:
            logger.info("Remounted %s native custom tool(s)", len(mounted))
        return mounted

    async def invoke(
        self,
        name: str,
        arguments: Optional[Mapping[str, Any]],
        agent_id: str,
        approval_mode: str = "ask",
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        key = str(name or "").strip()
        record = self.get(key)
        if record is None:
            raise NativeToolError(f"Native tool '{key}' was not found.", 404)
        if key not in self.tool_registry:
            self._mount(record)
        agent = self._require_agent(agent_id)
        if not isinstance(arguments, Mapping):
            raise NativeToolError("arguments must be an object")
        args = dict(arguments)
        sid = str(session_id or "").strip()
        if not sid:
            session = self.store.create_session(agent_id=agent.id, title=f"Native tool {key}")
            sid = session.id
        tool_call = ToolCall(id=f"native_{uuid.uuid4().hex[:10]}", name=key, arguments=args)
        kernel = self.kernel
        gate = getattr(kernel, "_gate_tool_call", None)
        if not callable(gate):
            raise NativeToolError("Tool policy gate is unavailable.", 503)
        gated = gate(tool_call, sid, agent, approval_mode=approval_mode)
        if gated is not None:
            return _invoke_body(key, gated, ran=False, session_id=sid, approval_mode=approval_mode)
        result = await self.tool_registry.execute(
            tool_call,
            agent,
            session_id=sid,
            approval_mode=approval_mode,
            state_store=self.store,
        )
        return _invoke_body(key, result, ran=bool(getattr(result, "success", False)), session_id=sid, approval_mode=approval_mode)

    def _validate(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        name = str(raw.get("name") or "").strip()
        if name.startswith("mcp_"):
            raise NativeToolError(
                "Native tools cannot use the mcp_ prefix. Attach an MCP server for that lane."
            )
        if not _NAME_RE.match(name):
            raise NativeToolError(
                "Tool name must be a lowercase identifier (letter, then letters, digits, or underscores)."
            )
        description = str(raw.get("description") or "").strip()
        if not description:
            raise NativeToolError("description is required")
        code = str(raw.get("code") or "")
        if not code.strip():
            raise NativeToolError("code is required and must define run(**kwargs)")
        if len(code) > _MAX_CODE_CHARS:
            raise NativeToolError(f"code exceeds {_MAX_CODE_CHARS} characters")
        if not _RUN_DEF_RE.search(code):
            raise NativeToolError("code must define run(**kwargs)")
        parameters = raw.get("parameters") or {"type": "object", "properties": {}, "additionalProperties": True}
        if not isinstance(parameters, dict):
            raise NativeToolError("parameters must be a JSON schema object")
        risk = str(raw.get("risk_level") or "medium").strip().lower()
        if risk not in _RISK_LEVELS:
            raise NativeToolError("risk_level must be low, medium, or high")
        requires_hitl = bool(raw.get("requires_hitl", True))
        if risk == "high":
            requires_hitl = True
        grant = raw.get("grant_agent_ids") or []
        if isinstance(grant, str):
            grant = [part.strip() for part in grant.split(",") if part.strip()]
        if not isinstance(grant, list) or not all(isinstance(item, str) for item in grant):
            raise NativeToolError("grant_agent_ids must be a list of agent ids")
        return {
            "name": name,
            "description": description,
            "parameters": parameters,
            "code": code,
            "requires_hitl": requires_hitl,
            "risk_level": risk,
            "source": "native_custom",
            "packaging": "native",
            "mcp_required": False,
            "grant_agent_ids": [item.strip() for item in grant if item.strip()],
        }

    def _reject_foreign_collision(self, name: str) -> None:
        if name not in self.tool_registry:
            return
        if any(row.get("name") == name for row in _read_rows(self.store)):
            return
        raise NativeToolError(f"Tool '{name}' is already registered and is not a native custom tool.", 409)

    def _mount(self, record: Mapping[str, Any]) -> None:
        name = str(record["name"])
        code = str(record["code"])
        description = str(record["description"])
        parameters = dict(record.get("parameters") or {})

        async def _handler(**kwargs: Any) -> Any:
            return await _run_sandboxed(code, kwargs)

        self.tool_registry.register_tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=_handler,
        )

    def _sync_policy(self, name: str, requires_hitl: bool) -> None:
        raw = self.store.get_setting(TOOL_POLICY_SETTING)
        policy = dict(raw) if isinstance(raw, dict) else {}
        require = [str(item).strip() for item in (policy.get("require_confirm_tools") or []) if str(item).strip()]
        if requires_hitl and name not in require:
            require.append(name)
        if not requires_hitl:
            require = [item for item in require if item != name]
        policy["require_confirm_tools"] = require
        policy.setdefault("block_tools", list(policy.get("block_tools") or []))
        policy.setdefault("safe_tools", list(policy.get("safe_tools") or []))
        self.store.set_setting(TOOL_POLICY_SETTING, policy)
        reload = getattr(self.policy_gate, "reload_policy", None)
        if callable(reload):
            reload()
        if requires_hitl:
            register = getattr(self.hitl_engine, "register_high_risk_tool", None)
            if callable(register):
                register(name)

    def _grant(self, name: str, agent_ids: list[str]) -> list[str]:
        if not agent_ids:
            return []
        if self.agent_registry is None or not hasattr(self.store, "save_agent_override"):
            raise NativeToolError("Agent allowlist is unavailable.", 503)
        granted: list[str] = []
        for agent_id in agent_ids:
            profile = self.agent_registry.get_agent(agent_id)
            if profile is None:
                raise NativeToolError(f"Agent '{agent_id}' was not found.", 404)
            names = list(getattr(profile, "allowed_tool_names", None) or [])
            if name not in names:
                names.append(name)
            existing = self.store.get_agent_override(agent_id) or AgentCustomization(agent_id=agent_id)
            existing.allowed_tool_names = names
            existing.user_modified = True
            self.store.save_agent_override(existing)
            marker = getattr(self.store, "mark_agent_user_modified", None)
            if callable(marker):
                marker(agent_id, modified=True)
            granted.append(agent_id)
        return granted

    def _require_agent(self, agent_id: str) -> Any:
        key = str(agent_id or "").strip()
        if not key:
            raise NativeToolError("agent_id is required")
        getter = getattr(self.agent_registry, "get_agent", None)
        if not callable(getter):
            raise NativeToolError("Agent registry is unavailable.", 503)
        profile = getter(key)
        if profile is None:
            raise NativeToolError(f"Agent '{key}' was not found.", 404)
        return profile


def _public_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("name"),
        "description": row.get("description"),
        "parameters": row.get("parameters") or {},
        "requires_hitl": bool(row.get("requires_hitl")),
        "risk_level": row.get("risk_level") or "medium",
        "source": "native_custom",
        "packaging": "native",
        "mcp_required": False,
        "origin_label": catalog_origin_label("native_custom"),
        "has_code": bool(str(row.get("code") or "").strip()),
    }


def _invoke_body(name: str, result: Any, *, ran: bool, session_id: str, approval_mode: str) -> dict[str, Any]:
    output = getattr(result, "output", None)
    error = getattr(result, "error", None)
    success = bool(getattr(result, "success", False))
    parked = isinstance(output, dict) and output.get("status") == "parked"
    approval_id = output.get("approval_id") if isinstance(output, dict) else None
    return {
        "tool_name": name,
        "packaging": "native",
        "mcp_required": False,
        "ran": ran and not parked,
        "success": success,
        "parked": parked,
        "approval_id": approval_id,
        "approval_mode": "run" if str(approval_mode or "").strip().lower() == "run" else "ask",
        "session_id": session_id,
        "output": output,
        "error": error,
    }


async def _run_sandboxed(code: str, arguments: Mapping[str, Any]) -> Any:
    args = dict(arguments or {})
    try:
        args_json = json.dumps(args)
    except TypeError as exc:
        raise RuntimeError("native tool arguments must be JSON-serializable") from exc
    result = await SandboxedSubprocessWorker.run_sandboxed(
        [sys.executable, "runner.py"],
        timeout_seconds=20.0,
        files={
            "runner.py": _RUNNER,
            "tool.py": code,
            "args.json": args_json,
        },
        read_outputs=["result.json"],
    )
    raw = (result.output_files or {}).get("result.json") or ""
    if not result.success or not raw.strip():
        detail = (result.error or result.stderr or result.stdout or "native tool failed").strip()
        raise RuntimeError(detail)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("native tool result.json was not valid JSON") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError("native tool did not return a result")
    return parsed.get("result")
