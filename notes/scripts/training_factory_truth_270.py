#!/usr/bin/env python3
# CARD-270 live smoke
from __future__ import annotations
import json, time, uuid
from pathlib import Path
try:
    import httpx
except ImportError:
    httpx = None
BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "marathon-card270-live-smoke.json"
AGENT = "assistant"

def main() -> int:
    result = {"card": 270, "ok": False, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": {}}
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
        cap = "CARD270 probe tool %s" % uuid.uuid4().hex[:6]
        gr = client.post(
            "/api/agents/%s/gaps" % AGENT,
            json={
                "turn_text": "I need a tool that echoes %s" % cap,
                "identified_capability": cap,
                "suggested_tool_name": "echo_card270_%s" % uuid.uuid4().hex[:6],
            },
        )
        result["checks"]["create_gap"] = {"status": gr.status_code}
        if gr.status_code >= 400:
            result["error"] = "create gap failed"
            result["checks"]["create_gap"]["body"] = gr.text[:300]
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 2
        gap_id = ((gr.json() or {}).get("gap") or {}).get("id")
        result["gap_id"] = gap_id
        tr = client.post("/api/agents/%s/gaps/%s/train" % (AGENT, gap_id))
        tb = tr.json() if "json" in tr.headers.get("content-type", "") else {}
        result["checks"]["train"] = {"status": tr.status_code, "body": tb}
        job_id = tb.get("job_id")
        result["job_id"] = job_id
        train_status = tb.get("status")
        trained_list = client.get("/api/agents/%s/gaps" % AGENT, params={"status": "trained"})
        trained_hit = any(g.get("id") == gap_id for g in ((trained_list.json() or {}).get("gaps") or []))
        honesty = train_status == "training" and not trained_hit
        result["checks"]["train_honesty"] = {
            "api_status": train_status,
            "premature_trained": trained_hit,
            "ok": honesty,
        }
        pr = client.post(
            "/api/agent_training_factory/jobs/%s/promote" % job_id,
            json={"decision": "approved"},
        )
        pb = pr.json() if "json" in pr.headers.get("content-type", "") else {"text": pr.text[:400]}
        cant_ok = pr.status_code == 422
        result["checks"]["promote_empty_cant"] = {"status": pr.status_code, "body": pb, "ok": cant_ok}
        cant_list = client.get("/api/agents/%s/gaps" % AGENT, params={"status": "cant"})
        cant_hit = any(g.get("id") == gap_id for g in ((cant_list.json() or {}).get("gaps") or []))
        result["checks"]["gap_cant"] = {"ok": cant_hit or cant_ok, "in_list": cant_hit}
        result["ok"] = bool(result["checks"]["train_honesty"]["ok"] and result["checks"]["promote_empty_cant"]["ok"])
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
