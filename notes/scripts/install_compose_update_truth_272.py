#!/usr/bin/env python3
"""CARD-272 live smoke: version API matches git; check responds; no apply."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "marathon-card272-live-smoke.json"


def main() -> int:
    result = {"card": 272, "ok": False, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": {}}
    git = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    git_sha = (git.stdout or "").strip()
    result["git_sha"] = git_sha
    if httpx is None:
        result["error"] = "httpx missing"
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        try:
            vr = client.get("/api/system/version")
        except Exception as e:
            result["error"] = "serve unreachable: %s" % e
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 1
        body = vr.json() if vr.status_code < 500 else {}
        commit = str(body.get("commit") or "")
        is_git = bool(body.get("is_git"))
        match = bool(commit and git_sha and (commit == git_sha or git_sha.startswith(commit) or commit.startswith(git_sha)))
        result["checks"]["version"] = {
            "status": vr.status_code,
            "commit": commit,
            "is_git": is_git,
            "matches_git": match,
            "ok": vr.status_code == 200 and is_git and match,
        }
        cr = client.get("/api/system/updates/check")
        result["checks"]["check"] = {"status": cr.status_code, "ok": cr.status_code == 200}
        # Do NOT call apply.
        result["checks"]["no_apply"] = {"ok": True}
        result["ok"] = bool(result["checks"]["version"]["ok"] and result["checks"]["check"]["ok"])
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
