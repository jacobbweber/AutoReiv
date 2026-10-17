"""Agora Skill Folder Authoring & Risk-Tiered Auto-Enable (CARD-689, ADR-0065).

Single canonical path (`save_skill_file`) used by both:
- `PUT /api/capabilities/skills/{skill_id}/file` (operator HTTP route)
- `write_skill_file` (agent capability-authoring tool)

Invariants:
- Writes only under `<data>/skills/<skill_id>/` (`SKILL.md`, `references/<name>.md`, `tools/<name>.py`).
  `platform/skills/` is never modified at runtime.
- Saving `tools/<name>.py` runs `ToolCheckService.check_native` first:
  1. Broken or unsafe code (`not check.ok`) is refused (`saved=False`) and nothing is written to disk.
  2. Pure `read_only` code (`check.status == "passed"`, `check.access == []`, `risk == "read_only"`)
     is auto-enabled (`auto_enabled=True`, `enabled=True`, `approval="enabled"`), mounted into
     `ScopedToolRegistry`, and activated for the current session.
  3. Code with outside access (`network`, `files`, `programs`, `hidden_imports`) or non-`read_only`
     risk (`write`, `network`, `destructive`) is saved disabled (`auto_enabled=False`,
     `enabled=False`, `approval="disabled"`), unmounted if previously mounted, and returns
     `access_warning(check.access)` so the operator reviews it before enabling.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.application.kernel.tool_registry import get_tool_context
from src.application.safety.approval_mode import (
    classify_tool_effect,
    normalize_approval_mode,
    resolve_approval_mode,
    should_auto_enable_tool,
)
from src.application.skills.agora_loader import (
    _RISK_TO_LEVEL,
    _TOOL_NAME_RE,
    _VALID_RISKS,
    _annotation_to_json_type,
    _literal_default,
    disable_skill_tool,
    enable_skill_tool,
)
from src.application.skills.session_skills import record_session_skill_activation
from src.application.tools.tool_check import ToolCheckService, access_warning, detect_access
from src.infrastructure.content.store import check_id, split_frontmatter


def _ensure_user_skill_md(store: Any, skill_id: str) -> Path:
    """Ensure `<data>/skills/<skill_id>/SKILL.md` exists on disk before writing references/ or tools/."""
    user_md = store.skills.user_path(skill_id)
    if user_md is None:
        raise RuntimeError("No data dir configured: cannot save user skill files.")
    if user_md.is_file():
        return user_md
    existing = store.skills.load(skill_id, include_hidden=True)
    if existing is not None:
        saved = store.skills.save(skill_id, dict(existing.meta), existing.body)
        return saved.path
    default_name = skill_id.replace("-", " ").replace("_", " ").title()
    saved = store.skills.save(
        skill_id,
        {"name": default_name, "description": f"Capabilities and tools for {default_name}."},
        f"# {default_name}\n",
    )
    return saved.path


def _infer_spec_from_source(tool_name: str, code: str) -> tuple[Dict[str, Any], str, str]:
    """Infer `(parameters_schema, declared_or_derived_risk, risk_level)` from Python source via AST."""
    default_params: Dict[str, Any] = {"type": "object", "properties": {}}
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return default_params, "read_only", "low"

    run_fn: Optional[ast.FunctionDef | ast.AsyncFunctionDef] = None
    declared_risk = ""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run":
            run_fn = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "RISK":
                    ok, val = _literal_default(node.value)
                    if ok and isinstance(val, str) and val.strip().lower() in _VALID_RISKS:
                        declared_risk = val.strip().lower()

    if run_fn is not None:
        args = run_fn.args
        pos_args = list(args.posonlyargs) + list(args.args)
        num_defaults = len(args.defaults)
        default_offset = len(pos_args) - num_defaults
        properties: Dict[str, Dict[str, Any]] = {}
        required: list[str] = []

        for idx, arg in enumerate(pos_args):
            if arg.arg in ("self", "cls"):
                continue
            prop: Dict[str, Any] = {"type": _annotation_to_json_type(arg.annotation)}
            if idx >= default_offset:
                default_node = args.defaults[idx - default_offset]
                ok, default_val = _literal_default(default_node)
                if ok and default_val is not None:
                    prop["default"] = default_val
            else:
                required.append(arg.arg)
            properties[arg.arg] = prop

        for kw_arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
            prop = {"type": _annotation_to_json_type(kw_arg.annotation)}
            if kw_default is not None:
                ok, default_val = _literal_default(kw_default)
                if ok and default_val is not None:
                    prop["default"] = default_val
            else:
                required.append(kw_arg.arg)
            properties[kw_arg.arg] = prop

        default_params = {"type": "object", "properties": properties}
        if required:
            default_params["required"] = required
        if args.kwarg is not None:
            default_params["additionalProperties"] = True

    access = detect_access(code or "")
    if not declared_risk:
        if "network" in access:
            declared_risk = "network"
        elif access:
            declared_risk = "write"
        else:
            declared_risk = "read_only"
    risk_level = _RISK_TO_LEVEL.get(declared_risk, "medium")
    return default_params, declared_risk, risk_level


def _activate_current_session(skill_id: str) -> None:
    ctx = get_tool_context() or {}
    session_id = str(ctx.get("session_id") or "").strip()
    if session_id:
        record_session_skill_activation(session_id, skill_id)


async def save_skill_file(
    store: Any,
    skill_id: str,
    rel_path: str,
    content: str,
    *,
    checker: Optional[ToolCheckService] = None,
    tool_registry: Any = None,
    sample_arguments: Optional[Mapping[str, Any]] = None,
    state_store: Any = None,
    approval_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Write `SKILL.md`, `references/<name>.md`, or `tools/<name>.py` into `<data>/skills/<skill_id>/`."""
    if store is None or store.skills.user_dir is None:
        raise RuntimeError("No data dir configured: cannot save user skill files.")
    clean_id = check_id(skill_id)
    text = str(content or "")

    norm = str(rel_path or "SKILL.md").strip().replace("\\", "/").lstrip("/")
    if not norm:
        norm = "SKILL.md"
    parts = norm.split("/")
    if any(p in ("..", ".", "") for p in parts):
        raise ValueError("Path traversal rejected.")

    if norm == "SKILL.md":
        meta, body = split_frontmatter(text)
        if not meta:
            existing = store.skills.load(clean_id, include_hidden=True)
            if existing is not None:
                meta = dict(existing.meta)
            else:
                default_name = clean_id.replace("-", " ").replace("_", " ").title()
                meta = {"name": default_name, "description": f"Capabilities for {default_name}."}
            body = text
        else:
            meta.setdefault("name", clean_id.replace("-", " ").replace("_", " ").title())
            meta.setdefault("description", f"Capabilities for {meta['name']}.")
        saved = store.skills.save(clean_id, meta, body)
        _activate_current_session(clean_id)
        return {
            "success": True,
            "saved": True,
            "skill_id": clean_id,
            "path": "SKILL.md",
            "source": saved.source,
            "message": f"Saved SKILL.md for skill '{clean_id}'.",
        }

    if len(parts) == 2 and parts[0] == "references":
        filename = parts[1]
        if not filename.endswith(".md") or filename.startswith("."):
            raise ValueError(f"Invalid reference filename '{filename}'; must end with .md.")
        user_md = _ensure_user_skill_md(store, clean_id)
        ref_dir = user_md.parent / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        target = (ref_dir / filename).resolve()
        target.relative_to(user_md.parent.resolve())
        target.write_text(text, encoding="utf-8", newline="\n")
        _activate_current_session(clean_id)
        return {
            "success": True,
            "saved": True,
            "skill_id": clean_id,
            "path": f"references/{filename}",
            "source": "user",
            "message": f"Saved references/{filename} in skill '{clean_id}'.",
        }

    if len(parts) == 2 and parts[0] == "tools":
        filename = parts[1]
        if not filename.endswith(".py") or filename.startswith(("_", ".")):
            raise ValueError(f"Invalid tool filename '{filename}'; must be <tool_name>.py.")
        tool_name = filename[:-3].strip()
        if not _TOOL_NAME_RE.match(tool_name) or tool_name.startswith("mcp_"):
            raise ValueError(
                f"Invalid tool name '{tool_name}'; must be lowercase letters, digits, or underscores (no mcp_ prefix)."
            )
        if tool_registry is not None and tool_name in tool_registry:
            get_origin = getattr(tool_registry, "get_tool_origin", None)
            if callable(get_origin) and get_origin(tool_name) == "platform":
                raise ValueError(f"Tool '{tool_name}' collides with a platform built-in tool.")

        params, declared_risk, risk_level = _infer_spec_from_source(tool_name, text)
        svc = checker or ToolCheckService()
        check = await svc.check_native(
            name=tool_name,
            code=text,
            parameters=params,
            risk_level=risk_level,
            sample_arguments=dict(sample_arguments) if isinstance(sample_arguments, Mapping) else None,
        )
        if not check.ok:
            return {
                "success": False,
                "saved": False,
                "skill_id": clean_id,
                "path": f"tools/{filename}",
                "tool_name": tool_name,
                "check": check.to_dict(),
                "message": check.operator_message(),
            }

        user_md = _ensure_user_skill_md(store, clean_id)
        tools_dir = user_md.parent / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        target = (tools_dir / filename).resolve()
        target.relative_to(user_md.parent.resolve())
        target.write_text(text, encoding="utf-8", newline="\n")

        effect = classify_tool_effect(risk=declared_risk, access=list(check.access or []))
        active_mode = normalize_approval_mode(approval_mode) or resolve_approval_mode(state_store)
        check_ok = (check.status == "passed") if effect == "read_only" else bool(check.ok)
        auto_enable = should_auto_enable_tool(
            mode=active_mode,
            check_passed=check_ok,
            effect=effect,
        )
        warn = access_warning(list(check.access or []))
        if auto_enable:
            spec = enable_skill_tool(store, clean_id, tool_name, tool_registry=tool_registry)
            _activate_current_session(clean_id)
            return {
                "success": True,
                "saved": True,
                "skill_id": clean_id,
                "path": f"tools/{filename}",
                "tool_name": tool_name,
                "auto_enabled": True,
                "enabled": True,
                "approval": spec.get("approval", "enabled"),
                "approval_mode": active_mode,
                "effect": effect,
                "mounted": bool(tool_registry is not None and tool_name in tool_registry),
                "risk": declared_risk,
                "access": list(check.access or []),
                "access_warning": warn,
                "check": check.to_dict(),
                "message": (
                    f"{check.operator_message()} {effect} tool '{tool_name}' auto-enabled and mounted "
                    f"in skill '{clean_id}' (approval_mode={active_mode})."
                ),
            }

        spec = disable_skill_tool(store, clean_id, tool_name, tool_registry=tool_registry)
        return {
            "success": True,
            "saved": True,
            "skill_id": clean_id,
            "path": f"tools/{filename}",
            "tool_name": tool_name,
            "auto_enabled": False,
            "enabled": False,
            "approval": spec.get("approval", "disabled"),
            "approval_mode": active_mode,
            "effect": effect,
            "mounted": False,
            "risk": declared_risk,
            "access": list(check.access or []),
            "access_warning": warn,
            "check": check.to_dict(),
            "message": (
                f"{check.operator_message()} Saved disabled in skill '{clean_id}' (effect={effect}, "
                f"approval_mode={active_mode}); operator approval is required before enabling. {warn}".strip()
            ),
        }

    raise ValueError(f"Unsupported skill file path '{rel_path}'. Allowed: SKILL.md, references/*.md, tools/*.py.")
