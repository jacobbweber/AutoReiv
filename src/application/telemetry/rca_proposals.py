"""Staged Root Cause Analysis (RCA) self-healing proposals for recurring tool and routine failures [CARD-704].

Adapted from Crucible (`ADR-0008`, `ADR-0014`, `rca_stager.py`):
- Aggregates recurring tool and routine failures from `telemetry_spans` without silently mutating code.
- Resolves Agora skill folder coordinates (`skill_id`, `tools/<tool_name>.py`) and current source code.
- Stages structured RCA proposals (`id`, `severity`, `kind`, `target_name`, `skill_id`, `file_path`,
  `failure_count`, `total_calls`, `latest_error`, `trace_ids`, `session_ids`, `sample_arguments`,
  `suggested_remediation`, `repair_tool`, `repair_prompt`).
- Auto-resolves proposals when a newer execution succeeds, when the tool is repaired via `save_skill_file`,
  or when the operator dismisses the proposal (`POST /api/telemetry/rca-proposals/{id}/dismiss`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.skills.agora_loader import list_skill_colocated_tools
from src.application.telemetry.span_waterfall import scrub_text
from src.domain.telemetry.models import utc_now
from src.infrastructure.content import store as content_store_mod

RCA_DISMISSED_SETTINGS_KEY = "rca_dismissed_proposals"


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _ensure_utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def load_dismissed_map(store: Any) -> Dict[str, str]:
    """Return `{proposal_id: iso_timestamp}` from SQLite `system_settings`."""
    if store is None or not hasattr(store, "get_setting"):
        return {}
    raw = store.get_setting(RCA_DISMISSED_SETTINGS_KEY)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items() if k and v}
    except (ValueError, TypeError):
        pass
    return {}


def save_dismissed_map(store: Any, mapping: Dict[str, str]) -> None:
    """Persist `{proposal_id: iso_timestamp}` into SQLite `system_settings`."""
    if store is None or not hasattr(store, "set_setting"):
        return
    store.set_setting(RCA_DISMISSED_SETTINGS_KEY, json.dumps(mapping, sort_keys=True))


def mark_rca_proposal_resolved(store: Any, proposal_id: str) -> Dict[str, Any]:
    """Record a dismissal/resolution timestamp for `proposal_id`."""
    clean_id = str(proposal_id or "").strip()
    if not clean_id:
        raise ValueError("proposal_id is required")
    mapping = load_dismissed_map(store)
    now_iso = utc_now().isoformat()
    mapping[clean_id] = now_iso
    save_dismissed_map(store, mapping)
    return {"id": clean_id, "dismissed": True, "dismissed_at": now_iso}


def mark_tool_rca_resolved(store: Any, tool_name: str) -> None:
    """Mark `rca:tool:<tool_name>` resolved when `save_skill_file` updates the tool."""
    clean_tool = str(tool_name or "").strip()
    if not clean_tool or store is None:
        return
    mark_rca_proposal_resolved(store, f"rca:tool:{clean_tool}")


class RcaProposalService:
    """Synthesizes staged RCA self-healing proposals from failed tool and routine spans [CARD-704]."""

    def __init__(self, store: Any, content_store: Any = None):
        self.store = store
        self.content_store = content_store or content_store_mod.get_store()

    def _locate_skill_tool(self, tool_name: str) -> Dict[str, Optional[str]]:
        """Find if `tool_name` is a colocated `tools/<tool_name>.py` inside an Agora skill folder."""
        clean_name = str(tool_name or "").strip()
        if not clean_name or self.content_store is None:
            return {"skill_id": None, "file_path": None, "code": None}
        try:
            skills = self.content_store.skills.list(include_hidden=True)
        except Exception:
            skills = []
        for skill in skills:
            try:
                colocated = list_skill_colocated_tools(self.content_store, skill.id)
            except Exception:
                continue
            for spec in colocated:
                if spec.get("name") == clean_name:
                    rel_path = f"tools/{clean_name}.py"
                    code = None
                    abs_path = spec.get("path")
                    if abs_path:
                        try:
                            from pathlib import Path

                            p = Path(str(abs_path))
                            if p.is_file():
                                code = p.read_text(encoding="utf-8")
                        except Exception:
                            code = None
                    return {
                        "skill_id": skill.id,
                        "file_path": rel_path,
                        "code": code,
                    }
        return {"skill_id": None, "file_path": None, "code": None}

    def list_proposals(self, min_failures: int = 1, limit: int = 25) -> List[Dict[str, Any]]:
        """Aggregate active failing tool and routine spans into staged RCA proposals."""
        if self.store is None or not hasattr(self.store, "get_telemetry_spans"):
            return []

        spans = self.store.get_telemetry_spans(limit=2000)
        dismissed_map = load_dismissed_map(self.store)

        grouped: Dict[tuple[str, str], List[Any]] = {}
        for span in spans:
            st = str(getattr(span, "span_type", "") or "").strip().lower()
            meta = getattr(span, "metadata", None) or {}
            if st == "tool":
                kind = "tool"
                target = str(getattr(span, "name", "") or "").strip()
            elif st == "routine" or (isinstance(meta, dict) and meta.get("routine_id")):
                kind = "routine"
                target = str(getattr(span, "name", "") or meta.get("routine_id") or "").strip()
            else:
                continue
            if not target:
                continue
            grouped.setdefault((kind, target), []).append(span)

        proposals: List[Dict[str, Any]] = []
        for (kind, target_name), item_spans in grouped.items():
            # Sort newest first
            ordered = sorted(
                item_spans,
                key=lambda s: _ensure_utc(getattr(s, "created_at", None)),
                reverse=True,
            )
            if not ordered:
                continue

            newest = ordered[0]
            newest_failed = (not bool(getattr(newest, "success", True))) or (
                str(getattr(newest, "status", "ok") or "ok").lower() == "error"
            )
            if not newest_failed:
                # Most recent execution succeeded -> capability is healthy
                continue

            proposal_id = f"rca:{kind}:{target_name}"
            dismissed_dt = _parse_iso(dismissed_map.get(proposal_id))

            # Collect consecutive failures since the last success (and after any dismissal)
            recent_failures: List[Any] = []
            for s in ordered:
                s_dt = _ensure_utc(getattr(s, "created_at", None))
                if dismissed_dt is not None and s_dt <= dismissed_dt:
                    break
                is_fail = (not bool(getattr(s, "success", True))) or (
                    str(getattr(s, "status", "ok") or "ok").lower() == "error"
                )
                if not is_fail:
                    break
                recent_failures.append(s)

            failure_count = len(recent_failures)
            if failure_count < max(1, int(min_failures or 1)):
                continue

            total_calls = len(ordered)
            latest_span = recent_failures[0]
            latest_error = scrub_text(
                str(getattr(latest_span, "error_message", None) or "Execution failed without error message")
            )
            latest_ts = _ensure_utc(getattr(latest_span, "created_at", None)).isoformat()

            trace_ids: List[str] = []
            session_ids: List[str] = []
            agent_ids: List[str] = []
            sample_arguments: Dict[str, Any] = {}

            for fspan in recent_failures:
                tid = str(getattr(fspan, "trace_id", None) or getattr(fspan, "id", "") or "").strip()
                if tid and tid not in trace_ids and len(trace_ids) < 5:
                    trace_ids.append(tid)
                sid = str(getattr(fspan, "session_id", None) or "").strip()
                if sid and sid not in session_ids and len(session_ids) < 5:
                    session_ids.append(sid)
                aid = str(getattr(fspan, "agent_id", None) or "").strip()
                if aid and aid not in agent_ids and len(agent_ids) < 5:
                    agent_ids.append(aid)
                if not sample_arguments:
                    meta = getattr(fspan, "metadata", None) or {}
                    if isinstance(meta, dict) and isinstance(meta.get("arguments"), dict):
                        sample_arguments = dict(meta["arguments"])

            if failure_count >= 3:
                severity = "critical"
            elif failure_count >= 2:
                severity = "high"
            else:
                severity = "warning"

            loc = self._locate_skill_tool(target_name) if kind == "tool" else {
                "skill_id": None,
                "file_path": None,
                "code": None,
            }
            skill_id = loc["skill_id"]
            file_path = loc["file_path"]
            current_code = loc["code"]

            if kind == "tool" and not (skill_id and file_path):
                # Only stage self-repair proposals for colocated Agora skill tools or runtime-built native tools.
                # Built-in platform tools (e.g. register_native_tool, wiki_note_update) failing on caller validation
                # are caller input errors, not broken tool implementations.
                from src.application.tools.native_packaging import load_native_tool_names

                if target_name not in load_native_tool_names(self.store):
                    continue

            primary_trace = trace_ids[0] if trace_ids else "unknown"
            if kind == "tool" and skill_id and file_path:
                repair_tool = "write_skill_file"
                suggested_remediation = (
                    f"Inspect trace {primary_trace} and update {file_path} in skill '{skill_id}' "
                    f"via write_skill_file so `{target_name}` handles the failing input cleanly."
                )
                repair_prompt = (
                    f"Please repair the failing Agora skill tool `{target_name}` in skill `{skill_id}` (`{file_path}`).\n\n"
                    f"Telemetry RCA Evidence:\n"
                    f"- Proposal ID: `{proposal_id}`\n"
                    f"- Failure Count: {failure_count} (latest trace: `{primary_trace}`)\n"
                    f"- Latest Error: `{latest_error}`\n"
                    f"- Failing Arguments: `{json.dumps(sample_arguments, sort_keys=True)}`\n"
                    + (
                        f"\nCurrent `{file_path}` source:\n```python\n{current_code.strip()}\n```\n"
                        if current_code
                        else ""
                    )
                    + f"\nCall `write_skill_file` now with `skill_id=\"{skill_id}\"`, `path=\"{file_path}\"`, "
                    f"and the fixed Python code (keeping `RISK = \"read_only\"` and a typed `def run(...) -> dict:` "
                    f"entrypoint that handles this edge case without raising `{latest_error.split(':')[0]}`)."
                )
            elif kind == "tool":
                repair_tool = "write_skill_file"
                suggested_remediation = (
                    f"Inspect trace {primary_trace} and repair tool `{target_name}` via write_skill_file "
                    f"or register_native_tool to prevent `{latest_error}`."
                )
                repair_prompt = (
                    f"Please diagnose and repair the failing tool `{target_name}`.\n\n"
                    f"Telemetry RCA Evidence:\n"
                    f"- Proposal ID: `{proposal_id}`\n"
                    f"- Failure Count: {failure_count} (latest trace: `{primary_trace}`)\n"
                    f"- Latest Error: `{latest_error}`\n"
                    f"- Failing Arguments: `{json.dumps(sample_arguments, sort_keys=True)}`\n\n"
                    f"Inspect the skill/tool definition and update it via `write_skill_file` (or `register_native_tool`) "
                    f"so it handles this input cleanly without failing."
                )
            else:
                repair_tool = "routine_update"
                suggested_remediation = (
                    f"Inspect routine `{target_name}` (trace {primary_trace}) and remediate recurring error: {latest_error}."
                )
                repair_prompt = (
                    f"Please diagnose the failing routine `{target_name}`.\n\n"
                    f"Telemetry RCA Evidence:\n"
                    f"- Proposal ID: `{proposal_id}`\n"
                    f"- Failure Count: {failure_count} (latest trace: `{primary_trace}`)\n"
                    f"- Latest Error: `{latest_error}`\n\n"
                    f"Explain the root cause and propose or apply the fix."
                )

            proposals.append(
                {
                    "id": proposal_id,
                    "kind": kind,
                    "target_name": target_name,
                    "skill_id": skill_id,
                    "file_path": file_path,
                    "severity": severity,
                    "status": "staged",
                    "failure_count": failure_count,
                    "total_calls": total_calls,
                    "latest_error": latest_error,
                    "latest_timestamp": latest_ts,
                    "trace_ids": trace_ids,
                    "session_ids": session_ids,
                    "agent_ids": agent_ids,
                    "sample_arguments": sample_arguments,
                    "suggested_remediation": suggested_remediation,
                    "repair_tool": repair_tool,
                    "repair_prompt": repair_prompt,
                }
            )

        proposals.sort(
            key=lambda p: (p["failure_count"], p["latest_timestamp"]),
            reverse=True,
        )
        return proposals[: max(1, int(limit or 25))]

    def dismiss_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Dismiss a staged RCA proposal until a newer failure occurs."""
        return mark_rca_proposal_resolved(self.store, proposal_id)
