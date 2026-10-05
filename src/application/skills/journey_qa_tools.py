"""CARD-632/633: read CARD-532 live QA journey reports; run journeys throwaway-only with HITL."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry

DEFAULT_REPORT_DIRNAME = "autoreiv-qa"
MAX_LIST = 50
MAX_FAILURE_LINES = 40
DEFAULT_QA_PORT = 8770
FORBIDDEN_QA_PORTS = frozenset({8000})
DEFAULT_RUN_TIMEOUT_S = 1200
MAX_RUN_TIMEOUT_S = 3600
MIN_RUN_TIMEOUT_S = 30


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




def _repo_root() -> Path:
    # src/application/skills/journey_qa_tools.py -> repo root
    return Path(__file__).resolve().parents[3]


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Best-effort kill of a live_qa subprocess (and children on Windows)."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class JourneyQaTools:
    """CARD-532 journey reports (read) and throwaway live QA runs (CARD-633)."""

    _run_lock = threading.Lock()
    _active_proc: Optional[subprocess.Popen] = None

    def __init__(
        self,
        report_root: Optional[Path] = None,
        *,
        checkout: Optional[Path] = None,
        python_exe: Optional[str] = None,
        live_qa_script: Optional[Path] = None,
        run_executor: Optional[Callable[..., Dict[str, Any]]] = None,
    ):
        self._root = Path(report_root).resolve() if report_root else default_report_root()
        self._checkout = Path(checkout).resolve() if checkout else _repo_root()
        self._python = python_exe or sys.executable
        self._live_qa = Path(live_qa_script) if live_qa_script else (self._checkout / "scripts" / "live_qa.py")
        self._run_executor = run_executor  # tests inject a fake runner

    @property
    def report_root(self) -> Path:
        return self._root

    def cancel_active_run(self) -> bool:
        """Kill an in-flight run_journey subprocess (Stop / HITL cancel after start)."""
        proc = JourneyQaTools._active_proc
        if proc is None:
            return False
        _kill_process_tree(proc)
        JourneyQaTools._active_proc = None
        return True

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

    def run_journey(
        self,
        journey_id: str,
        viewports: str = "desktop,phone",
        card: str = "",
        timeout_seconds: int = DEFAULT_RUN_TIMEOUT_S,
        port: int = DEFAULT_QA_PORT,
    ) -> Dict[str, Any]:
        """Start a CARD-532 live QA journey in a throwaway env only (HITL before call).

        Hard rules (CARD-533 D1/D2/D3): never live :8000, never Jacob's AppData, never --data clone.
        """
        jid = str(journey_id or "").strip()
        if not jid:
            return {"success": False, "error": "journey_id is required (e.g. card-623-compact-honest)."}
        if "/" in jid or "\\" in jid or ".." in jid:
            return {"success": False, "error": "journey_id must be a journey file stem, not a path."}
        try:
            port_i = int(port)
        except (TypeError, ValueError):
            return {"success": False, "error": f"Invalid port: {port}"}
        if port_i in FORBIDDEN_QA_PORTS:
            return {
                "success": False,
                "error": f"Port {port_i} is Jacob's live serve; journey runs use the CARD-532 throwaway port (default {DEFAULT_QA_PORT}).",
            }
        try:
            timeout = int(timeout_seconds or DEFAULT_RUN_TIMEOUT_S)
        except (TypeError, ValueError):
            timeout = DEFAULT_RUN_TIMEOUT_S
        timeout = max(MIN_RUN_TIMEOUT_S, min(timeout, MAX_RUN_TIMEOUT_S))
        vps = str(viewports or "desktop,phone").strip() or "desktop,phone"
        card_folder = str(card or "").strip() or ("-".join(jid.split("-")[:2]) if jid.startswith("card-") else jid)

        if self._run_executor is not None:
            return self._run_executor(
                journey_id=jid,
                viewports=vps,
                card=card_folder,
                timeout_seconds=timeout,
                port=port_i,
                data="throwaway",
            )

        if not self._live_qa.is_file():
            return {"success": False, "error": f"live_qa.py not found at {self._live_qa}"}

        if not JourneyQaTools._run_lock.acquire(blocking=False):
            return {"success": False, "error": "Another journey run is already in progress; wait or cancel it."}

        out_dir = self._root / card_folder
        cmd = [
            self._python,
            str(self._live_qa),
            "run",
            "--data",
            "throwaway",  # CARD-633 D1: hard-coded; never clone / live AppData
            "--port",
            str(port_i),
            "--journeys",
            jid,
            "--viewports",
            vps,
            "--card",
            card_folder,
            "--out",
            str(out_dir),
        ]
        started = time.time()
        proc: Optional[subprocess.Popen] = None
        try:
            # Ensure report parent exists; live_qa also creates it.
            out_dir.mkdir(parents=True, exist_ok=True)
            creationflags = 0
            preexec = None
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                preexec = os.setsid  # type: ignore[attr-defined]
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._checkout),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                preexec_fn=preexec,
            )
            JourneyQaTools._active_proc = proc
            try:
                stdout, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_process_tree(proc)
                # Also stop the throwaway serve if still up
                try:
                    subprocess.run(
                        [self._python, str(self._live_qa), "stop", "--port", str(port_i)],
                        cwd=str(self._checkout),
                        capture_output=True,
                        timeout=60,
                        check=False,
                    )
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Journey run timed out after {timeout}s and was killed.",
                    "journey_id": jid,
                    "port": port_i,
                    "data": "throwaway",
                    "report_dir": str(out_dir),
                    "elapsed_s": round(time.time() - started, 1),
                }
            code = proc.returncode
            tail = (stdout or "")[-4000:]
            report_path = out_dir / "report.json"
            overall = "unknown"
            if report_path.is_file():
                try:
                    data = _load_report(report_path)
                    runs = data.get("runs") if isinstance(data.get("runs"), list) else []
                    outcomes = [str(r.get("outcome") or "") for r in runs if isinstance(r, dict)]
                    overall = "fail" if any(o.lower() == "fail" for o in outcomes) else ("pass" if outcomes else "unknown")
                except (OSError, ValueError, json.JSONDecodeError):
                    overall = "unknown"
            ok = code == 0 and overall != "fail"
            return {
                "success": bool(ok),
                "exit_code": code,
                "overall": overall,
                "journey_id": jid,
                "viewports": vps,
                "port": port_i,
                "data": "throwaway",
                "report_dir": str(out_dir),
                "report_path": str(report_path) if report_path.is_file() else "",
                "elapsed_s": round(time.time() - started, 1),
                "output_tail": tail,
                "note": "Throwaway CARD-532 env only; live :8000 and AppData were not used."
                + ("" if ok else " Use summarize_journey_failures on the report folder for details."),
            }
        except Exception as exc:
            if proc is not None:
                _kill_process_tree(proc)
            return {"success": False, "error": f"run_journey failed: {exc}", "journey_id": jid}
        finally:
            JourneyQaTools._active_proc = None
            JourneyQaTools._run_lock.release()

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
        registry.register_tool(
            name="run_journey",
            description=(
                "Run one CARD-532 live QA journey in a throwaway AutoReiv env on :8770 "
                "(never Jacob's :8000 or live AppData; never clones AppData). "
                "Requires operator approval before each run. After it finishes, use "
                "summarize_journey_failures on the report folder."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "journey_id": {
                        "type": "string",
                        "description": "Journey stem under tests/e2e/journeys (e.g. card-623-compact-honest)",
                    },
                    "viewports": {
                        "type": "string",
                        "description": "Comma list: desktop,phone (default both)",
                        "default": "desktop,phone",
                    },
                    "card": {
                        "type": "string",
                        "description": "Report folder name under the QA report root (default from journey id)",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Kill the run after this many seconds (default 1200, max 3600)",
                        "default": DEFAULT_RUN_TIMEOUT_S,
                    },
                },
                "required": ["journey_id"],
            },
            handler=self.run_journey,
            risk="network",
        )
