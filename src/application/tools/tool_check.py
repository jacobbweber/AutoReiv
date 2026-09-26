"""Check a Developer-built tool once in the sandbox before it is registered [CARD-511].

ADR-0060 D6: of the Factory's verification battery, only ``detect_path_safety_violation``
outlives the Factory, and it lives here now. This module must not import
``agent_training_factory``, ``verification_battery``, ``tool_synthesizer`` or
``factory_packets`` (CARD-497 deletes them).

Native tools: static (parse, module-level ``run``, path safety), import in the sandbox,
then one sample call through the same exec-and-call runner that invoke uses.
MCP servers: start, ``tools/list`` (at least one tool, valid names, object input
schemas), then one sample ``tools/call``.

Honest limits: the sandbox is a fresh temp folder with secret-looking environment
variables removed, output caps and a timeout. It does not block the network or jail
the file system, so a tool with side effects performs them during the sample call.
High-risk tools skip the call, and Developer may skip it with a stated reason. The
check never calls an LLM and never injects secrets.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Optional

from src.application.kernel.tool_registry import get_tool_context
from src.application.skills.sandbox_worker import SandboxedSubprocessWorker, SubprocessResult

logger = logging.getLogger(__name__)

CHECK_EVENT_KIND = "tools_studio_tool_check"
MEDIATION_TEMPLATE_ID = "tools_studio_developer_mediation"

NATIVE_IMPORT_TIMEOUT = 10.0
NATIVE_CALL_TIMEOUT = 20.0
MCP_LIST_TIMEOUT = 10.0
MCP_CALL_TIMEOUT = 20.0
MAX_ERROR_CHARS = 2000

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_SKIPPED_CALL = "checked_without_call"
STATUS_COULD_NOT_RUN = "could_not_run"
OK_STATUSES = frozenset({STATUS_PASSED, STATUS_SKIPPED_CALL})
HIGH_RISK_SKIP_REASON = "high risk: sample call skipped"

# Credentials the tool registry exports for the calling agent never reach the check.
_DROP_ENV_PREFIXES = ("AUTOREIV_CRED_",)
_MCP_TOOL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_VERIFIER_STATUS = {
    STATUS_PASSED: "passed",
    STATUS_FAILED: "failed",
    STATUS_SKIPPED_CALL: "skipped",
    STATUS_COULD_NOT_RUN: "failed",
}

# Same exec-and-call path as invoke. native_packaging imports this for invoke.
NATIVE_RUNNER = """
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

# The check's call is the invoke runner, except the result must really be JSON.
_CHECK_CALL_RUNNER = NATIVE_RUNNER.replace(
    'Path("result.json").write_text(\n    json.dumps({"ok": True, "result": result}, default=str),\n    encoding="utf-8",\n)\n',
    'try:\n    payload = json.dumps({"ok": True, "result": result})\n'
    "except (TypeError, ValueError) as exc:\n"
    '    raise SystemExit("run() returned a value that is not JSON-serializable: " + str(exc))\n'
    'Path("result.json").write_text(payload, encoding="utf-8")\n',
)

_IMPORT_RUNNER = """
from pathlib import Path

namespace = {"__name__": "native_tool"}
source = Path("tool.py").read_text(encoding="utf-8")
exec(compile(source, "tool.py", "exec"), namespace, namespace)
if not callable(namespace.get("run")):
    raise SystemExit("native tool code must define run(**kwargs)")
Path("imported.json").write_text('{"ok": true}', encoding="utf-8")
"""


def detect_path_safety_violation(tool_code: str) -> Optional[str]:
    """Return reason if tool_code has path traversal / sandbox escape.

    Absolute Windows paths (C:\\Users\\..., D:\\Archive\\...) are allowed.
    Moved here from ``orchestration/verification_battery.py`` [ADR-0060 D6, CARD-511].
    """
    code = tool_code or ""
    if re.search(r"\.\.(?:/|\\)", code):
        return "Path traversal segment ('..') detected. Disallowed."
    if re.search(r"[\"']/(?:etc|proc|sys)(?:/|\\|[\"'])", code):
        return "Sensitive absolute Unix path literal detected. Disallowed."
    if re.search(r"[\"'/]/(?:etc|proc|sys)/", code):
        return "Sensitive absolute Unix path literal detected. Disallowed."
    return None


@dataclass
class ToolCheckResult:
    """Outcome of one check. Stored on the tool row, the MCP record and the job journey."""

    tool: str
    lane: str
    status: str
    stage: Optional[str] = None
    error: Optional[str] = None
    stages: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    sample_arguments: Optional[dict] = None
    sample_tool: Optional[str] = None
    skip_reason: Optional[str] = None
    duration_ms: int = 0
    checked_at: str = ""

    @property
    def ok(self) -> bool:
        return self.status in OK_STATUSES

    def operator_message(self) -> str:
        if self.status == STATUS_PASSED:
            if self.lane == "mcp":
                return f"Checked: {self.tool} started, listed its tools and answered one sample call."
            return f"Checked: {self.tool} ran once in the sandbox."
        if self.status == STATUS_SKIPPED_CALL:
            return f"Checked without a sample call: {self.skip_reason or 'skipped'}."
        if self.status == STATUS_COULD_NOT_RUN:
            reason = (self.error or "the sandbox did not start").strip().rstrip(".")
            return f"The check could not run: {reason}. Nothing was registered; try again."
        first = (self.error or "").strip().splitlines()[0] if (self.error or "").strip() else "no error output"
        stage = (self.stage or "tool").replace("_", " ")
        return f"Not registered: {self.tool} failed the {stage} check. {first}"

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["message"] = self.operator_message()
        return body


Runner = Callable[..., Awaitable[SubprocessResult]]


def build_sample_arguments(schema: Any) -> dict[str, Any]:
    """Minimal input from a JSON Schema: required properties only [REQ-511-007]."""
    if not isinstance(schema, Mapping):
        return {}
    props = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    out: dict[str, Any] = {}
    for key in required:
        spec = props.get(key) if isinstance(props.get(key), Mapping) else {}
        if "default" in spec:
            out[key] = spec["default"]
            continue
        enum = spec.get("enum")
        if isinstance(enum, list) and enum:
            out[key] = enum[0]
            continue
        kind = spec.get("type")
        if isinstance(kind, list):
            kind = next((k for k in kind if k != "null"), None)
        out[key] = {"string": "", "integer": 0, "number": 0, "boolean": False, "array": [], "object": {}}.get(kind, "")
    return out


_JSON_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def validate_sample_arguments(schema: Any, args: Any) -> Optional[str]:
    """Return a reason when Developer's sample input does not fit the tool schema."""
    if not isinstance(args, Mapping):
        return "sample_arguments must be an object"
    if not isinstance(schema, Mapping):
        return None
    props = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
    for key in schema.get("required") if isinstance(schema.get("required"), list) else []:
        if key not in args:
            return f"sample_arguments is missing the required '{key}'"
    for key, value in args.items():
        spec = props.get(key)
        if not isinstance(spec, Mapping):
            continue
        kind = spec.get("type")
        if isinstance(kind, str) and kind in _JSON_TYPES:
            wrong_bool = kind in {"integer", "number"} and isinstance(value, bool)
            if wrong_bool or not isinstance(value, _JSON_TYPES[kind]):
                return f"sample_arguments '{key}' should be {kind}"
        enum = spec.get("enum")
        if isinstance(enum, list) and enum and value not in enum:
            return f"sample_arguments '{key}' must be one of {enum}"
    return None


def trim_error(text: Any, limit: int = MAX_ERROR_CHARS) -> str:
    """Last traceback line first, then the rest, capped [REQ-511-002]."""
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return "no error output"
    last = lines[-1].strip()
    rest = "\n".join(lines[:-1])
    body = f"{last}\n{rest}" if rest else last
    return body[:limit]


def _static_native(code: str) -> tuple[Optional[str], list[str]]:
    try:
        tree = ast.parse(code, filename="tool.py")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})", []
    if not any(isinstance(node, ast.FunctionDef) and node.name == "run" for node in tree.body):
        return "code must define a module-level def run(**kwargs)", []
    reason = detect_path_safety_violation(code)
    if reason:
        return reason, []
    warnings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            note = f"uses {node.func.id}() (line {node.lineno})"
            if note not in warnings:
                warnings.append(note)
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            warnings.append(f"bare except (line {node.lineno})")
    return None, warnings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _Outcome(Exception):
    def __init__(self, status: str, stage: str, error: str):
        super().__init__(error)
        self.status = status
        self.stage = stage
        self.error = error


class ToolCheckService:
    """One sandbox run before registration [CARD-511]. No LLM, no secrets."""

    def __init__(
        self,
        runner: Optional[Runner] = None,
        adapter_factory: Optional[Callable[..., Any]] = None,
        import_timeout: float = NATIVE_IMPORT_TIMEOUT,
        call_timeout: float = NATIVE_CALL_TIMEOUT,
        mcp_list_timeout: float = MCP_LIST_TIMEOUT,
        mcp_call_timeout: float = MCP_CALL_TIMEOUT,
    ) -> None:
        self.runner = runner
        self.adapter_factory = adapter_factory
        self.import_timeout = float(import_timeout)
        self.call_timeout = float(call_timeout)
        self.mcp_list_timeout = float(mcp_list_timeout)
        self.mcp_call_timeout = float(mcp_call_timeout)

    # ------------------------------------------------------------------ native
    async def check_native(
        self,
        *,
        name: str,
        code: str,
        parameters: Any,
        risk_level: str = "medium",
        sample_arguments: Optional[Mapping[str, Any]] = None,
        sample_call: str = "run",
        skip_reason: Optional[str] = None,
    ) -> ToolCheckResult:
        skip, reason = _skip_decision(risk_level, sample_call, skip_reason)
        started = time.perf_counter()
        result = ToolCheckResult(tool=str(name), lane="native", status=STATUS_PASSED, skip_reason=reason if skip else None)
        try:
            error, warnings = _static_native(str(code or ""))
            result.warnings = warnings
            if error:
                raise _Outcome(STATUS_FAILED, "static", error)
            result.stages.append({"name": "static", "ok": True})

            args: dict[str, Any] = {}
            if not skip:
                if sample_arguments is not None:
                    problem = validate_sample_arguments(parameters, sample_arguments)
                    if problem:
                        raise _Outcome(STATUS_FAILED, "sample_input", problem)
                    args = dict(sample_arguments)
                else:
                    args = build_sample_arguments(parameters)

            await self._sandbox(
                "import",
                files={"runner.py": _IMPORT_RUNNER, "tool.py": code},
                read_outputs=["imported.json"],
                timeout=self.import_timeout,
            )
            result.stages.append({"name": "import", "ok": True})

            if skip:
                result.status = STATUS_SKIPPED_CALL
            else:
                result.sample_arguments = args
                out = await self._sandbox(
                    "sample_call",
                    files={"runner.py": _CHECK_CALL_RUNNER, "tool.py": code, "args.json": json.dumps(args)},
                    read_outputs=["result.json"],
                    timeout=self.call_timeout,
                )
                raw = (out.output_files or {}).get("result.json") or ""
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    raise _Outcome(STATUS_FAILED, "sample_call", "run() did not leave a JSON result")
                if not isinstance(parsed, dict) or not parsed.get("ok"):
                    raise _Outcome(STATUS_FAILED, "sample_call", "run() did not return a result")
                result.stages.append({"name": "sample_call", "ok": True})
        except _Outcome as outcome:
            _mark(result, outcome)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.checked_at = _now_iso()
        logger.info("Tool check %s (native): %s %s", name, result.status, result.stage or "")
        return result

    async def _sandbox(self, stage: str, *, files: dict[str, str], read_outputs: list[str], timeout: float) -> SubprocessResult:
        runner = self.runner or SandboxedSubprocessWorker.run_sandboxed
        try:
            out = await runner(
                [sys.executable, "runner.py"],
                timeout_seconds=timeout,
                files=files,
                read_outputs=read_outputs,
                drop_env_prefixes=_DROP_ENV_PREFIXES,
            )
        except Exception as exc:  # the sandbox itself did not start
            raise _Outcome(STATUS_COULD_NOT_RUN, stage, f"{type(exc).__name__}: {exc}")
        error = str(getattr(out, "error", "") or "")
        if error.startswith("Subprocess launch error") or error.startswith("Security violation"):
            raise _Outcome(STATUS_COULD_NOT_RUN, stage, error)
        if "timed out" in error.lower():
            raise _Outcome(STATUS_FAILED, stage, f"timed out after {timeout:g} s")
        if not getattr(out, "success", False):
            raise _Outcome(STATUS_FAILED, stage, trim_error(out.stderr or error or out.stdout))
        missing = [name for name in read_outputs if name not in (out.output_files or {})]
        if missing:
            raise _Outcome(STATUS_FAILED, stage, f"the tool exited without writing {missing[0]}")
        return out

    # --------------------------------------------------------------------- mcp
    async def check_mcp(
        self,
        *,
        name: str,
        command: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
        transport: str = "stdio",
        url: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        sample_arguments: Optional[Mapping[str, Any]] = None,
        sample_tool: Optional[str] = None,
        sample_call: str = "run",
        skip_reason: Optional[str] = None,
    ) -> ToolCheckResult:
        skip, reason = _skip_decision("medium", sample_call, skip_reason)
        started = time.perf_counter()
        result = ToolCheckResult(tool=str(name), lane="mcp", status=STATUS_PASSED, skip_reason=reason if skip else None)
        adapter = None
        try:
            try:
                factory = self.adapter_factory
                if factory is None:
                    from src.infrastructure.mcp.client_adapter import MCPClientAdapter as factory  # noqa: N813
                adapter = factory(
                    server_name=str(name),
                    command=command,
                    env=env,
                    timeout_seconds=self.mcp_list_timeout,
                    transport=transport,
                    url=url,
                    headers=headers,
                )
            except Exception as exc:
                raise _Outcome(STATUS_COULD_NOT_RUN, "list", f"{type(exc).__name__}: {exc}")

            try:
                raw_tools = await adapter.list_tools_raw()
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                tail = _exited_stderr(adapter)
                if tail and tail not in detail:
                    detail = f"{detail}\n{tail}"
                raise _Outcome(STATUS_FAILED, "list", trim_error(f"server did not answer tools/list: {detail}"))
            if not raw_tools:
                raise _Outcome(STATUS_FAILED, "list", "the server listed no tools")
            names: list[str] = []
            schemas: dict[str, Any] = {}
            for item in raw_tools:
                tool_name = item.get("name") if isinstance(item, Mapping) else None
                if not isinstance(tool_name, str) or not _MCP_TOOL_NAME_RE.match(tool_name):
                    raise _Outcome(STATUS_FAILED, "list", f"tool '{tool_name}' has an invalid name (letters, digits, _ and - only)")
                schema = item.get("inputSchema")
                if not isinstance(schema, Mapping) or schema.get("type") != "object":
                    raise _Outcome(STATUS_FAILED, "list", f"tool '{tool_name}' inputSchema must be a JSON object schema")
                names.append(tool_name)
                schemas[tool_name] = schema
            result.stages.append({"name": "list", "ok": True, "tools": names})

            if skip:
                result.status = STATUS_SKIPPED_CALL
            else:
                chosen = names[0]
                if sample_tool:
                    wanted = str(sample_tool)
                    prefix = f"mcp_{name}_"
                    if wanted.startswith(prefix):
                        wanted = wanted[len(prefix):]
                    if wanted not in names:
                        raise _Outcome(STATUS_FAILED, "sample_call", f"sample_tool '{sample_tool}' is not one of: {', '.join(names)}")
                    chosen = wanted
                result.sample_tool = chosen
                if sample_arguments is not None:
                    problem = validate_sample_arguments(schemas[chosen], sample_arguments)
                    if problem:
                        raise _Outcome(STATUS_FAILED, "sample_input", problem)
                    args = dict(sample_arguments)
                else:
                    args = build_sample_arguments(schemas[chosen])
                result.sample_arguments = args
                adapter.timeout_seconds = self.mcp_call_timeout
                reply = await adapter.call_tool(chosen, args)
                if not isinstance(reply, Mapping) or not reply.get("success"):
                    error = reply.get("error") if isinstance(reply, Mapping) else reply
                    raise _Outcome(STATUS_FAILED, "sample_call", trim_error(error or "the sample call failed"))
                proc = getattr(adapter, "_proc", None)
                if proc is not None and proc.poll() is not None:
                    raise _Outcome(STATUS_FAILED, "sample_call", f"the server exited during the sample call (exit code {proc.poll()})")
                result.stages.append({"name": "sample_call", "ok": True})
        except _Outcome as outcome:
            _mark(result, outcome)
        finally:
            if adapter is not None:
                try:
                    await adapter.close()
                except Exception:
                    logger.debug("Tool check adapter close failed for %s", name, exc_info=True)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.checked_at = _now_iso()
        logger.info("Tool check %s (mcp): %s %s", name, result.status, result.stage or "")
        return result


def _skip_decision(risk_level: str, sample_call: str, skip_reason: Optional[str]) -> tuple[bool, Optional[str]]:
    mode = str(sample_call or "run").strip().lower()
    if mode not in {"run", "skip"}:
        raise ValueError("sample_call must be 'run' or 'skip'")
    reason = str(skip_reason or "").strip()
    if mode == "skip" and not reason:
        raise ValueError("skip_reason is required when sample_call is 'skip'")
    if str(risk_level or "").strip().lower() == "high":
        return True, HIGH_RISK_SKIP_REASON
    if mode == "skip":
        return True, reason
    return False, None


def _mark(result: ToolCheckResult, outcome: _Outcome) -> None:
    result.status = outcome.status
    result.stage = outcome.stage
    result.error = outcome.error
    result.stages.append({"name": outcome.stage, "ok": False})


def _exited_stderr(adapter: Any) -> str:
    proc = getattr(adapter, "_proc", None)
    if proc is None or proc.poll() is None or proc.stderr is None:
        return ""
    try:
        text = proc.stderr.read() or ""
        return trim_error(text, 600) if text.strip() else ""
    except Exception:
        return ""


def record_check_on_job(store: Any, result: ToolCheckResult) -> None:
    """Keep the check on the Tools Studio mediation job, when the chat has one [REQ-511-010]."""
    ctx = get_tool_context()
    job_id = str(ctx.get("job_id") or "").strip()
    if not job_id or store is None:
        return
    try:
        job = store.get_job(job_id)
        if job is None or getattr(job, "template_id", None) != MEDIATION_TEMPLATE_ID:
            return
        payload = result.to_dict()
        payload["session_id"] = ctx.get("session_id")
        store.save_standing_journey_event(job_id=job_id, kind=CHECK_EVENT_KIND, payload=payload)
        phases = list(store.list_phases_for_job(job_id) or [])
        saver = getattr(store, "save_job_phase_checkpoint", None)
        if phases and callable(saver):
            phase = phases[0]
            saver(
                job_id=job_id,
                phase_id=phase.id,
                phase_index=int(getattr(phase, "index", 0) or 0),
                verifier_status=_VERIFIER_STATUS.get(result.status, "failed"),
            )
    except Exception:
        logger.exception("Could not record the tool check on job %s", job_id)


def tool_checks_for_job(store: Any, job_id: str) -> list[dict[str, Any]]:
    lister = getattr(store, "list_standing_journey_events", None)
    if not callable(lister):
        return []
    try:
        events = lister(job_id) or []
    except Exception:
        return []
    return [dict(event.get("payload") or {}) for event in events if event.get("kind") == CHECK_EVENT_KIND]
