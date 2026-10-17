"""Per-turn and per-job hierarchical span waterfall tracing and credential scrubbing [CARD-700].

Adapted from Agent-OS (`agent_os/trace.py`, `agent_os/redact.py`) and Crucible (`ADR-0008`):
- Scrubs API keys, Bearer tokens, and sensitive dictionary keys (`scrub_text`, `scrub_value`).
- Provides `TraceWriter`, `load_spans`, and `format_trace` for OpenTelemetry-shaped JSONL traces.
- Synthesizes and persists hierarchical parent-child span waterfalls (`turn` -> `user_input`,
  `compaction`, `model_request` -> `model_response`, `tool_call` -> `tool_result`, `final_answer`)
  under `<data_dir>/traces/<trace_id>.jsonl` and exposes them to the UI and `/api/traces`.
"""

from __future__ import annotations

import json
import re
import secrets
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.infrastructure.data.resolver import DataDirResolver

MINIMUM_SECRET_LENGTH = 8

_SENSITIVE_KEY_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "access_token",
        "refresh_token",
        "client_secret",
        "private_key",
    }
)

_INLINE_SECRET_RES = (
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]{8,}|AIza[A-Za-z0-9_-]{10,})\b"),
    re.compile(r"(?i)\b((?:token|api_key|apikey|secret|password)\s*[:=]\s*)[^\s,;\"']{8,}"),
)


def scrub_text(text: str, secret: str = "") -> str:
    """Remove configured secrets and common credential patterns from text."""
    if not text:
        return ""
    out = str(text)
    if secret and len(secret) >= MINIMUM_SECRET_LENGTH and secret in out:
        out = out.replace(secret, "[redacted]")
    out = _INLINE_SECRET_RES[0].sub(r"\1[redacted]", out)
    out = _INLINE_SECRET_RES[1].sub("[redacted]", out)
    out = _INLINE_SECRET_RES[2].sub(r"\1[redacted]", out)
    return out


def scrub_value(value: object, secret: str = "") -> object:
    """Recursively scrub credentials from strings, dicts, and lists."""
    if isinstance(value, str):
        return scrub_text(value, secret)
    if isinstance(value, Mapping):
        cleaned: dict[str, object] = {}
        for k, v in value.items():
            key_str = str(k)
            key_lower = key_str.lower()
            if key_lower in _SENSITIVE_KEY_NAMES:
                cleaned[key_str] = "[redacted]" if v else ""
            elif key_lower == "authorization" and isinstance(v, str):
                cleaned[key_str] = scrub_text(v, secret) if "bearer " in v.lower() else "[redacted]"
            else:
                cleaned[key_str] = scrub_value(v, secret)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [scrub_value(item, secret) for item in value]
    return value


def traces_dir(store: Any = None) -> Path | None:
    """Return `<data_dir>/traces` inside the resolved AutoReiv data root, or None for in-memory test stores."""
    import os

    db_path = getattr(store, "db_path", None) if store is not None else None
    if isinstance(db_path, (str, Path)) and str(db_path) != ":memory:":
        p = Path(db_path).resolve()
        root = p.parent.parent if p.parent.name == "database" else p.parent
    elif os.environ.get("AUTOREIV_DATA_DIR"):
        root = Path(os.environ["AUTOREIV_DATA_DIR"]).resolve()
    elif store is not None and str(db_path) == ":memory:":
        return None
    else:
        resolved = DataDirResolver().resolve()
        root = getattr(resolved, "root", resolved)
    d = Path(root) / "traces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_trace_filename(trace_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(trace_id or "trace")).strip("_")
    return f"{cleaned or 'trace'}.jsonl"


def _unix_nano(moment: datetime) -> str:
    return str(int(moment.timestamp() * 1_000_000_000))


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class SpanState:
    def __init__(self, attributes: dict[str, object]) -> None:
        self.attributes = attributes
        self.status = "ok"
        self.error = ""

    def fail(self, error: str) -> None:
        self.status = "error"
        if not self.error:
            self.error = error


class TraceWriter:
    """Context-managed hierarchical span recorder writing JSONL traces."""

    def __init__(self, path: Path | None = None, *, trace_id: str, cover: str = "") -> None:
        self.trace_id = trace_id
        self.cover = cover
        self.path = path if path is not None else (traces_dir() / _safe_trace_filename(trace_id))
        self.completed: list[dict[str, Any]] = []
        self._stack: list[str] = []
        self._seq = 0

    @contextmanager
    def span(self, name: str, **attributes: object) -> Iterator[SpanState]:
        state = SpanState(dict(attributes))
        span_id = secrets.token_hex(8)
        parent = self._stack[-1] if self._stack else None
        self._stack.append(span_id)
        self._seq += 1
        seq = self._seq
        started = time.perf_counter()
        start_dt = datetime.now(timezone.utc)
        try:
            yield state
        except Exception as exc:
            state.status = "error"
            if not state.error:
                state.error = str(exc)
            raise
        finally:
            self._stack.pop()
            end_dt = datetime.now(timezone.utc)
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            scrubbed_attrs = scrub_value(state.attributes, self.cover)
            ready_attrs = _json_ready(scrubbed_attrs) if isinstance(scrubbed_attrs, Mapping) else {}
            record: dict[str, Any] = {
                "trace_id": self.trace_id,
                "span_id": span_id,
                "parent_span_id": parent,
                "name": name,
                "start_time": start_dt.isoformat(timespec="microseconds"),
                "end_time": end_dt.isoformat(timespec="microseconds"),
                "start_time_unix_nano": _unix_nano(start_dt),
                "end_time_unix_nano": _unix_nano(end_dt),
                "duration_ms": duration_ms,
                "status": state.status,
                "error": scrub_text(state.error, self.cover),
                "attributes": ready_attrs if isinstance(ready_attrs, dict) else {},
                "seq": seq,
            }
            self._write(record)
            self.completed.append(record)

    def _write(self, record: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            handle.flush()


def load_spans(path: Path) -> list[dict[str, Any]]:
    """Read and chronologically sort spans from a JSONL trace file."""
    spans: list[dict[str, Any]] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise TypeError(f"{path} line {idx} is not a span object.")
        attrs = parsed.get("attributes")
        parent = parsed.get("parent_span_id")
        spans.append(
            {
                "trace_id": str(parsed.get("trace_id", "")),
                "span_id": str(parsed.get("span_id", "")),
                "parent_span_id": parent if isinstance(parent, str) and parent else None,
                "name": str(parsed.get("name", "")),
                "start_time": str(parsed.get("start_time", "")),
                "end_time": str(parsed.get("end_time", "")),
                "start_time_unix_nano": str(parsed.get("start_time_unix_nano", "")),
                "end_time_unix_nano": str(parsed.get("end_time_unix_nano", "")),
                "duration_ms": float(parsed.get("duration_ms") or 0.0),
                "status": str(parsed.get("status", "ok")),
                "error": str(parsed.get("error", "")),
                "attributes": dict(attrs) if isinstance(attrs, Mapping) else {},
                "seq": int(parsed.get("seq") or idx),
            }
        )
    spans.sort(key=lambda s: (s.get("seq", 0), s.get("start_time", "")))
    return spans


def _brief(span: Mapping[str, Any]) -> str:
    attrs = span.get("attributes") or {}
    if not isinstance(attrs, Mapping):
        return ""
    bits: list[str] = []
    for key in ("tool", "model", "finish_reason", "outcome"):
        val = attrs.get(key)
        if isinstance(val, str) and val:
            label = "finish" if key == "finish_reason" else key
            bits.append(f"{label}={val}")
    return ("  " + " ".join(bits)) if bits else ""


def format_trace(spans: Sequence[Mapping[str, Any]], *, full: bool = False) -> str:
    """Format a span list as an indented parent-child latency waterfall."""
    if not spans:
        return "No spans in this trace."
    known_ids = {str(s.get("span_id")) for s in spans if s.get("span_id")}
    children: dict[str | None, list[Mapping[str, Any]]] = {}
    for span in spans:
        parent = span.get("parent_span_id")
        parent_key = str(parent) if (isinstance(parent, str) and parent in known_ids) else None
        children.setdefault(parent_key, []).append(span)

    lines: list[str] = []

    def walk(parent: str | None, depth: int) -> None:
        for span in children.get(parent, []):
            indent = "  " * depth
            name = str(span.get("name", "span"))
            dur = float(span.get("duration_ms") or 0.0)
            status = str(span.get("status", "ok"))
            brief = _brief(span)
            lines.append(f"{indent}{name:<16} {dur:>8.1f} ms  {status}{brief}")
            if full:
                details: dict[str, object] = dict(span.get("attributes") or {})
                if span.get("error"):
                    details["error"] = span.get("error")
                rendered = json.dumps(details, ensure_ascii=False, indent=2, default=str)
                pad = indent + "  "
                lines.append(pad + rendered.replace("\n", "\n" + pad))
            walk(str(span.get("span_id", "")), depth + 1)

    walk(None, 0)
    return "\n".join(lines)


def _make_synthetic_span(
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    name: str,
    start_dt: datetime,
    duration_ms: float,
    status: str = "ok",
    error: str = "",
    attributes: Mapping[str, object] | None = None,
    seq: int = 0,
) -> dict[str, Any]:
    dur = round(max(0.0, float(duration_ms or 0.0)), 2)
    end_dt = start_dt + timedelta(milliseconds=dur)
    scrubbed_attrs = scrub_value(dict(attributes or {}))
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "start_time": start_dt.isoformat(timespec="microseconds"),
        "end_time": end_dt.isoformat(timespec="microseconds"),
        "start_time_unix_nano": _unix_nano(start_dt),
        "end_time_unix_nano": _unix_nano(end_dt),
        "duration_ms": dur,
        "status": status,
        "error": scrub_text(error),
        "attributes": scrubbed_attrs if isinstance(scrubbed_attrs, dict) else {},
        "seq": seq,
    }


def _decorate_hierarchy(spans: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    """Attach `depth` and `percent_of_trace` to flat spans and build nested `waterfall` tree."""
    total_ms = sum(
        float(s.get("duration_ms") or 0.0)
        for s in spans
        if s.get("parent_span_id") is None
    )
    if total_ms <= 0:
        total_ms = max((float(s.get("duration_ms") or 0.0) for s in spans), default=1.0)
    denom = max(total_ms, 0.1)

    known_ids = {str(s["span_id"]) for s in spans if s.get("span_id")}
    children_map: dict[str | None, list[dict[str, Any]]] = {}
    for s in spans:
        parent = s.get("parent_span_id")
        parent_key = str(parent) if (isinstance(parent, str) and parent in known_ids) else None
        children_map.setdefault(parent_key, []).append(s)

    ordered: list[dict[str, Any]] = []

    def build_nodes(parent: str | None, depth: int) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for s in children_map.get(parent, []):
            dur = round(float(s.get("duration_ms") or 0.0), 2)
            pct = round(min(100.0, max(1.0 if dur > 0 else 0.0, (dur / denom) * 100.0)), 1)
            enriched = {
                **s,
                "duration_ms": dur,
                "depth": depth,
                "percent_of_trace": pct,
            }
            ordered.append(enriched)
            child_nodes = build_nodes(str(s["span_id"]), depth + 1)
            nodes.append({**enriched, "children": child_nodes})
        return nodes

    tree = build_nodes(None, 0)
    return ordered, tree, round(total_ms, 2)


def _matching_store_spans(store: Any, target_id: str) -> list[Any]:
    if not hasattr(store, "get_telemetry_spans"):
        return []
    all_spans = list(store.get_telemetry_spans(limit=500) or [])
    phase_prefix = f"{target_id}::phase::"
    matched = [
        s
        for s in all_spans
        if (
            s.trace_id == target_id
            or s.session_id == target_id
            or s.id == target_id
            or str(s.session_id or "").startswith(phase_prefix)
            or ((s.metadata or {}).get("step_context") or {}).get("job_id") == target_id
        )
    ]
    # Also include child tool spans whose parent_span_id is in matched turn spans
    turn_ids = {s.id for s in matched if s.span_type == "turn"}
    if turn_ids:
        seen_ids = {s.id for s in matched}
        for s in all_spans:
            if s.id not in seen_ids and s.parent_span_id in turn_ids:
                matched.append(s)
                seen_ids.add(s.id)
    matched.sort(key=lambda s: getattr(s, "created_at", datetime.now(timezone.utc)))
    return matched


def build_trace_waterfall(store: Any, trace_id: str) -> dict[str, Any] | None:
    """Build or load a hierarchical span waterfall for `trace_id` (turn_id, session_id, or job_id)."""
    if not trace_id:
        return None

    matched = _matching_store_spans(store, trace_id)
    t_dir = traces_dir(store)
    trace_file = (t_dir / _safe_trace_filename(trace_id)) if t_dir is not None else None

    if not matched:
        if trace_file is not None and trace_file.is_file():
            disk_spans = load_spans(trace_file)
            ordered, tree, total_ms = _decorate_hierarchy(disk_spans)
            return {
                "trace_id": trace_id,
                "session_id": trace_id,
                "agent_id": (ordered[0].get("attributes") or {}).get("agent_id") if ordered else None,
                "status": "error" if any(s.get("status") == "error" for s in ordered) else "ok",
                "total_duration_ms": total_ms,
                "span_count": len(ordered),
                "spans": ordered,
                "waterfall": tree,
                "formatted_waterfall": format_trace(ordered, full=False),
                "formatted_waterfall_full": format_trace(ordered, full=True),
                "jsonl_path": str(trace_file),
            }
        return None

    turns = [s for s in matched if s.span_type == "turn"]
    tools = [s for s in matched if s.span_type == "tool"]
    handoffs = [s for s in matched if s.span_type == "handoff"]

    tools_by_parent: dict[str | None, list[Any]] = {}
    for t in tools:
        tools_by_parent.setdefault(t.parent_span_id, []).append(t)

    synthesized: list[dict[str, Any]] = []
    seq = 0

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    if not turns:
        # Tool-only or handoff-only spans
        first = matched[0]
        root_id = f"{trace_id}:turn:0"
        base_dt = getattr(first, "created_at", datetime.now(timezone.utc))
        total_dur = sum(float(getattr(s, "duration_ms", 0.0) or 0.0) for s in matched)
        synthesized.append(
            _make_synthetic_span(
                trace_id=trace_id,
                span_id=root_id,
                parent_span_id=None,
                name="turn",
                start_dt=base_dt,
                duration_ms=total_dur,
                status="ok",
                attributes={"session_id": first.session_id, "agent_id": first.agent_id},
                seq=next_seq(),
            )
        )
        for t in tools:
            tc_id = f"{t.id}:call"
            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=tc_id,
                    parent_span_id=root_id,
                    name="tool_call",
                    start_dt=t.created_at,
                    duration_ms=t.duration_ms,
                    status=t.status,
                    error=t.error_message or "",
                    attributes={"tool": t.name, **(t.metadata or {})},
                    seq=next_seq(),
                )
            )
            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=f"{t.id}:result",
                    parent_span_id=tc_id,
                    name="tool_result",
                    start_dt=t.created_at,
                    duration_ms=t.duration_ms,
                    status=t.status,
                    error=t.error_message or "",
                    attributes={
                        "tool": t.name,
                        "outcome": "ok" if t.success else "error",
                        "payload_bytes": (t.metadata or {}).get("payload_bytes", 0),
                    },
                    seq=next_seq(),
                )
            )
    else:
        orphan_tools = list(tools_by_parent.get(None, []))
        for idx, turn in enumerate(turns):
            root_id = turn.id
            meta = scrub_value(turn.metadata or {})
            meta_dict = meta if isinstance(meta, dict) else {}
            token_bd = meta_dict.get("token_breakdown") if isinstance(meta_dict.get("token_breakdown"), dict) else {}
            timing_bd = meta_dict.get("timing_breakdown") if isinstance(meta_dict.get("timing_breakdown"), dict) else {}
            step_ctx = meta_dict.get("step_context") if isinstance(meta_dict.get("step_context"), dict) else {}

            turn_Tools = list(tools_by_parent.get(turn.id, []))
            if idx == len(turns) - 1 and orphan_tools:
                turn_Tools.extend(orphan_tools)
                orphan_tools.clear()

            tool_dur_sum = sum(float(t.duration_ms or 0.0) for t in turn_Tools)
            total_turn_ms = round(float(turn.duration_ms or 0.0) + tool_dur_sum, 2)
            prep_ms = round(float(timing_bd.get("harness_prep_ms") or max(0.5, min(15.0, float(turn.duration_ms or 0.0) * 0.05))), 2)
            gen_ms = round(max(0.5, float(turn.duration_ms or 0.0) - prep_ms), 2)
            start_dt = getattr(turn, "created_at", datetime.now(timezone.utc))

            turn_attrs: dict[str, object] = {
                "session_id": turn.session_id,
                "agent_id": turn.agent_id,
                "model": turn.model,
                "provider": turn.provider,
                "prompt_tokens": turn.prompt_tokens,
                "completion_tokens": turn.completion_tokens,
            }
            if step_ctx.get("job_id"):
                turn_attrs["job_id"] = step_ctx.get("job_id")
            if step_ctx.get("phase_id"):
                turn_attrs["phase_id"] = step_ctx.get("phase_id")
            for k, v in meta_dict.items():
                if k not in ("token_breakdown", "timing_breakdown", "step_context"):
                    turn_attrs[k] = v

            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=root_id,
                    parent_span_id=None,
                    name="turn",
                    start_dt=start_dt,
                    duration_ms=total_turn_ms,
                    status=turn.status,
                    error=turn.error_message or "",
                    attributes=turn_attrs,
                    seq=next_seq(),
                )
            )

            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=f"{root_id}:user_input",
                    parent_span_id=root_id,
                    name="user_input",
                    start_dt=start_dt,
                    duration_ms=round(prep_ms * 0.4, 2),
                    status="ok",
                    attributes={
                        "prompt_tokens": token_bd.get("user_prompt", turn.prompt_tokens),
                        "session_id": turn.session_id,
                    },
                    seq=next_seq(),
                )
            )

            compacted_hist_tokens = int(token_bd.get("compacted_history") or 0)
            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=f"{root_id}:compaction",
                    parent_span_id=root_id,
                    name="compaction",
                    start_dt=start_dt,
                    duration_ms=round(prep_ms * 0.6, 2),
                    status="ok",
                    attributes={
                        "outcome": "active" if compacted_hist_tokens > 0 else "within_budget",
                        "compacted_history_tokens": compacted_hist_tokens,
                    },
                    seq=next_seq(),
                )
            )

            req_id = f"{root_id}:model_request"
            finish_reason = "tool_calls" if turn_Tools else ("stop" if turn.success else "error")
            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=req_id,
                    parent_span_id=root_id,
                    name="model_request",
                    start_dt=start_dt,
                    duration_ms=round(float(turn.duration_ms or 0.0), 2),
                    status=turn.status,
                    error=turn.error_message or "",
                    attributes={
                        "model": turn.model,
                        "provider": turn.provider,
                        "prompt_tokens": turn.prompt_tokens,
                        "active_tool_count": meta_dict.get("active_tool_count", 0),
                    },
                    seq=next_seq(),
                )
            )

            synthesized.append(
                _make_synthetic_span(
                    trace_id=trace_id,
                    span_id=f"{root_id}:model_response",
                    parent_span_id=req_id,
                    name="model_response",
                    start_dt=start_dt,
                    duration_ms=gen_ms,
                    status=turn.status,
                    error=turn.error_message or "",
                    attributes={
                        "model": turn.model,
                        "completion_tokens": turn.completion_tokens,
                        "ttft_ms": turn.ttft_ms,
                        "finish_reason": finish_reason,
                    },
                    seq=next_seq(),
                )
            )

            for t in turn_Tools:
                tc_id = f"{t.id}:tool_call"
                t_meta = scrub_value(t.metadata or {})
                t_meta_dict = t_meta if isinstance(t_meta, dict) else {}
                synthesized.append(
                    _make_synthetic_span(
                        trace_id=trace_id,
                        span_id=tc_id,
                        parent_span_id=root_id,
                        name="tool_call",
                        start_dt=t.created_at,
                        duration_ms=t.duration_ms,
                        status=t.status,
                        error=t.error_message or "",
                        attributes={
                            "tool": t.name,
                            "arguments": t_meta_dict.get("arguments", {}),
                        },
                        seq=next_seq(),
                    )
                )
                synthesized.append(
                    _make_synthetic_span(
                        trace_id=trace_id,
                        span_id=f"{t.id}:tool_result",
                        parent_span_id=tc_id,
                        name="tool_result",
                        start_dt=t.created_at,
                        duration_ms=t.duration_ms,
                        status=t.status,
                        error=t.error_message or "",
                        attributes={
                            "tool": t.name,
                            "outcome": "ok" if t.success else "error",
                            "payload_bytes": t_meta_dict.get("payload_bytes", 0),
                        },
                        seq=next_seq(),
                    )
                )

            for h in handoffs:
                synthesized.append(
                    _make_synthetic_span(
                        trace_id=trace_id,
                        span_id=f"{h.id}:handoff",
                        parent_span_id=root_id,
                        name=h.name,
                        start_dt=h.created_at,
                        duration_ms=h.duration_ms,
                        status=h.status,
                        error=h.error_message or "",
                        attributes=h.metadata or {},
                        seq=next_seq(),
                    )
                )

            if idx == len(turns) - 1:
                synthesized.append(
                    _make_synthetic_span(
                        trace_id=trace_id,
                        span_id=f"{root_id}:final_answer",
                        parent_span_id=root_id,
                        name="final_answer",
                        start_dt=start_dt,
                        duration_ms=round(max(0.2, gen_ms * 0.1), 2),
                        status=turn.status,
                        error=turn.error_message or "",
                        attributes={
                            "finish_reason": "stop" if turn.success else "error",
                            "completion_tokens": turn.completion_tokens,
                        },
                        seq=next_seq(),
                    )
                )

    ordered, tree, total_ms = _decorate_hierarchy(synthesized)

    # Persist credential-scrubbed JSONL trace file under <data_dir>/traces/
    if trace_file is not None:
        try:
            trace_file.parent.mkdir(parents=True, exist_ok=True)
            with trace_file.open("w", encoding="utf-8") as fh:
                for item in ordered:
                    fh.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass

    first_span = matched[0]
    overall_status = "error" if any(not getattr(s, "success", True) for s in matched) else "ok"
    return {
        "trace_id": trace_id,
        "session_id": getattr(first_span, "session_id", None) or trace_id,
        "agent_id": getattr(first_span, "agent_id", None),
        "status": overall_status,
        "total_duration_ms": total_ms,
        "span_count": len(ordered),
        "spans": ordered,
        "waterfall": tree,
        "formatted_waterfall": format_trace(ordered, full=False),
        "formatted_waterfall_full": format_trace(ordered, full=True),
        "jsonl_path": str(trace_file) if trace_file is not None else "",
    }


def list_traces(store: Any, *, session_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List recent traces grouped by trace_id / session_id."""
    if not hasattr(store, "get_telemetry_spans"):
        return []
    raw_spans = list(store.get_telemetry_spans(session_id=session_id, limit=max(limit * 10, 200)) or [])
    grouped: dict[str, list[Any]] = {}
    for s in raw_spans:
        tid = str(s.trace_id or s.session_id or s.id)
        grouped.setdefault(tid, []).append(s)

    items: list[dict[str, Any]] = []
    for tid, group in grouped.items():
        turns = [s for s in group if s.span_type == "turn"]
        tools = [s for s in group if s.span_type == "tool"]
        latest = max(group, key=lambda s: getattr(s, "created_at", datetime.now(timezone.utc)))
        total_dur = round(sum(float(s.duration_ms or 0.0) for s in group), 1)
        status = "error" if any(not s.success for s in group) else "ok"
        items.append(
            {
                "trace_id": tid,
                "session_id": getattr(latest, "session_id", None),
                "agent_id": getattr(latest, "agent_id", None),
                "model": turns[0].model if turns else getattr(latest, "model", None),
                "status": status,
                "duration_ms": total_dur,
                "turn_count": len(turns),
                "tool_count": len(tools),
                "span_count": len(group),
                "created_at": latest.created_at.isoformat()
                if hasattr(latest.created_at, "isoformat")
                else str(latest.created_at),
            }
        )
        if len(items) >= limit:
            break
    return items
