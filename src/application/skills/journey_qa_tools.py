"""CARD-632: read CARD-532 live QA journey reports (no run, no browser, no live data)."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry

DEFAULT_REPORT_DIRNAME = "autoreiv-qa"
MAX_LIST = 50
MAX_FAILURE_LINES = 40


def default_report_root() -> Path:
    """CARD-532 report root: AUTOREIV_QA_REPORT_DIR or <temp>/autoreiv-qa."""
    env = str(os.environ.get("AUTOREIV_QA_REPORT_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(tempfile.gettempdir()) / DEFAULT_REPORT_DIRNAME).resolve()


def _jail(root: Path, rel: str) -> Path:
    root = root.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Refusing path outside the journey report root: {rel}") from exc
    return target


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    except OSError:
        return ""


def _load_report(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("report.json must be an object")
    return data


def _resolve_report_file(root: Path, card_or_path: str) -> Path:
    key = (card_or_path or "").strip().replace("\\", "/")
    if not key:
        raise ValueError("card_or_path is required (folder name under the report root, e.g. card-621)")
    if key.endswith("report.json"):
        return _jail(root, key)
    # bare folder name or relative folder
    candidate = _jail(root, key)
    if candidate.is_dir():
        return candidate / "report.json"
    if candidate.is_file():
        return candidate
    # also try card- prefix normalize
    if not key.startswith("card-") and key.lower().startswith("card"):
        pass
    raise FileNotFoundError(f"No report.json under {key}")


def _run_failures(run: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if str(run.get("outcome") or "").lower() == "fail":
        steps = run.get("steps") or []
        failed_steps = [s for s in steps if isinstance(s, dict) and str(s.get("status") or "").lower() == "fail"]
        if not failed_steps and steps:
            failed_steps = [steps[-1]] if isinstance(steps[-1], dict) else []
        if not failed_steps:
            out.append(
                {
                    "journey": str(run.get("journey") or ""),
                    "viewport": str(run.get("viewport") or ""),
                    "step": "(run failed)",
                    "reason": "no failing step recorded",
                    "screenshot": "",
                }
            )
        for s in failed_steps:
            out.append(
                {
                    "journey": str(run.get("journey") or ""),
                    "viewport": str(run.get("viewport") or ""),
                    "step": str(s.get("step") or ""),
                    "reason": str(s.get("reason") or ""),
                    "screenshot": str(s.get("screenshot") or ""),
                }
            )
    for note in run.get("consoleErrors") or []:
        out.append(
            {
                "journey": str(run.get("journey") or ""),
                "viewport": str(run.get("viewport") or ""),
                "step": "console error",
                "reason": str(note)[:300],
                "screenshot": "",
            }
        )
    for note in run.get("failedRequests") or []:
        out.append(
            {
                "journey": str(run.get("journey") or ""),
                "viewport": str(run.get("viewport") or ""),
                "step": "failed request",
                "reason": str(note)[:300],
                "screenshot": "",
            }
        )
    return out


class JourneyQaTools:
    """Read-only access to CARD-532 journey report folders."""

    def __init__(self, report_root: Optional[Path] = None):
        self._root = Path(report_root).resolve() if report_root else default_report_root()

    @property
    def report_root(self) -> Path:
        return self._root

    def list_journey_reports(self, limit: int = 20) -> Dict[str, Any]:
        limit = max(1, min(int(limit or 20), MAX_LIST))
        root = self._root
        if not root.is_dir():
            return {
                "success": True,
                "report_root": str(root),
                "reports": [],
                "note": "Report root does not exist yet (no live QA runs on this machine).",
            }
        rows: List[Dict[str, Any]] = []
        for child in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
            if not child.is_dir():
                continue
            report = child / "report.json"
            if not report.is_file():
                continue
            try:
                data = _load_report(report)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                rows.append(
                    {
                        "card": child.name,
                        "path": str(report),
                        "mtime": _mtime_iso(report),
                        "error": str(exc)[:200],
                    }
                )
                continue
            runs = data.get("runs") if isinstance(data.get("runs"), list) else []
            outcomes = [str(r.get("outcome") or "") for r in runs if isinstance(r, dict)]
            failed = sum(1 for o in outcomes if o.lower() == "fail")
            rows.append(
                {
                    "card": child.name,
                    "path": str(report),
                    "mtime": _mtime_iso(report),
                    "title": str(data.get("title") or ""),
                    "started_at": str(data.get("startedAt") or ""),
                    "run_count": len(runs),
                    "outcomes": outcomes,
                    "failed_runs": failed,
                    "overall": "fail" if failed else ("pass" if outcomes else "unknown"),
                }
            )
            if len(rows) >= limit:
                break
        return {"success": True, "report_root": str(root), "reports": rows}

    def read_journey_report(self, card_or_path: str) -> Dict[str, Any]:
        try:
            path = _resolve_report_file(self._root, card_or_path)
        except (ValueError, FileNotFoundError) as exc:
            return {"success": False, "error": str(exc), "report_root": str(self._root)}
        if not path.is_file():
            return {"success": False, "error": f"Missing report: {path}", "report_root": str(self._root)}
        try:
            data = _load_report(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {"success": False, "error": f"Could not read report: {exc}", "path": str(path)}
        runs = data.get("runs") if isinstance(data.get("runs"), list) else []
        slim_runs = []
        for r in runs:
            if not isinstance(r, dict):
                continue
            steps = r.get("steps") if isinstance(r.get("steps"), list) else []
            slim_runs.append(
                {
                    "journey": r.get("journey"),
                    "viewport": r.get("viewport"),
                    "outcome": r.get("outcome"),
                    "step_count": len(steps),
                    "failing_steps": [
                        {"step": s.get("step"), "reason": s.get("reason"), "screenshot": s.get("screenshot")}
                        for s in steps
                        if isinstance(s, dict) and str(s.get("status") or "").lower() == "fail"
                    ],
                    "console_errors": list(r.get("consoleErrors") or [])[:10],
                    "failed_requests": list(r.get("failedRequests") or [])[:10],
                }
            )
        summary_md = path.parent / "summary.md"
        summary_text = ""
        if summary_md.is_file():
            summary_text = summary_md.read_text(encoding="utf-8", errors="replace")[:4000]
        return {
            "success": True,
            "path": str(path),
            "report_root": str(self._root),
            "title": data.get("title"),
            "started_at": data.get("startedAt"),
            "base": data.get("base"),
            "runs": slim_runs,
            "summary_md": summary_text,
        }

    def summarize_journey_failures(self, card_or_path: str) -> Dict[str, Any]:
        read = self.read_journey_report(card_or_path)
        if not read.get("success"):
            return read
        # Need full steps for reasons — reload
        try:
            path = _resolve_report_file(self._root, card_or_path)
            data = _load_report(path)
        except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
            return {"success": False, "error": str(exc)}
        failures: List[Dict[str, str]] = []
        for r in data.get("runs") or []:
            if isinstance(r, dict):
                failures.extend(_run_failures(r))
        if not failures:
            lines = [
                f"All runs passed for {Path(read['path']).parent.name}.",
                f"Runs: {len(read.get('runs') or [])}.",
            ]
            return {
                "success": True,
                "path": read["path"],
                "failed": False,
                "summary": "\n".join(lines),
                "failures": [],
            }
        lines = [f"Found {len(failures)} failure note(s) in {Path(read['path']).parent.name}:"]
        for i, f in enumerate(failures[:MAX_FAILURE_LINES], 1):
            bit = f"{i}. [{f['journey']} / {f['viewport']}] step={f['step']!r}"
            if f["reason"]:
                bit += f" — {f['reason'][:240]}"
            if f["screenshot"]:
                bit += f" (screenshot: {f['screenshot']})"
            lines.append(bit)
        if len(failures) > MAX_FAILURE_LINES:
            lines.append(f"...and {len(failures) - MAX_FAILURE_LINES} more.")
        return {
            "success": True,
            "path": read["path"],
            "failed": True,
            "summary": "\n".join(lines),
            "failures": failures[:MAX_FAILURE_LINES],
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="list_journey_reports",
            description=(
                "List recent CARD-532 live QA journey report folders under the QA report root "
                "(AUTOREIV_QA_REPORT_DIR or <temp>/autoreiv-qa). Read-only; does not start a server or browser."
            ),
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
            },
            handler=self.list_journey_reports,
            risk="read_only",
        )
        registry.register_tool(
            name="read_journey_report",
            description=(
                "Read one CARD-532 journey report.json (and summary.md if present). "
                "Pass a folder name under the report root such as card-621. Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {"card_or_path": {"type": "string"}},
                "required": ["card_or_path"],
            },
            handler=self.read_journey_report,
            risk="read_only",
        )
        registry.register_tool(
            name="summarize_journey_failures",
            description=(
                "Explain failing steps from a CARD-532 journey report in plain words "
                "(journey, viewport, step, reason, screenshot path). Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {"card_or_path": {"type": "string"}},
                "required": ["card_or_path"],
            },
            handler=self.summarize_journey_failures,
            risk="read_only",
        )
