"""
Nightly SkillOpt-Sleep-shaped skill eval (CARD-111) [REQ-IMPROVE-007 - REQ-IMPROVE-012] [REQ-IMPROVE-016].

Harvest failed turns from live SQLite, mine pack gaps, optional replay (default off),
in-process checker gate, then CARD-106 propose_skill draft only. Never commit_skill_pack.
Never write SKILL.md. Never train weights. No skillopt pip. No second scheduler.

02:00 America/New_York is the wrong default for this operator (surprise GPU load).
21:00 UTC is 17:00 EDT -- also wrong. Seed paused (enabled=false); weekday 21:00 ET.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from src.application.gateway.generation_semaphore import (
    DEFAULT_MAX_CONCURRENT_GENERATIONS,
    get_process_generation_limit,
)
from src.application.orchestration.ace_online import reflect_failed_turn
from src.application.orchestration.skill_proposals import propose_skill
from src.domain.observability.models import TelemetryFilter
from src.infrastructure.data.resolver import DataDirResolver, repo_root

ROUTINE_ID = "skill-eval-sleep"
AGENT_ID = "agent-builder"
SOURCE = "skill-eval-sleep"
DEFAULT_LOOKBACK_HOURS = 72
DEFAULT_MAX_SESSIONS = 20
DEFAULT_MAX_TASKS = 10
KNOWN_CHECKERS = frozenset({"harvest_gate", "verify_telemetry_consistency"})
MAX_INSIGHT_CHARS = 400


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        text = dt[:-1] + "+00:00" if dt.endswith("Z") else dt
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _meta(routine: Any) -> Dict[str, Any]:
    raw = getattr(routine, "metadata", None) if routine is not None else None
    return dict(raw or {})


def lookback_hours_of(routine: Any = None, override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    try:
        return int(_meta(routine).get("lookback_hours", DEFAULT_LOOKBACK_HOURS))
    except (TypeError, ValueError):
        return DEFAULT_LOOKBACK_HOURS


def replay_enabled(routine: Any = None, override: Optional[bool] = None) -> bool:
    if override is not None:
        return bool(override)
    return bool(_meta(routine).get("replay", False))


def named_checker(routine: Any = None) -> Optional[str]:
    raw = str(_meta(routine).get("checker") or "").strip()
    return raw or None


def harvest_db_is_live(
    store: Any,
    *,
    data_dir: Union[str, Path, None] = None,
    resolver: Optional[DataDirResolver] = None,
) -> Dict[str, Any]:
    """Refuse checkout ./data when LocalAppData is the live tree [REQ-IMPROVE-009]."""
    res = resolver or DataDirResolver()
    raw = getattr(store, "db_path", None)
    text = str(raw or "").strip()
    if not text or text == ":memory:":
        return {"live": True, "reason": "temp-or-memory"}
    db_path = Path(text)
    live_root = res.platform_default()
    live_db = live_root / "autoreiv.db"
    if res._is_legacy_db(db_path, str(db_path)):
        try:
            same_as_live = db_path.resolve() == live_db.resolve()
        except OSError:
            same_as_live = False
        if not same_as_live:
            return {
                "live": False,
                "reason": (
                    "Refusing checkout ./data harvest; live data dir is "
                    f"{live_root}. CARD-109 LocalAppData stays the source."
                ),
                "db_path": str(db_path),
            }
    return {"live": True, "reason": "ok", "db_path": str(db_path)}


def harvest_failed_turns(
    store: Any,
    *,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    max_tasks: int = DEFAULT_MAX_TASKS,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Read-only harvest of failed turn spans and FAILED jobs/phases."""
    now_utc = _aware(now) or datetime.now(timezone.utc)
    start = None
    if lookback_hours and int(lookback_hours) > 0:
        start = now_utc - timedelta(hours=int(lookback_hours))
    items: List[Dict[str, Any]] = []
    traces = store.get_filtered_traces(
        TelemetryFilter(span_type="turn", has_error=True, start_time=start),
        limit=max(max_tasks * 4, 40),
    )
    for span in traces:
        meta = dict(getattr(span, "metadata", None) or {})
        items.append(
            {
                "kind": "turn",
                "span_id": getattr(span, "id", None),
                "session_id": getattr(span, "session_id", None),
                "error": getattr(span, "error_message", None),
                "pack_id": meta.get("pack_id") or meta.get("skill_id"),
                "tool_name": meta.get("tool_name") or getattr(span, "name", None),
                "created_at": getattr(span, "created_at", None),
            }
        )
    getter = getattr(store, "_get_connection", None)
    if callable(getter):
        conn = getter()
        try:
            cur = conn.cursor()
            try:
                sql = "SELECT id, session_id, agent_id, status, goal, created_at FROM jobs WHERE lower(status) = 'failed'"
                params: List[Any] = []
                if start is not None:
                    sql += " AND created_at >= ?"
                    params.append(start.isoformat())
                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(max_tasks)
                for r in cur.execute(sql, tuple(params)).fetchall():
                    items.append(
                        {
                            "kind": "job",
                            "span_id": r["id"] if hasattr(r, "keys") else r[0],
                            "session_id": r["session_id"] if hasattr(r, "keys") else r[1],
                            "error": (r["goal"] if hasattr(r, "keys") else r[4]) or "job failed",
                            "pack_id": None,
                            "tool_name": None,
                            "created_at": r["created_at"] if hasattr(r, "keys") else r[5],
                        }
                    )
            except Exception:
                pass
            try:
                for r in cur.execute(
                    "SELECT id, name, react_state FROM phases "
                    "WHERE react_state = 'FAILED' OR lower(status) = 'failed' LIMIT ?",
                    (max_tasks,),
                ).fetchall():
                    name = r["name"] if hasattr(r, "keys") else r[1]
                    items.append(
                        {
                            "kind": "phase",
                            "span_id": r["id"] if hasattr(r, "keys") else r[0],
                            "session_id": None,
                            "error": f"phase {name} FAILED",
                            "pack_id": None,
                            "tool_name": name,
                            "created_at": None,
                        }
                    )
            except Exception:
                pass
        finally:
            if getattr(store, "_mem_conn", None) is None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _key(row: Dict[str, Any]) -> datetime:
        return _aware(row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)

    items.sort(key=_key, reverse=True)
    chosen: List[Dict[str, Any]] = []
    sessions: set[str] = set()
    for row in items:
        sid = str(row.get("session_id") or "").strip()
        if sid:
            if sid not in sessions and len(sessions) >= max_sessions:
                continue
            sessions.add(sid)
        chosen.append(row)
        if len(chosen) >= max_tasks:
            break
    return chosen


def mine_pack_gaps(harvested: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in harvested:
        pack = str(row.get("pack_id") or "").strip() or "unknown"
        tool = str(row.get("tool_name") or "").strip() or "turn"
        err = str(row.get("error") or "failed").strip()[:120]
        groups[f"{pack}|{tool}|{err}"].append(row)
    candidates: List[Dict[str, Any]] = []
    for key, rows in groups.items():
        pack, tool, _err = key.split("|", 2)
        pack_id = pack
        if pack_id == "unknown":
            continue
        head = rows[0]
        reflected = reflect_failed_turn(
            pack_id=pack_id,
            error_message=str(head.get("error") or ""),
            tool_errors=[{"tool_name": tool, "error": str(head.get("error") or "failed")}],
        )
        insight = reflected["insight"]
        if len(insight) > MAX_INSIGHT_CHARS:
            insight = insight[: MAX_INSIGHT_CHARS - 1].rstrip() + "."
        candidates.append(
            {
                "pack_id": pack_id,
                "tool_name": tool,
                "insight": insight,
                "evidence": reflected["evidence"],
                "count": len(rows),
                "span_id": head.get("span_id"),
                "session_id": head.get("session_id"),
            }
        )
    candidates.sort(key=lambda c: int(c.get("count") or 0), reverse=True)
    return candidates[:DEFAULT_MAX_TASKS]


def harvest_gate(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return {"status": "skip", "passed": False, "reason": "empty harvest; success no-op"}
    for cand in candidates:
        blob = f"{cand.get('insight') or ''} {cand.get('evidence') or ''}".lower()
        if "src/" in blob.replace("\\", "/") and ".py" in blob:
            return {"status": "fail", "passed": False, "reason": "python src rewrite"}
        if not str(cand.get("pack_id") or "").strip():
            return {"status": "fail", "passed": False, "reason": "missing pack_id"}
    return {"status": "pass", "passed": True, "reason": "harvest_gate"}


def run_checker_gate(
    candidates: List[Dict[str, Any]],
    *,
    routine: Any = None,
    checker: Optional[Callable[..., Dict[str, Any]]] = None,
    store: Any = None,
) -> Dict[str, Any]:
    name = named_checker(routine)
    if name and name not in KNOWN_CHECKERS and checker is None:
        return {
            "status": "skip",
            "passed": False,
            "verification_passed": False,
            "reason": f"Named checker '{name}' is missing; honest skip, not pass.",
            "checker": name,
        }
    if checker is not None:
        result = checker(candidates, store=store, routine=routine)
        status = str(result.get("status") or ("pass" if result.get("passed") else "fail")).lower()
        passed = status == "pass"
        return {
            "status": "pass" if passed else ("skip" if status == "skip" else "fail"),
            "passed": passed,
            "verification_passed": passed,
            "reason": result.get("reason") or status,
            "checker": name or "custom",
        }
    gated = harvest_gate(candidates)
    gated["verification_passed"] = bool(gated.get("passed"))
    gated["checker"] = name or "harvest_gate"
    return gated


def run_skill_eval_job(
    store: Any,
    data_dir: Union[str, Path],
    *,
    routine: Any = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    catalog: Any = None,
    checker: Optional[Callable[..., Dict[str, Any]]] = None,
    replay: Optional[bool] = None,
    replay_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
    lookback_hours: Optional[int] = None,
    now: Optional[datetime] = None,
    resolver: Optional[DataDirResolver] = None,
) -> Dict[str, Any]:
    """Harvest + mine + optional replay + gate + propose_skill. No commit, no SKILL.md write."""
    data_root = Path(data_dir)
    agent = (agent_id or (getattr(routine, "agent_id", None) if routine is not None else None) or AGENT_ID).strip()
    session = (session_id or "").strip() or f"routine_{ROUTINE_ID}"
    lookback = lookback_hours_of(routine, lookback_hours)
    do_replay = replay_enabled(routine, replay)

    live = harvest_db_is_live(store, data_dir=data_root, resolver=resolver)
    if not live.get("live"):
        return {
            "success": True,
            "status": "skip",
            "reason": live.get("reason"),
            "harvested": 0,
            "proposal_id": None,
            "skill_md_written": False,
            "disk_written": False,
            "src_written": False,
            "auto_commit": False,
            "committed": False,
            "replay": False,
            "stream_turn_attached": False,
            "checker": "skip",
        }

    harvested = harvest_failed_turns(store, lookback_hours=lookback, now=now)
    if not harvested:
        return {
            "success": True,
            "status": "success",
            "reason": "empty harvest; success no-op",
            "harvested": 0,
            "proposal_id": None,
            "skill_md_written": False,
            "disk_written": False,
            "src_written": False,
            "auto_commit": False,
            "committed": False,
            "replay": do_replay,
            "stream_turn_attached": False,
            "checker": "skip",
        }

    candidates = mine_pack_gaps(harvested)
    replay_info = {"replay": do_replay, "ran": 0, "skipped": True, "reason": "replay default off"}
    if do_replay:
        cap = get_process_generation_limit() or DEFAULT_MAX_CONCURRENT_GENERATIONS
        ran = 0
        if replay_fn is not None and cap >= 1:
            replay_fn(candidates[0])
            ran = 1
        replay_info = {
            "replay": True,
            "ran": ran,
            "skipped": ran == 0,
            "reason": "bounded replay (max 1)" if ran else "no replay_fn; harvest+gate only",
        }

    gate = run_checker_gate(candidates, routine=routine, checker=checker, store=store)
    if not gate.get("passed"):
        return {
            "success": gate.get("status") != "fail",
            "status": gate.get("status") or "skip",
            "reason": gate.get("reason"),
            "harvested": len(harvested),
            "proposal_id": None,
            "skill_md_written": False,
            "disk_written": False,
            "src_written": False,
            "auto_commit": False,
            "committed": False,
            "replay": do_replay,
            "replay_info": replay_info,
            "stream_turn_attached": False,
            "checker": gate.get("status"),
            "verification_passed": False,
        }

    cand = candidates[0]
    pack_id = str(cand["pack_id"])
    if catalog is None:
        from src.application.skills.user_catalog import UserSkillCatalog

        catalog = UserSkillCatalog(skills_dir=data_root / "skills")
    snapshot_id = None
    skill_path = catalog.resolve_skill_md(pack_id) if hasattr(catalog, "resolve_skill_md") else None
    skill_before = skill_path.read_bytes() if skill_path is not None and skill_path.is_file() else None
    if skill_path is not None and skill_path.is_file() and hasattr(catalog, "snapshot_pack"):
        snap = catalog.snapshot_pack(pack_id)
        if not snap.get("success"):
            return {
                "success": False,
                "status": "failed",
                "reason": snap.get("error") or "Snapshot failed; proposal was not created.",
                "harvested": len(harvested),
                "proposal_id": None,
                "skill_md_written": False,
                "disk_written": False,
                "src_written": False,
                "auto_commit": False,
                "committed": False,
                "replay": do_replay,
                "stream_turn_attached": False,
                "checker": "pass",
            }
        snapshot_id = snap.get("snapshot_id")

    drafted = propose_skill(
        store,
        what=f"Append nightly skill-eval insight to {pack_id} SOP",
        why=cand["insight"],
        how=f"Patch SKILL.md SOP with one bullet; no Python.\n\n- {cand['insight']}",
        where=f"skills/{pack_id}/SKILL.md",
        data_dir=data_root,
        session_id=session,
        agent_id=agent,
        pack_id=pack_id,
        extra_payload={
            "source": SOURCE,
            "auto_commit": False,
            "ace_delta": True,
            "snapshot_id": snapshot_id,
            "routine_id": ROUTINE_ID,
            "lookback_hours": lookback,
            "replay": do_replay,
            "evidence": cand.get("evidence"),
        },
    )
    skill_after = skill_path.read_bytes() if skill_path is not None and skill_path.is_file() else skill_before
    skill_md_written = bool(skill_before is not None and skill_after != skill_before)
    return {
        "success": drafted.get("status") == "draft" and not skill_md_written,
        "status": "success" if drafted.get("status") == "draft" else "failed",
        "reason": "propose_skill draft staged; human still approves (CARD-106). auto_commit false.",
        "harvested": len(harvested),
        "proposal_id": drafted.get("proposal_id"),
        "approval_id": drafted.get("approval_id"),
        "kind": drafted.get("kind"),
        "proposal_status": drafted.get("status"),
        "skill_md_written": skill_md_written,
        "disk_written": bool(drafted.get("disk_written")),
        "src_written": False,
        "auto_commit": False,
        "committed": False,
        "replay": do_replay,
        "replay_info": replay_info,
        "stream_turn_attached": False,
        "checker": "pass",
        "verification_passed": True,
        "pack_id": pack_id,
        "snapshot_id": snapshot_id,
        "routine_id": ROUTINE_ID,
        "checkout_root": str(repo_root()),
        "curator": maybe_hook_curator(data_root, routine),
    }



def maybe_hook_curator(data_root: Path, routine: Any = None) -> Dict[str, Any]:
    """CARD-112 hook. Off unless routine.metadata.auto_archive is true."""
    from src.application.skills.skill_curator import maybe_curate_from_routine
    from src.application.skills.user_catalog import UserSkillCatalog

    catalog = UserSkillCatalog(skills_dir=data_root / "skills")
    return maybe_curate_from_routine(catalog, routine)

def job_output_text(result: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "status": result.get("status"),
            "reason": result.get("reason"),
            "harvested": result.get("harvested"),
            "proposal_id": result.get("proposal_id"),
            "skill_md_written": result.get("skill_md_written"),
            "auto_commit": False,
            "checker": result.get("checker"),
        },
        indent=2,
    )
