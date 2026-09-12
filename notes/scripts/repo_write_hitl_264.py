#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CARD-264 scoped repo write HITL smoke.

Modes:
  --validate   policy / register / jail / rollback fixtures (no live serve)
  --live       Jarvis→Ollama Park→Approve + Deny probes; writes
               notes/marathon-card264-live-smoke.json

Do NOT invent job_ids — capture only from live SSE / Observe.
Stack branch: feat/repo-write-hitl-264 off feat/homelab-outcome-smoke-263 tip.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

BASE = "http://127.0.0.1:8000"
DB = Path.home() / "AppData/Local/AutoReiv/database/autoreiv.db"
LIVE_OUT = ROOT / "notes" / "marathon-card264-live-smoke.json"
AGENT_ID = "homelab"

APPROVE_PROBE = "notes/_card264_live_probe.txt"
DENY_PROBE = "notes/_card264_deny_probe.txt"
APPROVE_CONTENT = "CARD264-APPROVE-PROBE"
DENY_CONTENT = "SHOULD-NOT-LAND"

APPROVE_PROMPT = (
    "Using repo_file_write, create notes/_card264_live_probe.txt with content exactly "
    "CARD264-APPROVE-PROBE. Done-when: after I Approve the HITL park, the file exists "
    "with that content. Keep under 80 words."
)
DENY_PROMPT = (
    "Using repo_file_write, create notes/_card264_deny_probe.txt with content "
    "SHOULD-NOT-LAND. Done-when: I Deny the HITL park and the file does not exist. "
    "Keep under 60 words."
)

DESIGN_ROOM = (
    "Scoped repo_file_write/patch REQUIRE_CONFIRM; Deny leaves tree clean; "
    "Approve proves disk change; rollback restores prior — no silent checkout writes."
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
    except Exception:
        return "unknown"


def validate() -> int:
    from src.application.kernel.hitl_engine import HITLApprovalEngine
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.safety import tool_policy_gate as tpg
    from src.application.skills.repo_tools import RepoCheckoutTools
    from src.domain.gateway.models import ToolCall

    missing = [
        n
        for n in ("repo_file_write", "repo_file_patch", "repo_file_rollback")
        if n not in tpg._DEFAULT_REQUIRE_CONFIRM
    ]
    if missing:
        print(f"VALIDATE FAIL: missing REQUIRE_CONFIRM defaults: {missing}")
        return 1
    if "repo_file_write" in tpg._DEFAULT_SAFE:
        print("VALIDATE FAIL: repo_file_write must not be SAFE")
        return 1

    class _DummyStore:
        pass

    engine = HITLApprovalEngine(store=_DummyStore())  # type: ignore[arg-type]
    if not engine.requires_approval(
        ToolCall(id="1", name="repo_file_write", arguments={"path": "notes/x.txt", "content": "a"})
    ):
        print("VALIDATE FAIL: HITL must require approval for repo_file_write")
        return 1

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "notes").mkdir()
        (tmp / "notes" / "existing.txt").write_text("PRIOR\n", encoding="utf-8")
        (tmp / ".env").write_text("SECRET=1\n", encoding="utf-8")
        skill = RepoCheckoutTools(default_checkout_root=str(tmp))
        reg = ScopedToolRegistry()
        skill.register_tools(reg)
        for name in ("repo_file_write", "repo_file_patch", "repo_file_rollback"):
            if name not in reg:
                print(f"VALIDATE FAIL: {name} not registered")
                return 1
        written = skill.repo_file_write(path="notes/_v.txt", content="NEW\n")
        if not written.get("success"):
            print("VALIDATE FAIL: write failed", written)
            return 1
        if (tmp / "notes" / "_v.txt").read_text(encoding="utf-8") != "NEW\n":
            print("VALIDATE FAIL: write content mismatch")
            return 1
        rolled = skill.repo_file_rollback(path="notes/_v.txt")
        if not rolled.get("success") or (tmp / "notes" / "_v.txt").exists():
            print("VALIDATE FAIL: rollback did not delete created file", rolled)
            return 1
        patched = skill.repo_file_patch(path="notes/existing.txt", content="PATCHED\n")
        if not patched.get("success"):
            print("VALIDATE FAIL: patch failed", patched)
            return 1
        rolled2 = skill.repo_file_rollback(path="notes/existing.txt")
        if (tmp / "notes" / "existing.txt").read_text(encoding="utf-8") != "PRIOR\n":
            print("VALIDATE FAIL: rollback did not restore prior", rolled2)
            return 1
        env = skill.repo_file_write(path=".env", content="HACK=1\n")
        if env.get("success"):
            print("VALIDATE FAIL: .env write must be denied")
            return 1
        class _Store:
            def get_setting(self, key):
                return None

        class _Agent:
            allowed_tool_names = ["repo_file_write"]
            mcp_servers = []

        gate = tpg.ToolPolicyGate(store=_Store())
        decision = gate.evaluate(
            ToolCall(
                id="deny",
                name="repo_file_write",
                arguments={"path": "notes/_deny.txt", "content": "nope"},
            ),
            _Agent(),
            matched_capability_ids=["tool.repo_file_write"],
            registry_tool_names={"repo_file_write"},
        )
        if decision.verdict != tpg.ToolPolicyVerdict.REQUIRE_CONFIRM:
            print("VALIDATE FAIL: gate verdict", decision)
            return 1
        if (tmp / "notes" / "_deny.txt").exists():
            print("VALIDATE FAIL: deny semantics — tool must not have run")
            return 1

    print("VALIDATE OK: policy + HITL + jail + rollback + deny-unexecuted")
    return 0


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
            "tool.repo_file_write",
            "repo_file_write",
            "Create or overwrite a UTF-8 file under the AutoReiv checkout (HITL)",
            ["repo", "checkout", "write", "create", "file", "notes", "patch"],
            RiskLevel.HIGH,
            True,
        ),
        (
            "tool.repo_file_patch",
            "repo_file_patch",
            "Overwrite an existing UTF-8 file under checkout (HITL)",
            ["repo", "checkout", "patch", "edit", "overwrite", "file"],
            RiskLevel.HIGH,
            True,
        ),
        (
            "tool.repo_file_rollback",
            "repo_file_rollback",
            "Rollback last checkout write/patch to pre-write snapshot (HITL)",
            ["repo", "checkout", "rollback", "revert", "undo"],
            RiskLevel.HIGH,
            True,
        ),
        (
            "tool.repo_file_read",
            "repo_file_read",
            "Read a UTF-8 file under the AutoReiv checkout root (sandboxed)",
            ["repo", "checkout", "read", "file"],
            RiskLevel.LOW,
            False,
        ),
        (
            "tool.repo_file_list",
            "repo_file_list",
            "List a directory under the AutoReiv checkout root (sandboxed)",
            ["repo", "checkout", "list", "directory"],
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
                source="card264_live_smoke",
            )
        )
        ids.append(cid)
    return ids


def _probe_path(rel: str) -> Path:
    return ROOT / rel


def _clean_probes() -> None:
    for rel in (APPROVE_PROBE, DENY_PROBE, "notes/_card264_rollback_probe.txt"):
        p = _probe_path(rel)
        if p.exists():
            p.unlink()


def _list_pending(client: Any, sid: str) -> list[dict[str, Any]]:
    try:
        ar = client.get(f"{BASE}/api/chat/approvals/{sid}", timeout=15.0)
        items = ar.json() if ar.status_code == 200 else []
        if isinstance(items, dict):
            items = items.get("approvals") or items.get("items") or []
        return list(items or [])
    except Exception:
        return []


def _decide_pending(client: Any, sid: str, decision: str) -> list[str]:
    """Resolve pending HITL via /api/approvals (APPROVED|REJECTED)."""
    decided: list[str] = []
    decision_norm = (decision or "").strip().lower()
    api_decision = "APPROVED" if decision_norm in {"approve", "approved"} else "REJECTED"
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
                json={"decision": api_decision, "session_id": sid, "reason": f"card264-smoke-{api_decision.lower()}"},
                timeout=60.0,
            )
            if resp.status_code < 400:
                decided.append(str(aid))
    except Exception:
        pass
    return decided


def _parse_sse_block(block: str) -> tuple[str | None, dict[str, Any]]:
    ev = None
    data_lines: list[str] = []
    for line in block.splitlines():
        if line.startswith("event:"):
            ev = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not ev:
        return None, {}
    try:
        payload = json.loads("\n".join(data_lines) or "{}")
    except Exception:
        payload = {"raw": data_lines}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    return ev, payload


def stream_job(
    client: Any,
    prompt: str,
    *,
    title: str,
    decision: str,
    resume_after: bool,
    max_s: float = 420.0,
) -> dict[str, Any]:
    sid = client.post(
        f"{BASE}/api/sessions",
        json={"agent_id": AGENT_ID, "title": title},
        timeout=30.0,
    ).json()["id"]
    events: list[dict[str, Any]] = []
    turn_tail = ""
    job_id = None
    decided: list[str] = []
    parked = False
    t0 = time.time()
    last_decide = 0.0
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
        for chunk in resp.iter_text():
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                ev, payload = _parse_sse_block(block)
                if not ev:
                    continue
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
                    parked = True
                    decided += _decide_pending(client, sid, decision)
                    last_decide = time.time()
            if done:
                break
            if time.time() - t0 > max_s:
                break
            if time.time() - last_decide > 8:
                newly = _decide_pending(client, sid, decision)
                if newly:
                    parked = True
                    decided += newly
                last_decide = time.time()

    decided += _decide_pending(client, sid, decision)
    if _list_pending(client, sid):
        parked = True
        decided += _decide_pending(client, sid, decision)

    if resume_after and decision == "approve" and job_id:
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
                    "content": "Continue the standing Job after HITL Approve of the repo write.",
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
                            ev, payload = _parse_sse_block(block)
                            if not ev:
                                continue
                            events.append({"event": ev, "data": payload})
                            if ev == "token":
                                turn_tail += str(payload.get("text") or "")
                            if ev == "turn_done":
                                turn_tail = str(payload.get("content") or turn_tail)
                            if ev in {"approval_required", "hitl", "waiting_approval"}:
                                parked = True
                                decided += _decide_pending(client, sid, "approve")
                        if time.time() - t1 > 150:
                            break
        except Exception:
            pass
        decided += _decide_pending(client, sid, "approve")

    journey: dict[str, Any] = {}
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
                        status = str(
                            (journey.get("job") or {}).get("status")
                            or journey.get("status")
                            or ""
                        )
                    if str(status).lower() in {"done", "completed", "failed", "cancelled", "parked"}:
                        break
            except Exception:
                pass
            time.sleep(3)

    ev_names = [e.get("event") for e in events]
    if any(n in {"approval_required", "hitl", "waiting_approval"} for n in ev_names):
        parked = True

    return {
        "session_id": sid,
        "job_id": job_id,
        "event_names": ev_names,
        "events": events,
        "turn_tail": turn_tail[:2000],
        "journey": journey,
        "decided": decided,
        "parked": parked,
        "elapsed_s": round(time.time() - t0, 1),
    }


def live() -> int:
    if httpx is None:
        print("httpx required for --live")
        return 2
    _clean_probes()
    matched = seed()
    health = httpx.get(f"{BASE}/api/health", timeout=10.0).json()

    with httpx.Client(timeout=60.0) as client:
        approve = stream_job(
            client,
            APPROVE_PROMPT,
            title="card264-repo-write-approve",
            decision="approve",
            resume_after=True,
        )
        deny_existed_before = _probe_path(DENY_PROBE).exists()
        deny = stream_job(
            client,
            DENY_PROMPT,
            title="card264-repo-write-deny",
            decision="deny",
            resume_after=False,
        )

    approve_path = _probe_path(APPROVE_PROBE)
    deny_path = _probe_path(DENY_PROBE)
    approve_exists = approve_path.is_file()
    approve_text = approve_path.read_text(encoding="utf-8") if approve_exists else ""
    approve_ok = approve_exists and APPROVE_CONTENT in approve_text
    deny_exists = deny_path.exists()
    deny_ok = (not deny_existed_before) and (not deny_exists)

    # Record disk proof then clean probes so the feat commit stays tidy.
    if approve_exists:
        approve_path.unlink()
    if deny_exists:
        deny_path.unlink()

    approve_job = approve.get("job_id")
    deny_job = deny.get("job_id")
    passed = bool(
        approve_ok
        and deny_ok
        and approve_job
        and approve.get("parked")
        and deny.get("parked")
        and deny.get("decided")
    )
    artifact: dict[str, Any] = {
        "card": "CARD-264",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "agent_id": AGENT_ID,
        "matched_at_seed": matched,
        "health": health,
        "design_room": DESIGN_ROOM,
        "approve": {
            "prompt": APPROVE_PROMPT,
            "session_id": approve.get("session_id"),
            "job_id": approve_job,
            "parked": approve.get("parked"),
            "decided": approve.get("decided"),
            "file_existed_after_approve": approve_ok,
            "content_contains": APPROVE_CONTENT if approve_ok else None,
            "probe": APPROVE_PROBE,
            "journey_job": (approve.get("journey") or {}).get("job")
            if isinstance(approve.get("journey"), dict)
            else None,
            "event_names": approve.get("event_names"),
            "turn_tail": approve.get("turn_tail"),
            "elapsed_s": approve.get("elapsed_s"),
        },
        "deny": {
            "prompt": DENY_PROMPT,
            "session_id": deny.get("session_id"),
            "job_id": deny_job,
            "parked": deny.get("parked"),
            "decided": deny.get("decided"),
            "file_existed_after_deny": deny_exists,
            "tree_clean": deny_ok,
            "probe": DENY_PROBE,
            "journey_job": (deny.get("journey") or {}).get("job")
            if isinstance(deny.get("journey"), dict)
            else None,
            "event_names": deny.get("event_names"),
            "turn_tail": deny.get("turn_tail"),
            "elapsed_s": deny.get("elapsed_s"),
        },
        "pass": passed,
        "notes": (
            "job_ids captured from live SSE only — never invented. "
            "Approve must park then land CARD264-APPROVE-PROBE. "
            "Deny must park then leave notes/_card264_deny_probe.txt absent."
        ),
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "pass": passed,
                "approve_job_id": approve_job,
                "deny_job_id": deny_job,
                "approve_file": approve_ok,
                "deny_tree_clean": deny_ok,
                "tip": artifact["tip_sha"],
            },
            indent=2,
        )
    )
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true")
    g.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.validate:
        return validate()
    return live()


if __name__ == "__main__":
    raise SystemExit(main())
