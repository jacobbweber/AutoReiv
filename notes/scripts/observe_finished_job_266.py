"""CARD-266 Observe finished-job receipt smoke.

--validate  unit-style contract (no serve)
--live      Jarvis serve: existing or newly minted job_id opens; fake id 404s
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
LIVE_OUT = ROOT / "notes" / "marathon-card266-live-smoke.json"
BASE = "http://127.0.0.1:8000"
KNOWN_LIVE = "job_ed004b29cd44"
FAKE = "job_doesnotexist999"
DESIGN_ROOM = (
    "Finished job_id always opens in Observe — canonical GET 200 with the real tree, "
    "404 only if the job never existed."
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return ""


def _health() -> dict:
    return httpx.get(f"{BASE}/api/health", timeout=15.0).json()


def validate() -> int:
    from fastapi.testclient import TestClient

    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    tmp = ROOT / "notes" / "_card266_validate_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    db = tmp / "ctrl.db"
    if db.exists():
        db.unlink()
    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    orch = JobPhaseOrchestrator(store, data_dir=tmp)
    job = orch.create_job_with_phases(
        goal="CARD-266 validate",
        session_id="sess_266v",
        agent_id="assistant",
        phase_specs=[{"name": "Execute", "success_rule": "done"}],
    )
    client = TestClient(create_app(state_store=store))
    errors: list[str] = []
    r = client.get(f"/api/observe/jobs/{job.id}")
    if r.status_code != 200 or r.json().get("job_id") != job.id:
        errors.append(f"existing observe GET failed: {r.status_code} {r.text[:200]}")
    m = client.get(f"/api/observe/jobs/{FAKE}")
    if m.status_code != 404:
        errors.append(f"unknown should 404, got {m.status_code}")
    ok = not errors
    print(json.dumps({"ok": ok, "mode": "validate", "errors": errors, "job_id": job.id}))
    return 0 if ok else 1


def _mint_parent() -> tuple[str | None, str | None, list[str]]:
    notes: list[str] = []
    session_id = None
    try:
        sr = httpx.post(
            f"{BASE}/api/sessions",
            json={"agent_id": "assistant", "title": "CARD-266 receipt"},
            timeout=30.0,
        )
        if sr.status_code < 400:
            session_id = (sr.json() or {}).get("id") or (sr.json() or {}).get("session_id")
            notes.append(f"session={session_id}")
    except Exception as exc:
        notes.append(f"session soft-fail: {exc}")

    parent_job_id = None
    prompt = (
        "Standing job: search wiki for platform health once, then stop and wait. "
        "Done-when: one wiki_note_search tool result recorded. Keep under 40 words."
    )
    ev = None
    try:
        with httpx.stream(
            "POST",
            f"{BASE}/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": session_id,
                "content": prompt,
                "approval_mode": "ask",
            },
            timeout=300.0,
        ) as stream:
            buf = ""
            for chunk in stream.iter_text():
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
                        payload = {}
                    if not isinstance(payload, dict):
                        payload = {}
                    jid = payload.get("job_id")
                    if (ev == "job_created" or jid) and jid and not parent_job_id:
                        parent_job_id = str(jid)
                        notes.append(f"minted job_id={parent_job_id} (ev={ev})")
                    if parent_job_id and ev in {"job_created", "turn_done", "error"}:
                        break
                if parent_job_id and ev in {"job_created", "turn_done", "error"}:
                    break
    except Exception as exc:
        notes.append(f"chat mint failed: {exc}")
    return parent_job_id, session_id, notes


def live() -> int:
    if httpx is None:
        print(json.dumps({"ok": False, "errors": ["httpx missing"]}))
        return 1
    errors: list[str] = []
    notes: list[str] = []
    try:
        health = _health()
        notes.append(f"health={health.get('status')} version={health.get('version')}")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [f"serve unreachable: {exc}"], "tip_sha": tip_sha()}))
        return 1

    job_id = None
    known = httpx.get(f"{BASE}/api/observe/jobs/{KNOWN_LIVE}", timeout=30.0)
    notes.append(f"known {KNOWN_LIVE} observe_http={known.status_code}")
    if known.status_code == 200 and (known.json() or {}).get("job_id") == KNOWN_LIVE:
        job_id = KNOWN_LIVE
        notes.append("reused CARD-265 live job")
    else:
        minted, _sid, mint_notes = _mint_parent()
        notes.extend(mint_notes)
        job_id = minted

    if not job_id:
        payload = {
            "ok": False,
            "mode": "live",
            "tip_sha": tip_sha(),
            "errors": errors + ["no live job_id — refuse invent"],
            "notes": notes,
            "design_room": DESIGN_ROOM,
            "health": health,
        }
        LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    observe = httpx.get(f"{BASE}/api/observe/jobs/{job_id}", timeout=30.0)
    alias = httpx.get(f"{BASE}/api/jobs/{job_id}", timeout=30.0)
    query = httpx.get(
        f"{BASE}/api/observability/standing-journey",
        params={"job_id": job_id},
        timeout=30.0,
    )
    missing = httpx.get(f"{BASE}/api/observe/jobs/{FAKE}", timeout=30.0)
    missing_q = httpx.get(
        f"{BASE}/api/observability/standing-journey",
        params={"job_id": FAKE},
        timeout=30.0,
    )
    notes.append(f"observe={observe.status_code} alias={alias.status_code} query={query.status_code}")
    notes.append(f"fake observe={missing.status_code} fake query={missing_q.status_code}")

    body = observe.json() if observe.status_code == 200 else {}
    if observe.status_code != 200 or body.get("job_id") != job_id or not body.get("ok"):
        errors.append(f"canonical GET failed {observe.status_code}")
    if alias.status_code != 200 or (alias.json() or {}).get("job_id") != job_id:
        errors.append(f"alias GET failed {alias.status_code}")
    if query.status_code != 200 or (query.json() or {}).get("job_id") != job_id:
        errors.append(f"standing-journey GET failed {query.status_code}")
    if missing.status_code != 404:
        errors.append(f"fake id observe expected 404 got {missing.status_code}")
    if missing_q.status_code != 404:
        errors.append(f"fake id query expected 404 got {missing_q.status_code}")

    ok = not errors
    payload = {
        "ok": ok,
        "mode": "live",
        "card": "CARD-266",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "design_room": DESIGN_ROOM,
        "health": health,
        "notes": notes,
        "errors": errors,
        "job_id": job_id,
        "observe_status": observe.status_code,
        "alias_status": alias.status_code,
        "fake_status": missing.status_code,
        "journey": body if ok else None,
        "proof": "existing job_id 200 + same tree; unknown 404; no invent",
    }
    LIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.live:
        return live()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
