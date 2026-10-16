"""Agora Skill Folder Loader (CARD-687, ADR-0065).

Discovers colocated Python tools (`skills/<id>/tools/*.py`) and reference documents
(`skills/<id>/references/*.md`) inside shipped (`platform/skills/<id>`) and user
(`<data>/skills/<id>`) skill folders.

Key invariants:
- AST-only inspection at scan time: top-level code in `tools/*.py` is never imported or
  executed when listing or inferring schemas.
- JSON Schema `parameters` and `description` are inferred directly from `def run(...)`
  type annotations, defaults, and docstrings — no `tool.json` sidecar required.
- Shipped `platform/skills/<id>/tools/*.py` are enabled by default unless explicitly
  disabled by the operator; user-authored `<data>/skills/<id>/tools/*.py` require an
  approved SHA-256 hash in `<data>/skills/.tool_approvals.json`.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.tools.tool_check import access_warning, detect_access, detect_path_safety_violation

logger = logging.getLogger(__name__)

SKILL_TOOL_APPROVALS_FILE = ".tool_approvals.json"
_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VALID_RISKS = frozenset({"read_only", "write", "network", "destructive"})
_RISK_TO_LEVEL = {
    "read_only": "low",
    "write": "medium",
    "network": "medium",
    "destructive": "high",
}

_PY_TYPE_TO_SCHEMA: Dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "List": "array",
    "Sequence": "array",
    "tuple": "array",
    "dict": "object",
    "Dict": "object",
    "Mapping": "object",
    "Any": "string",
}


def code_sha256(code: str) -> str:
    return hashlib.sha256((code or "").replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _annotation_to_json_type(node: Optional[ast.AST]) -> str:
    if node is None:
        return "string"
    if isinstance(node, ast.Name):
        return _PY_TYPE_TO_SCHEMA.get(node.id, "string")
    if isinstance(node, ast.Attribute):
        return _PY_TYPE_TO_SCHEMA.get(node.attr, "string")
    if isinstance(node, ast.Subscript):
        # Handle Optional[T], Union[T, None], list[T], dict[K, V]
        base = node.value
        base_name = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        if base_name in ("Optional", "Union"):
            slice_node = node.slice
            if isinstance(slice_node, ast.Tuple) and slice_node.elts:
                for elt in slice_node.elts:
                    if not (isinstance(elt, ast.Constant) and elt.value is None) and not (
                        isinstance(elt, ast.Name) and elt.id == "None"
                    ):
                        return _annotation_to_json_type(elt)
            return _annotation_to_json_type(slice_node)
        return _PY_TYPE_TO_SCHEMA.get(base_name, "string")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Handle Python 3.10+ `T | None`
        if isinstance(node.right, ast.Constant) and node.right.value is None:
            return _annotation_to_json_type(node.left)
        if isinstance(node.left, ast.Constant) and node.left.value is None:
            return _annotation_to_json_type(node.right)
        return _annotation_to_json_type(node.left)
    return "string"


def _literal_default(node: ast.AST) -> tuple[bool, Any]:
    try:
        return True, ast.literal_eval(node)
    except Exception:
        return False, None


def extract_agora_tool_spec(path: Path, *, source: str = "user", skill_id: str = "") -> Optional[Dict[str, Any]]:
    """Parse a colocated `tools/<name>.py` file via AST without importing or executing it."""
    if not path.is_file() or path.suffix.lower() != ".py" or path.name.startswith(("_", ".")):
        return None
    name = path.stem.strip()
    if not _TOOL_NAME_RE.match(name) or name.startswith("mcp_"):
        return None
    try:
        code = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        tree = ast.parse(code, filename=str(path))
    except SyntaxError as exc:
        logger.warning("Skipping Agora tool %s with syntax error: %s", path, exc)
        return None

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

    if run_fn is None:
        return None

    module_doc = (ast.get_docstring(tree) or "").strip()
    run_doc = (ast.get_docstring(run_fn) or "").strip()
    raw_doc = module_doc or run_doc or f"Execute {name}."
    description = raw_doc.splitlines()[0].strip()

    # Build JSON Schema parameters from `def run(...)` signature
    args = run_fn.args
    pos_args = list(args.posonlyargs) + list(args.args)
    num_defaults = len(args.defaults)
    default_offset = len(pos_args) - num_defaults

    properties: Dict[str, Dict[str, Any]] = {}
    required: List[str] = []

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

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters["required"] = required
    if args.kwarg is not None:
        parameters["additionalProperties"] = True

    access = detect_access(code)
    path_violation = detect_path_safety_violation(code)
    if not declared_risk:
        if "network" in access:
            declared_risk = "network"
        elif "files" in access or "programs" in access:
            declared_risk = "write"
        else:
            declared_risk = "read_only"

    risk_level = _RISK_TO_LEVEL.get(declared_risk, "medium")
    requires_hitl = declared_risk != "read_only"

    return {
        "name": name,
        "skill_id": skill_id,
        "description": description,
        "parameters": parameters,
        "code": code,
        "code_sha256": code_sha256(code),
        "path": str(path),
        "relative_path": f"tools/{path.name}",
        "source": source,
        "risk": declared_risk,
        "risk_level": risk_level,
        "requires_hitl": requires_hitl,
        "access": access,
        "access_warning": access_warning(access),
        "path_safety_violation": path_violation,
    }


def _approvals_path(store: Any) -> Optional[Path]:
    data_root = getattr(store, "data_root", None)
    if data_root is None:
        return None
    return Path(data_root) / "skills" / SKILL_TOOL_APPROVALS_FILE


def read_skill_tool_approvals(store: Any) -> Dict[str, Dict[str, Any]]:
    path = _approvals_path(store)
    if not path or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}
    except (OSError, ValueError):
        pass
    return {}


def write_skill_tool_approvals(store: Any, approvals: Dict[str, Dict[str, Any]]) -> None:
    path = _approvals_path(store)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(approvals, indent=2, sort_keys=True), encoding="utf-8")


def _approval_key(skill_id: str, tool_name: str) -> str:
    return f"{skill_id}/{tool_name}"


def resolve_tool_approval_state(
    store: Any,
    skill_id: str,
    spec: Dict[str, Any],
    approvals: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute enabled/approval state for one colocated tool.

    Shipped (`platform/skills/<id>/tools/*.py`) tools are enabled by default unless the
    operator explicitly disabled them in `.tool_approvals.json`.
    User (`<data>/skills/<id>/tools/*.py`) tools require `enabled=True` AND matching
    `approved_sha256 == code_sha256`.
    """
    if approvals is None:
        approvals = read_skill_tool_approvals(store)
    entry = approvals.get(_approval_key(skill_id, spec["name"])) or {}
    current_sha = spec["code_sha256"]
    approved_sha = str(entry.get("approved_sha256") or "")

    if spec.get("path_safety_violation"):
        return {
            "enabled": False,
            "approval": "blocked",
            "approved_sha256": approved_sha or None,
        }

    if spec.get("source") == "shipped":
        enabled = bool(entry.get("enabled", True))
        return {
            "enabled": enabled,
            "approval": "enabled" if enabled else "disabled",
            "approved_sha256": current_sha,
        }

    enabled_flag = bool(entry.get("enabled", False))
    if enabled_flag and approved_sha == current_sha:
        state = "enabled"
        enabled = True
    elif enabled_flag:
        state = "needs_reapproval"
        enabled = False
    else:
        state = "disabled"
        enabled = False
    return {
        "enabled": enabled,
        "approval": state,
        "approved_sha256": approved_sha or None,
    }


def list_skill_colocated_tools(store: Any, skill_id: str) -> List[Dict[str, Any]]:
    """Return all colocated `tools/*.py` specs for `skill_id` (user tool overrides shipped by name)."""
    clean_id = str(skill_id or "").strip()
    if not clean_id or store is None:
        return []
    shipped_md = store.skills.shipped_path(clean_id)
    user_md = store.skills.user_path(clean_id)
    shipped_tools_dir = shipped_md.parent / "tools" if shipped_md else None
    user_tools_dir = user_md.parent / "tools" if user_md else None

    found: Dict[str, Dict[str, Any]] = {}
    if shipped_tools_dir and shipped_tools_dir.is_dir():
        for py_file in sorted(shipped_tools_dir.glob("*.py")):
            spec = extract_agora_tool_spec(py_file, source="shipped", skill_id=clean_id)
            if spec:
                found[spec["name"]] = spec

    if user_tools_dir and user_tools_dir.is_dir():
        for py_file in sorted(user_tools_dir.glob("*.py")):
            spec = extract_agora_tool_spec(py_file, source="user", skill_id=clean_id)
            if spec:
                found[spec["name"]] = spec

    approvals = read_skill_tool_approvals(store)
    result: List[Dict[str, Any]] = []
    for name in sorted(found):
        spec = dict(found[name])
        spec.update(resolve_tool_approval_state(store, clean_id, spec, approvals))
        result.append(spec)
    return result


def enabled_colocated_tool_names(store: Any, skill_id: str) -> List[str]:
    """Names of enabled colocated `tools/*.py` in `skill_id`."""
    return [t["name"] for t in list_skill_colocated_tools(store, skill_id) if t.get("enabled")]


def enable_skill_tool(
    store: Any,
    skill_id: str,
    tool_name: str,
    *,
    tool_registry: Any = None,
) -> Dict[str, Any]:
    """Approve the current code SHA-256 and enable a colocated tool in `skills/<skill_id>/tools/<tool_name>.py`."""
    tools = {t["name"]: t for t in list_skill_colocated_tools(store, skill_id)}
    spec = tools.get(str(tool_name or "").strip())
    if spec is None:
        raise LookupError(f"Tool '{tool_name}' not found in skill '{skill_id}'.")
    if spec.get("path_safety_violation"):
        raise ValueError(f"Tool '{tool_name}' has a path safety violation: {spec['path_safety_violation']}")

    approvals = read_skill_tool_approvals(store)
    approvals[_approval_key(skill_id, spec["name"])] = {
        "enabled": True,
        "approved_sha256": spec["code_sha256"],
    }
    write_skill_tool_approvals(store, approvals)
    spec.update(resolve_tool_approval_state(store, skill_id, spec, approvals))
    if tool_registry is not None:
        mount_colocated_tool(tool_registry, spec)
    return spec


def disable_skill_tool(
    store: Any,
    skill_id: str,
    tool_name: str,
    *,
    tool_registry: Any = None,
) -> Dict[str, Any]:
    """Disable a colocated tool and unmount it from the live tool registry."""
    tools = {t["name"]: t for t in list_skill_colocated_tools(store, skill_id)}
    spec = tools.get(str(tool_name or "").strip())
    if spec is None:
        raise LookupError(f"Tool '{tool_name}' not found in skill '{skill_id}'.")

    approvals = read_skill_tool_approvals(store)
    prev = approvals.get(_approval_key(skill_id, spec["name"])) or {}
    approvals[_approval_key(skill_id, spec["name"])] = {
        "enabled": False,
        "approved_sha256": prev.get("approved_sha256"),
    }
    write_skill_tool_approvals(store, approvals)
    spec.update(resolve_tool_approval_state(store, skill_id, spec, approvals))
    if tool_registry is not None:
        unmount = getattr(tool_registry, "unmount_tool", None)
        if callable(unmount) and spec["name"] in tool_registry:
            unmount(spec["name"])
    return spec


def mount_colocated_tool(tool_registry: Any, spec: Dict[str, Any]) -> bool:
    """Mount one enabled colocated tool onto `ScopedToolRegistry` using the subprocess sandbox."""
    if not spec.get("enabled") or tool_registry is None:
        return False
    name = str(spec["name"])
    # Never overwrite a platform built-in tool
    get_origin = getattr(tool_registry, "get_tool_origin", None)
    if callable(get_origin) and name in tool_registry and get_origin(name) == "platform":
        return False

    from src.application.tools.native_packaging import _run_sandboxed

    code = str(spec["code"])

    async def _handler(**kwargs: Any) -> Any:
        return await _run_sandboxed(code, kwargs)

    tool_registry.register_tool(
        name=name,
        description=str(spec["description"]),
        parameters=dict(spec.get("parameters") or {"type": "object", "properties": {}}),
        handler=_handler,
        origin="agora_skill",
        risk=str(spec.get("risk") or "read_only"),
    )
    return True


def mount_all_enabled_skill_tools(store: Any, tool_registry: Any) -> List[str]:
    """Scan all skills in `ContentStore` and mount every enabled colocated tool."""
    if store is None or tool_registry is None:
        return []
    mounted: List[str] = []
    for skill in store.skills.list(include_hidden=False):
        for spec in list_skill_colocated_tools(store, skill.id):
            if spec.get("enabled") and mount_colocated_tool(tool_registry, spec):
                mounted.append(spec["name"])
    return mounted


def list_skill_references(store: Any, skill_id: str) -> List[Dict[str, str]]:
    """List `references/*.md` files in a skill folder (user references override shipped by filename)."""
    clean_id = str(skill_id or "").strip()
    if not clean_id or store is None:
        return []
    shipped_md = store.skills.shipped_path(clean_id)
    user_md = store.skills.user_path(clean_id)
    shipped_ref_dir = shipped_md.parent / "references" if shipped_md else None
    user_ref_dir = user_md.parent / "references" if user_md else None

    refs: Dict[str, Dict[str, str]] = {}
    if shipped_ref_dir and shipped_ref_dir.is_dir():
        for md_file in sorted(shipped_ref_dir.glob("*.md")):
            if not md_file.name.startswith("."):
                refs[md_file.name] = {
                    "name": md_file.name,
                    "path": f"references/{md_file.name}",
                    "source": "shipped",
                    "_abs": str(md_file),
                }
    if user_ref_dir and user_ref_dir.is_dir():
        for md_file in sorted(user_ref_dir.glob("*.md")):
            if not md_file.name.startswith("."):
                refs[md_file.name] = {
                    "name": md_file.name,
                    "path": f"references/{md_file.name}",
                    "source": "user",
                    "_abs": str(md_file),
                }
    return [
        {"name": refs[k]["name"], "path": refs[k]["path"]}
        for k in sorted(refs)
    ]


def read_skill_file(store: Any, skill_id: str, rel_path: str) -> Dict[str, Any]:
    """Read `SKILL.md`, `references/<name>.md`, or `tools/<name>.py` inside a skill folder with path-traversal jailing."""
    clean_id = str(skill_id or "").strip()
    loaded = store.skills.load(clean_id, include_hidden=True) if store and clean_id else None
    if loaded is None:
        raise LookupError(f"Skill '{skill_id}' not found.")

    norm = str(rel_path or "SKILL.md").strip().replace("\\", "/").lstrip("/")
    if not norm:
        norm = "SKILL.md"
    parts = norm.split("/")
    if any(p in ("..", ".", "") for p in parts):
        raise ValueError("Path traversal rejected.")

    if norm == "SKILL.md":
        return {
            "skill_id": clean_id,
            "path": "SKILL.md",
            "source": loaded.source,
            "content": loaded.path.read_text(encoding="utf-8"),
        }

    if len(parts) == 2 and parts[0] in ("references", "tools"):
        subdir, filename = parts[0], parts[1]
        expected_suffix = ".md" if subdir == "references" else ".py"
        if not filename.endswith(expected_suffix) or filename.startswith("."):
            raise ValueError(f"Invalid file in {subdir}/: {filename}")

        user_md = store.skills.user_path(clean_id)
        shipped_md = store.skills.shipped_path(clean_id)
        candidates = []
        if user_md:
            candidates.append((user_md.parent / subdir / filename, "user", user_md.parent))
        if shipped_md:
            candidates.append((shipped_md.parent / subdir / filename, "shipped", shipped_md.parent))

        for candidate, src, root_dir in candidates:
            try:
                resolved = candidate.resolve()
                resolved.relative_to(root_dir.resolve())
            except (OSError, ValueError):
                continue
            if resolved.is_file():
                return {
                    "skill_id": clean_id,
                    "path": f"{subdir}/{filename}",
                    "source": src,
                    "content": resolved.read_text(encoding="utf-8"),
                }
        raise LookupError(f"File '{norm}' not found in skill '{clean_id}'.")

    raise ValueError(f"Unsupported skill file path '{rel_path}'. Allowed: SKILL.md, references/*.md, tools/*.py.")


def build_capabilities_tree(store: Any) -> Dict[str, Any]:
    """Return the Agora directory tree for all skills in `ContentStore`."""
    if store is None:
        return {"skills": []}
    skills_out: List[Dict[str, Any]] = []
    for item in store.skills.list(include_hidden=True):
        colocated = [
            {k: v for k, v in t.items() if k != "code"}
            for t in list_skill_colocated_tools(store, item.id)
        ]
        refs = list_skill_references(store, item.id)
        skills_out.append(
            {
                "id": item.id,
                "name": str(item.meta.get("name") or item.id),
                "description": str(item.meta.get("description") or ""),
                "source": item.source,
                "shipped": item.shipped,
                "edited": item.edited,
                "shipped_changed": item.shipped_changed,
                "hidden": item.id in store.skills.hidden(),
                "files": ["SKILL.md"]
                + [r["path"] for r in refs]
                + [t["relative_path"] for t in colocated],
                "references": refs,
                "declared_tools": list(item.tools),
                "colocated_tools": colocated,
            }
        )
    return {"skills": skills_out}
