#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CARD-263 Homelab-class outcome smoke (Wiki + checkout + Job honesty).

Modes:
  --validate   classify frozen fixtures (no live serve)
  --live       Jarvis→Ollama Homelab Ask; writes notes/marathon-card263-live-smoke.json

Usage:
  python notes/scripts/homelab_outcome_smoke_263.py --validate
  python notes/scripts/homelab_outcome_smoke_263.py --live
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.orchestration.homelab_outcome_smoke import (  # noqa: E402
    evaluate_fixture_pack,
    evaluate_homelab_outcome,
)

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

BASE = "http://127.0.0.1:8000"
DB = Path.home() / "AppData/Local/AutoReiv/database/autoreiv.db"
LIVE_OUT = ROOT / "notes" / "marathon-card263-live-smoke.json"
AGENT_ID = "homelab"

COS_PROMPT = (
    "Homelab-class: Using repo_file_list and repo_file_read, read AGENTS.md from the "
    "AutoReiv checkout and summarize the card rule (Three Beats; cards stay Ready until "
    "build) into a new Wiki note in 00_Inbox. Done-when: I can open that note via "
    "wiki_note_read and the note only claims what repo_file_read returned. Do not invent "
    "checkout or wiki paths. Keep under 160 words."
)

DESIGN_ROOM = (
    "One Homelab-class Ask grounds Wiki + repo_file_* on the same job_id; "
    "Journey DONE on Observe; claims only tool-provenanced facts — no invent."
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception:
        return "unknown"


def frozen_fixtures() -> list[dict[str, Any]]:
    job = "job_aabbccddeeff"
    events = [
        {"event": "job_created", "data": {"job_id": job}},
        {"event": "plan_formulated", "data": {"job_id": job, "phase": "Formulate"}},
        {"event": "phase_start", "data": {"job_id": job, "phase": "Execute"}},
        {
            "event": "tool_output",
            "data": {"name": "repo_file_read", "success": True, "path": "AGENTS.md"},
        },
        {
            "event": "tool_output",
            "data": {"name": "wiki_note_create", "success": True, "path": "00_Inbox/agents-card-rule.md"},
        },
        {
            "event": "tool_output",
            "data": {"name": "wiki_note_read", "success": True, "path": "00_Inbox/agents-card-rule.md"},
        },
    ]
    journey = {
        "ok": True,
        "job_id": job,
        "job": {"id": job, "status": "done"},
        "phases": [{"name": "Formulate", "status": "done"}, {"name": "Execute", "status": "done"}],
    }
    return [
        {
            "id": "fx_pass",
            "expect_ok": True,
            "events": events,
            "job": {"id": job, "status": "done"},
            "journey": journey,
            "turn_text": "Wrote 00_Inbox/agents-card-rule.md from AGENTS.md.",
            "expected_job_id": job,
        },
        {
            "id": "fx_no_repo",
            "expect_ok": False,
            "events": [e for e in events if "repo_file" not in str(e)],
            "job": {"id": job, "status": "done"},
            "journey": journey,
            "turn_text": "Wrote 00_Inbox/agents-card-rule.md",
            "expected_job_id": job,
        },
        {
            "id": "fx_invent",
            "expect_ok": False,
            "events": events,
            "job": {"id": job, "status": "done"},
            "journey": journey,
            "turn_text": "See 00_Inbox/totally-fake-okta.md",
            "expected_job_id": job,
        },
        {
            "id": "fx_wrong_observe",
            "expect_ok": False,
            "events": events,
            "job": {"id": job, "status": "done"},
            "journey": {"ok": True, "job_id": "job_deadbeef0001", "job": {"id": "job_deadbeef0001", "status": "done"}},
            "turn_text": "Wrote 00_Inbox/agents-card-rule.md from AGENTS.md.",
            "expected_job_id": job,
        },
    ]


def seed() -> list[str]:
    from src.domain.capabilities.models import (
        CapabilityIndexEntry,
        CapabilityKind,
        RiskLevel,
        TrustTier,
    )
    from src.infrastructure.memory.repositories.capability_catalog import (
        CapabilityCatalogRepository,
    )
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=str(DB))
    repo = CapabilityCatalogRepository(store)
    specs = [
        (
            "tool.repo_file_read",
            "repo_file_read",
            "Read a UTF-8 file under the AutoReiv checkout root (sandboxed)",
            ["repo", "checkout", "agents.md", "read", "source", "code", "file", "cards"],
            RiskLevel.LOW,
            False,
        ),
        (
            "tool.repo_file_list",
            "repo_file_list",
            "List a directory under the AutoReiv checkout root (sandboxed)",
            ["repo", "checkout", "list", "directory", "files", "source"],
            RiskLevel.LOW,
            False,
        ),
        (
            "tool.wiki_note_create",
            "wiki_note_create",
            "Create a wiki note in the vault",
            ["wiki", "create", "note", "write", "author", "inbox", "00_inbox"],
            RiskLevel.HIGH,
            True,
        ),
        (
            "tool.wiki_note_read",
            "wiki_note_read",
            "Read a wiki note",
            ["wiki", "note", "read", "open", "exists", "inbox"],
            RiskLevel.LOW,
            False,
        ),
        (
            "tool.wiki_note_search",
            "wiki_note_search",
            "Search wiki notes",
            ["wiki", "search", "note", "vault"],
            RiskLevel.LOW,
            False,
        ),
        (
            "tool.wiki_note_list",
            "wiki_note_list",
            "List wiki notes",
            ["wiki", "list", "note", "inbox"],
            RiskLevel.LOW,
            False,
        ),
    ]
    ids = []
    for cid, name, summary, keywords, risk, hitl in specs:
        repo.upsert_entry(
            CapabilityIndexEntry(
                id=cid,
                kind=CapabilityKind.TOOL,
                name=name,
                summary=summary,
                keywords=keywords,
                roles=["homelab", "assistant", "librarian", "general"],
                trust_tier=TrustTier.TRUSTED,
                risk_level=risk,
                requires_hitl=hitl,
                source="card263_live_smoke",
            )
        )
        ids.append(cid)
    return ids


def _approve_pending(client: Any, sid: str) -> list[str]:
    """Approve pending HITL via /api/approvals (real HITL router)."""
    approved: list[str] = []
    try:
        ar = client.get(
            f"{BASE}/api/approvals/pending",
            params={"session_id": sid},
            timeout=15.0,
        )
        items = ar.json() if ar.status_code == 200 else []
        if isinstance(items, dict):
            items = items.get("approvals") or items.get("items") or items.get("pending") or []
        filtered = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            item_sid = str(item.get("session_id") or "")
            if item_sid == sid or item_sid.startswith(sid + "::"):
                filtered.append(item)
        if not filtered and items:
            filtered = [i for i in items if isinstance(i, dict)]
        for item in filtered:
            aid = item.get("approval_id") or item.get("id")
            if not aid:
                continue
            resp = client.post(
                f"{BASE}/api/approvals/{aid}/decision",
                json={"decision": "APPROVED", "session_id": sid, "reason": "card263-smoke"},
                timeout=60.0,
            )
            if resp.status_code < 400:
                approved.append(str(aid))
    except Exception:
        pass
    return approved


def stream_until_done(client: Any, prompt: str, *, max_s: float = 420.0) -> dict[str, Any]:
    sid = client.post(
        f"{BASE}/api/sessions",
        json={"agent_id": AGENT_ID, "title": "card263-homelab-outcome"},
        timeout=30.0,
    ).json()["id"]
    events: list[dict[str, Any]] = []
    turn_tail = ""
    job_id = None
    t0 = time.time()
    with client.stream(
        "POST",
        f"{BASE}/api/chat/stream",
        json={
            "session_id": sid,
            "content": prompt,
            "agent_id": AGENT_ID,
            "approval_mode": "ask",
        },
        timeout=max_s + 30,
    ) as resp:
        resp.raise_for_status()
        buf = ""
        done = False
        last_approve = 0.0
        for chunk in resp.iter_text():
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                ev = None
                data_lines: list[str] = []
                for line in block.splitlines():
                    if line.startswith("event:"):
                        ev = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                if not ev:
                    continue
                try:
                    payload = json.loads("\n".join(data_lines) or "{}")
                except Exception:
                    payload = {"raw": data_lines}
                if not isinstance(payload, dict):
                    payload = {"value": payload}
                events.append({"event": ev, "data": payload})
                if ev == "job_created":
                    job_id = payload.get("job_id") or job_id
                if ev == "token":
                    turn_tail += str(payload.get("text") or "")
                if ev == "turn_done":
                    turn_tail = str(payload.get("content") or turn_tail)
                    done = True
                if ev == "error":
                    turn_tail += " ERROR:" + json.dumps(payload)[:400]
                    done = True
                if ev in {"approval_required", "hitl", "waiting_approval"}:
                    _approve_pending(client, sid)
                    last_approve = time.time()
            if done:
                break
            if time.time() - t0 > max_s:
                break
            if time.time() - last_approve > 8:
                _approve_pending(client, sid)
                last_approve = time.time()

    approved = _approve_pending(client, sid)
    if job_id:
        try:
            client.post(
                f"{BASE}/api/chat/resume",
                json={"session_id": sid, "job_id": job_id},
                timeout=30.0,
            )
        except Exception:
            pass
        try:
            with client.stream(
                "POST",
                f"{BASE}/api/chat/stream",
                json={
                    "session_id": sid,
                    "content": "Continue the standing Job. Approve-complete the Wiki note if parked.",
                    "agent_id": AGENT_ID,
                    "approval_mode": "ask",
                    "resume": True,
                    "job_id": job_id,
                },
                timeout=180,
            ) as resp2:
                if resp2.status_code < 400:
                    buf = ""
                    t1 = time.time()
                    for chunk in resp2.iter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            block, buf = buf.split("\n\n", 1)
                            ev = None
                            data_lines: list[str] = []
                            for line in block.splitlines():
                                if line.startswith("event:"):
                                    ev = line[6:].strip()
                                elif line.startswith("data:"):
                                    data_lines.append(line[5:].strip())
                            if not ev:
                                continue
                            try:
                                payload = json.loads("\n".join(data_lines) or "{}")
                            except Exception:
                                payload = {"raw": data_lines}
                            if not isinstance(payload, dict):
                                payload = {"value": payload}
                            events.append({"event": ev, "data": payload})
                            if ev == "token":
                                turn_tail += str(payload.get("text") or "")
                            if ev == "turn_done":
                                turn_tail = str(payload.get("content") or turn_tail)
                            if ev in {"approval_required", "hitl", "waiting_approval"}:
                                _approve_pending(client, sid)
                        if time.time() - t1 > 150:
                            break
        except Exception:
            pass
        approved += _approve_pending(client, sid)

    journey = {}
    if job_id:
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                jr = client.get(
                    f"{BASE}/api/observability/standing-journey",
                    params={"job_id": job_id},
                    timeout=15.0,
                )
                if jr.status_code == 200:
                    journey = jr.json()
                    status = ""
                    if isinstance(journey, dict):
                        status = str((journey.get("job") or {}).get("status") or journey.get("status") or "")
                    if str(status).lower() in {"done", "completed", "failed", "cancelled"}:
                        break
            except Exception:
                pass
            time.sleep(3)

    return {
        "session_id": sid,
        "job_id": job_id,
        "agent_id": AGENT_ID,
        "event_names": [e.get("event") for e in events],
        "events": events,
        "turn_tail": turn_tail[:2000],
        "journey": journey,
        "approved": approved,
        "elapsed_s": round(time.time() - t0, 1),
    }


def run_validate() -> int:
    pack = evaluate_fixture_pack(frozen_fixtures())
    print(json.dumps({"mode": "validate", "ok": pack["ok"], "results": [
        {"id": r["id"], "match": r["match"], "expect_ok": r["expect_ok"], "got_ok": r["got_ok"]}
        for r in pack["results"]
    ]}, indent=2))
    return 0 if pack["ok"] else 1


def run_live() -> int:
    if httpx is None:
        print("httpx required for --live", file=sys.stderr)
        return 2
    matched = seed()
    health = httpx.get(f"{BASE}/api/health", timeout=10.0).json()
    with httpx.Client(timeout=60.0) as client:
        live = stream_until_done(client, COS_PROMPT)
    evs = live.get("events") or []
    journey = live.get("journey") or {}
    job_id = live.get("job_id")
    verdict = evaluate_homelab_outcome(
        events=evs,
        job={"id": job_id, "status": (journey.get("job") or {}).get("status")} if job_id else None,
        journey=journey,
        phases=journey.get("phases") or [],
        turn_text=str(live.get("turn_tail") or ""),
        expected_job_id=job_id,
    )
    artifact = {
        "card": "CARD-263",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "agent_id": AGENT_ID,
        "matched_at_seed": matched,
        "health": health,
        "prompt": COS_PROMPT,
        "session_id": live.get("session_id"),
        "job_id": job_id,
        "observe_job_id": verdict.get("observe_job_id"),
        "event_names": live.get("event_names"),
        "turn_tail": live.get("turn_tail"),
        "journey_job": (journey.get("job") if isinstance(journey, dict) else None),
        "journey_phases": (journey.get("phases") if isinstance(journey, dict) else None),
        "elapsed_s": live.get("elapsed_s"),
        "verdict": verdict,
        "pass": bool(verdict.get("ok")),
        "design_room_one_liner": DESIGN_ROOM,
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pass": artifact["pass"],
        "job_id": job_id,
        "observe_job_id": verdict.get("observe_job_id"),
        "bars": verdict.get("bars"),
        "tip": artifact["tip_sha"],
        "elapsed_s": live.get("elapsed_s"),
    }, indent=2))
    return 0 if artifact["pass"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return run_validate()
    return run_live()


if __name__ == "__main__":
    raise SystemExit(main())
