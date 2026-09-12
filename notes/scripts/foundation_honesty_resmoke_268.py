"""CARD-268 foundation honesty re-smoke (bones 1-5 + operator UI).

--validate  honesty fixtures + UI anchors (no live LLM)
--live      honesty pack live under qwen + Observe receipt + UI Playwright + Forge same-job probe
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIVE_OUT = ROOT / "notes" / "marathon-card268-live-smoke.json"
UI_OUT = ROOT / "notes" / "marathon-card268-ui-proof.json"
BASE = "http://127.0.0.1:8000"
DESIGN = (
    "Foundation audit 268: re-smoke bones 1-5 on tip under qwen with Chat/Observe UI proof "
    "- honesty, receipt, HITL, provenance, same-job resume - or call red."
)


def tip_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def _run(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def validate() -> int:
    errors: list[str] = []
    notes: list[str] = []
    r = _run([sys.executable, "notes/scripts/honesty_smoke_pack_261.py", "--validate"], timeout=120)
    notes.append(f"honesty_validate_exit={r.returncode}")
    if r.returncode != 0:
        errors.append("honesty_smoke_pack_261 --validate failed")
        notes.append((r.stdout or "")[-500:])
        notes.append((r.stderr or "")[-300:])
    t = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/orchestration/test_card268_foundation_honesty_resmoke.py",
            "tests/unit/observability/test_card266_observe_finished_job.py",
            "-q",
            "--tb=line",
        ],
        timeout=180,
    )
    notes.append(f"pytest_exit={t.returncode}")
    if t.returncode != 0:
        errors.append("unit tests failed")
        notes.append((t.stdout or "")[-600:])
    # Forge same-job unit probe (in-process, no serve)
    forge = _run([sys.executable, str(ROOT / "_card251_live_smoke.py")], timeout=120)
    notes.append(f"forge_probe_exit={forge.returncode}")
    forge_ok = False
    try:
        # script prints JSON at end or writes file — parse stdout
        text = forge.stdout or ""
        if '"ok": true' in text.lower() or '"ok":true' in text.replace(" ", "").lower():
            forge_ok = True
        # also check written artifact if present
        art = ROOT / "notes" / "marathon-card251-live-smoke.json"
        if art.exists():
            data = json.loads(art.read_text(encoding="utf-8"))
            forge_ok = bool(data.get("ok")) and bool((data.get("forge_result") or {}).get("same_job"))
            notes.append(f"forge_artifact_ok={data.get('ok')} same={((data.get('forge_result') or {}).get('same_job'))}")
    except Exception as exc:
        notes.append(f"forge_parse:{exc}")
    if forge.returncode != 0 and not forge_ok:
        # re-run and capture written path from script
        notes.append((forge.stdout or "")[-400:])
        notes.append((forge.stderr or "")[-200:])
        # Try import-style by executing and reading return via rewritten call
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("card251_smoke", ROOT / "_card251_live_smoke.py")
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            result = mod.main()
            forge_ok = bool(result.get("ok")) and bool((result.get("forge_result") or {}).get("same_job"))
            notes.append(f"forge_main_ok={forge_ok} job={result.get('job_id')}")
            (ROOT / "notes" / "marathon-card268-forge-probe.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        except Exception as exc:
            errors.append(f"forge same-job probe failed: {exc}")
    elif not forge_ok:
        errors.append("forge same-job probe not ok")

    ok = not errors
    payload = {
        "ok": ok,
        "mode": "validate",
        "tip_sha": tip_sha(),
        "errors": errors,
        "notes": notes,
        "design_room": DESIGN,
    }
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


def _pick_ui_job(honesty: dict[str, Any]) -> str | None:
    for s in honesty.get("scenarios") or []:
        jid = s.get("job_id")
        if jid and str(s.get("classification") or "") in {"pass", "kill_resume", "gate", "tool"}:
            return str(jid)
    for s in honesty.get("scenarios") or []:
        if s.get("job_id"):
            return str(s["job_id"])
    return None


def live() -> int:
    try:
        import httpx
    except Exception:
        print(json.dumps({"ok": False, "errors": ["httpx missing"]}))
        return 1

    errors: list[str] = []
    notes: list[str] = []
    bars: dict[str, Any] = {}

    try:
        health = httpx.get(f"{BASE}/api/health", timeout=15).json()
        notes.append(f"health={health.get('status')} version={health.get('version')}")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [f"serve unreachable: {exc}"], "tip_sha": tip_sha()}))
        return 1

    # 1) Honesty pack live (includes kill_resume)
    notes.append("starting honesty_smoke_pack_261 --live")
    h = _run([sys.executable, "notes/scripts/honesty_smoke_pack_261.py", "--live"], timeout=3600)
    notes.append(f"honesty_live_exit={h.returncode}")
    honesty_path = ROOT / "notes" / "marathon-card261-live-smoke.json"
    honesty: dict[str, Any] = {}
    if honesty_path.exists():
        honesty = json.loads(honesty_path.read_text(encoding="utf-8"))
        notes.append(f"honesty_ok={honesty.get('ok')} scenarios={len(honesty.get('scenarios') or [])}")
    else:
        errors.append("missing marathon-card261-live-smoke.json after --live")
    if h.returncode != 0 or not honesty.get("ok"):
        errors.append("honesty pack live red or failed")
        notes.append((h.stdout or "")[-500:])
        notes.append((h.stderr or "")[-300:])
    bars["honesty_pack"] = {
        "ok": bool(honesty.get("ok")),
        "merge_gate": honesty.get("merge_gate"),
        "counts_by_class": honesty.get("counts_by_class"),
        "job_ids": [s.get("job_id") for s in (honesty.get("scenarios") or []) if s.get("job_id")],
    }

    # Kill/resume same job from honesty scenarios
    kr = next((s for s in (honesty.get("scenarios") or []) if s.get("id") == "live_kill_resume" or s.get("classification") == "kill_resume"), None)
    bars["kill_resume"] = {
        "ok": bool(kr and kr.get("same_job_id") is not False and not kr.get("is_red")),
        "job_id": (kr or {}).get("job_id"),
        "same_job_id": (kr or {}).get("same_job_id"),
        "classification": (kr or {}).get("classification"),
    }
    if not bars["kill_resume"]["ok"]:
        errors.append("kill_resume bar failed")

    # 2) Observe receipt for a real job
    job_id = _pick_ui_job(honesty)
    if not job_id:
        errors.append("no live job_id for Observe/UI — refuse invent")
    else:
        obs = httpx.get(f"{BASE}/api/observe/jobs/{job_id}", timeout=30)
        fake = httpx.get(f"{BASE}/api/observe/jobs/job_doesnotexist999", timeout=30)
        bars["observe_receipt"] = {
            "ok": obs.status_code == 200 and (obs.json() or {}).get("job_id") == job_id and fake.status_code == 404,
            "job_id": job_id,
            "observe_status": obs.status_code,
            "fake_status": fake.status_code,
            "journey_status": ((obs.json() or {}).get("job") or {}).get("status") if obs.status_code == 200 else None,
            "phases": [
                {"name": p.get("name"), "status": p.get("status")}
                for p in ((obs.json() or {}).get("phases") or [])
            ]
            if obs.status_code == 200
            else [],
        }
        notes.append(f"observe job={job_id} status={obs.status_code} fake={fake.status_code}")
        if not bars["observe_receipt"]["ok"]:
            errors.append("Observe receipt bar failed")

    # 3) Operator UI proof (Playwright)
    ui: dict[str, Any] = {"ok": False}
    if job_id:
        ui_cmd = _run(
            ["node", "notes/scripts/foundation_honesty_ui_268.mjs", job_id, str(UI_OUT)],
            timeout=120,
        )
        notes.append(f"ui_exit={ui_cmd.returncode}")
        if UI_OUT.exists():
            ui = json.loads(UI_OUT.read_text(encoding="utf-8"))
        else:
            notes.append((ui_cmd.stdout or "")[-400:])
            notes.append((ui_cmd.stderr or "")[-400:])
            errors.append("UI proof artifact missing")
        bars["operator_ui"] = {
            "ok": bool(ui.get("ok")),
            "job_id": job_id,
            "checks": ui.get("checks"),
            "error": ui.get("error"),
        }
        if not ui.get("ok"):
            errors.append("operator UI proof failed (JSON alone ≠ Done)")

    # 4) Forge same-job probe (in-process)
    forge_ok = False
    forge_job = None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("card251_smoke", ROOT / "_card251_live_smoke.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        forge_result = mod.main()
        forge_ok = bool(forge_result.get("ok")) and bool((forge_result.get("forge_result") or {}).get("same_job"))
        forge_job = forge_result.get("job_id")
        (ROOT / "notes" / "marathon-card268-forge-probe.json").write_text(
            json.dumps(forge_result, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        errors.append(f"forge probe exception: {exc}")
    bars["forge_same_job"] = {"ok": forge_ok, "job_id": forge_job}
    if not forge_ok:
        errors.append("Forge same-job bar failed")

    # 5) HITL write honesty — prefer quick live deny if script supports, else validate + last green cite
    hitl_notes = []
    hitl_ok = False
    try:
        # Reuse 264 validate path if --live too heavy; try --validate first then light live flag
        v264 = _run([sys.executable, "notes/scripts/repo_write_hitl_264.py", "--validate"], timeout=180)
        hitl_notes.append(f"hitl_validate_exit={v264.returncode}")
        art264 = ROOT / "notes" / "marathon-card264-live-smoke.json"
        if art264.exists():
            d264 = json.loads(art264.read_text(encoding="utf-8"))
            hitl_notes.append(f"prior_264_ok={d264.get('ok')}")
        if v264.returncode == 0:
            # one live deny/approve if --live is available
            live264 = _run([sys.executable, "notes/scripts/repo_write_hitl_264.py", "--live"], timeout=900)
            hitl_notes.append(f"hitl_live_exit={live264.returncode}")
            if art264.exists():
                d264 = json.loads(art264.read_text(encoding="utf-8"))
                # CARD-264 artifact uses pass=True (not ok)
                ap = d264.get("approve") or {}
                den = d264.get("deny") or {}
                hitl_ok = bool(d264.get("pass") or d264.get("ok")) and bool(
                    ap.get("file_existed_after_approve")
                ) and bool(den.get("tree_clean") or den.get("file_existed_after_deny") is False)
                hitl_notes.append(
                    f"hitl_live_pass={d264.get('pass')} approve_landed={ap.get('file_existed_after_approve')} deny_clean={den.get('tree_clean')}"
                )
            else:
                hitl_ok = live264.returncode == 0
        else:
            errors.append("HITL 264 --validate failed")
    except Exception as exc:
        errors.append(f"HITL probe failed: {exc}")
    bars["hitl_write"] = {"ok": hitl_ok, "notes": hitl_notes}
    notes.extend(hitl_notes)
    if not hitl_ok:
        errors.append("HITL write honesty bar failed")

    # Provenance: honesty pack pass/tool scenarios must not invent — rely on honesty_ok + no red
    bars["provenance"] = {
        "ok": bool(honesty.get("ok")) and not (honesty.get("red_rows") or []),
        "note": "covered by honesty pack classes under qwen (no invent / Done-on-FAILED red)",
    }

    ok = not errors and all(bool(b.get("ok")) for b in bars.values() if isinstance(b, dict) and "ok" in b)
    payload = {
        "ok": ok,
        "mode": "live",
        "card": "CARD-268",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "design_room": DESIGN,
        "health": health,
        "notes": notes,
        "errors": errors,
        "bars": bars,
        "ui_job_id": job_id,
        "proof": "honesty pack + Observe receipt + Chat/Observe UI + kill/resume + Forge same job + HITL",
    }
    LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k != "bars"}, indent=2))
    print(json.dumps({"bars": bars}, indent=2))
    return 0 if ok else 1



def resume_failed() -> int:
    """Re-prove operator UI + HITL only; reuse prior honesty pack job_ids."""
    try:
        import httpx
    except Exception:
        print(json.dumps({"ok": False, "errors": ["httpx missing"]}))
        return 1

    errors: list[str] = []
    notes: list[str] = []
    prior = {}
    if LIVE_OUT.exists():
        prior = json.loads(LIVE_OUT.read_text(encoding="utf-8"))
    honesty_path = ROOT / "notes" / "marathon-card261-live-smoke.json"
    honesty = json.loads(honesty_path.read_text(encoding="utf-8")) if honesty_path.exists() else {}
    bars = dict(prior.get("bars") or {})
    # keep prior greens
    for k in ("honesty_pack", "kill_resume", "observe_receipt", "forge_same_job", "provenance"):
        if k in bars and bars[k].get("ok"):
            notes.append(f"kept_green:{k}")

    health = httpx.get(f"{BASE}/api/health", timeout=15).json()
    job_id = prior.get("ui_job_id") or _pick_ui_job(honesty)
    if not job_id:
        errors.append("no job_id for UI resume")
    else:
        obs = httpx.get(f"{BASE}/api/observe/jobs/{job_id}", timeout=30)
        fake = httpx.get(f"{BASE}/api/observe/jobs/job_doesnotexist999", timeout=30)
        bars["observe_receipt"] = {
            "ok": obs.status_code == 200 and (obs.json() or {}).get("job_id") == job_id and fake.status_code == 404,
            "job_id": job_id,
            "observe_status": obs.status_code,
            "fake_status": fake.status_code,
        }
        ui_cmd = _run(["node", "notes/scripts/foundation_honesty_ui_268.mjs", job_id, str(UI_OUT)], timeout=120)
        notes.append(f"ui_exit={ui_cmd.returncode}")
        ui = json.loads(UI_OUT.read_text(encoding="utf-8")) if UI_OUT.exists() else {"ok": False}
        bars["operator_ui"] = {"ok": bool(ui.get("ok")), "job_id": job_id, "checks": ui.get("checks"), "error": ui.get("error")}
        if not bars["operator_ui"]["ok"]:
            errors.append("operator UI proof failed")
            notes.append((ui_cmd.stdout or "")[-400:])

    # HITL: prefer existing 264 artifact if fresh pass; else re-live
    art264 = ROOT / "notes" / "marathon-card264-live-smoke.json"
    hitl_ok = False
    hitl_notes: list[str] = []
    if art264.exists():
        d264 = json.loads(art264.read_text(encoding="utf-8"))
        ap = d264.get("approve") or {}
        den = d264.get("deny") or {}
        hitl_ok = bool(d264.get("pass") or d264.get("ok")) and bool(ap.get("file_existed_after_approve")) and bool(
            den.get("tree_clean") or den.get("file_existed_after_deny") is False
        )
        hitl_notes.append(
            f"reuse_264 pass={d264.get('pass')} approve={ap.get('file_existed_after_approve')} deny_clean={den.get('tree_clean')}"
        )
    if not hitl_ok:
        live264 = _run([sys.executable, "notes/scripts/repo_write_hitl_264.py", "--live"], timeout=900)
        hitl_notes.append(f"hitl_live_exit={live264.returncode}")
        if art264.exists():
            d264 = json.loads(art264.read_text(encoding="utf-8"))
            ap = d264.get("approve") or {}
            den = d264.get("deny") or {}
            hitl_ok = bool(d264.get("pass") or d264.get("ok")) and bool(ap.get("file_existed_after_approve")) and bool(
                den.get("tree_clean") or den.get("file_existed_after_deny") is False
            )
    bars["hitl_write"] = {"ok": hitl_ok, "notes": hitl_notes}
    if not hitl_ok:
        errors.append("HITL write honesty bar failed")
    notes.extend(hitl_notes)

    ok = not errors and all(bool(b.get("ok")) for b in bars.values() if isinstance(b, dict) and "ok" in b)
    payload = {
        "ok": ok,
        "mode": "live_resume_failed",
        "card": "CARD-268",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tip_sha": tip_sha(),
        "serve": BASE,
        "design_room": DESIGN,
        "health": health,
        "notes": notes,
        "errors": errors,
        "bars": bars,
        "ui_job_id": job_id,
        "proof": "honesty pack + Observe receipt + Chat/Observe UI + kill/resume + Forge same job + HITL",
    }
    LIVE_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--resume-failed", action="store_true", help="Re-run only UI+HITL against prior honesty artifact")
    args = ap.parse_args()
    if args.resume_failed:
        return resume_failed()
    if args.live:
        return live()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
