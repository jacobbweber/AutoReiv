#!/usr/bin/env python3
"""CARD-271 live smoke: short Ask = no Job; outcome Ask = job_id + Observe journey."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "marathon-card271-live-smoke.json"
AGENT = "assistant"

SHORT = "Hi — one short friendly hello only. No tools."
OUTCOME = (
    "First search the wiki for standing Job graph notes, then list any related gaps, "
    "then summarize findings in under 80 words. Done-when: both search and summary recorded."
)


def _session(client: "httpx.Client", title: str) -> str:
    sr = client.post("/api/sessions", json={"agent_id": AGENT, "title": title}, timeout=30.0)
    if sr.status_code < 400:
        body = sr.json() or {}
        sid = body.get("id") or body.get("session_id")
        if sid:
            return str(sid)
    return "card271-%s" % uuid.uuid4().hex[:8]


def _stream_job(client: "httpx.Client", session_id: str, content: str) -> dict:
    job_id = None
    events = []
    err = None
    try:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "agent_id": AGENT,
                "session_id": session_id,
                "content": content,
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
                    data_lines = []
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
                    events.append(ev)
                    jid = payload.get("job_id")
                    if jid and not job_id:
                        job_id = str(jid)
                    if ev in {"turn_done", "done", "message_done", "error", "job_created"} and (
                        job_id or ev in {"turn_done", "done", "error"}
                    ):
                        if ev == "error":
                            err = str(payload)[:300]
                        if job_id or ev in {"turn_done", "done", "error"}:
                            # for short: stop on turn_done; for outcome wait for job then turn_done
                            if job_id and ev == "job_created":
                                continue
                            if ev in {"turn_done", "done", "error"}:
                                break
                if err or (events and events[-1] in {"turn_done", "done", "error"} and (job_id or content == SHORT)):
                    break
                if len(events) > 80:
                    break
    except Exception as exc:
        return {"ok": False, "error": str(exc), "job_id": job_id, "events": events[:40]}
    return {"ok": True, "job_id": job_id, "events": events[:40], "error": err}


def main() -> int:
    result = {
        "card": 271,
        "ok": False,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "short": {},
        "outcome": {},
        "observe": {},
    }
    if httpx is None:
        result["error"] = "httpx missing"
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        try:
            client.get("/api/agents").raise_for_status()
        except Exception as e:
            result["error"] = "serve unreachable: %s" % e
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 1

        sid_short = _session(client, "CARD-271 short")
        short = _stream_job(client, sid_short, SHORT)
        short_ok = short.get("ok") and not short.get("job_id")
        result["short"] = {**short, "session_id": sid_short, "no_job": short_ok}

        sid_out = _session(client, "CARD-271 outcome")
        outcome = _stream_job(client, sid_out, OUTCOME)
        job_id = outcome.get("job_id")
        outcome_ok = bool(outcome.get("ok") and job_id)
        result["outcome"] = {**outcome, "session_id": sid_out, "has_job": outcome_ok}

        observe_ok = False
        if job_id:
            # Prefer CARD-266 canonical observe path
            for path in (
                "/api/observe/jobs/%s" % job_id,
                "/api/observability/standing-journey?job_id=%s" % job_id,
            ):
                try:
                    r = client.get(path, timeout=30.0)
                    body = r.json() if "json" in r.headers.get("content-type", "") else {}
                    result["observe"][path] = {"status": r.status_code, "preview": str(body)[:400]}
                    if r.status_code == 200:
                        observe_ok = True
                        break
                except Exception as exc:
                    result["observe"][path] = {"error": str(exc)}
        result["observe"]["ok"] = observe_ok
        result["ok"] = bool(short_ok and outcome_ok and observe_ok)

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
