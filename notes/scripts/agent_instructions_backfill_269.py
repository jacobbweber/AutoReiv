#!/usr/bin/env python3
"""CARD-269 live smoke: Instructions sections for assistant/autoreiv/finance + short Ask each."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain.agents.good_agent_instructions import (  # noqa: E402
    REQUIRED_INSTRUCTION_SECTIONS,
    assert_good_agent_sections,
)

try:
    import httpx
except ImportError:
    httpx = None

BASE = "http://127.0.0.1:8000"
AGENTS = ("assistant", "autoreiv", "finance")
OUT = ROOT / "notes" / "marathon-card269-live-smoke.json"


def _agent_prompt(client: "httpx.Client", agent_id: str) -> str:
    r = client.get(f"/api/agents/{agent_id}", timeout=30.0)
    r.raise_for_status()
    return (r.json() or {}).get("system_prompt") or ""


def _short_ask(client: "httpx.Client", agent_id: str) -> dict:
    sid = None
    try:
        sr = client.post(
            "/api/sessions",
            json={"agent_id": agent_id, "title": f"CARD-269 {agent_id}"},
            timeout=30.0,
        )
        if sr.status_code < 400:
            body = sr.json() or {}
            sid = body.get("id") or body.get("session_id")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"session: {exc}"}

    if not sid:
        sid = f"card269-{agent_id}-{uuid.uuid4().hex[:8]}"

    job_id = None
    turn_done = False
    err = None
    events = []
    try:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "agent_id": agent_id,
                "session_id": sid,
                "content": "Reply with exactly one short line: CARD269_OK. No tools.",
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
                    if ev in {"turn_done", "done", "message_done"}:
                        turn_done = True
                        break
                    if ev == "error":
                        err = str(payload)[:300]
                        break
                if turn_done or err:
                    break
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "session_id": sid, "error": str(exc), "events": events[:20]}

    ok = bool(job_id or turn_done) and not err
    return {
        "ok": ok,
        "session_id": sid,
        "job_id": job_id,
        "turn_done": turn_done,
        "error": err,
        "events": events[:30],
    }


def main() -> int:
    result = {
        "card": 269,
        "ok": False,
        "agents": {},
        "asks": {},
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if httpx is None:
        result["error"] = "httpx missing"
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        try:
            client.get("/api/agents").raise_for_status()
        except Exception as e:  # noqa: BLE001
            result["error"] = f"serve unreachable: {e}"
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 1

        sections_ok = True
        for aid in AGENTS:
            prompt = _agent_prompt(client, aid)
            missing = assert_good_agent_sections(prompt)
            result["agents"][aid] = {
                "prompt_len": len(prompt),
                "missing_sections": missing,
                "has_all_sections": not missing,
                "section_heads_present": [s for s in REQUIRED_INSTRUCTION_SECTIONS if s in prompt],
            }
            if missing:
                sections_ok = False
            print(aid, "sections_ok", not missing, "len", len(prompt))

        asks_ok = True
        for aid in AGENTS:
            ask = _short_ask(client, aid)
            result["asks"][aid] = ask
            if not ask.get("ok"):
                asks_ok = False
            print(aid, "ask_ok", ask.get("ok"), "job", ask.get("job_id"), "err", ask.get("error"))

    result["ok"] = bool(sections_ok and asks_ok)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("artifact", OUT, "ok", result["ok"])
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
