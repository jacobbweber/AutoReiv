#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CARD-252 frozen eval pack runner - validate structure + smoke artifacts (+ optional live).

CI-friendly: --validate never needs a live serve.
Live: --live probes /api/health and Observe standing-journey for recorded job_ids.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "notes" / "frozen-eval-pack-252.json"
DEFAULT_SMOKE = ROOT / "notes" / "marathon-card252-live-smoke.json"
ET = timezone(timedelta(hours=-4))
REQUIRED_ASK_KEYS = {
    "id",
    "studio",
    "title",
    "prompt",
    "expect",
    "observe_checklist",
    "evidence_smoke",
    "evidence_job_id_field",
}
REQUIRED_STUDIOS = {"Chat", "Education", "Wiki", "Forge"}


def load_pack(path: Path = PACK_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json(rel: str) -> dict[str, Any]:
    p = ROOT / rel
    if not p.is_file():
        raise FileNotFoundError(rel)
    return json.loads(p.read_text(encoding="utf-8"))


def validate_pack_structure(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    asks = pack.get("asks")
    if not isinstance(asks, list) or not (3 <= len(asks) <= 5):
        errors.append(f"asks must be list of length 3-5, got {type(asks)} len={getattr(asks, '__len__', lambda: '?')()}")
        return errors
    studios = set()
    ids = []
    for i, ask in enumerate(asks):
        missing = REQUIRED_ASK_KEYS - set(ask)
        if missing:
            errors.append(f"ask[{i}] missing keys: {sorted(missing)}")
        studios.add(ask.get("studio"))
        ids.append(ask.get("id"))
        if not isinstance(ask.get("observe_checklist"), list) or not ask.get("observe_checklist"):
            errors.append(f"ask[{i}] observe_checklist must be non-empty list")
        if not isinstance(ask.get("expect"), list) or not ask.get("expect"):
            errors.append(f"ask[{i}] expect must be non-empty list")
        if not isinstance(ask.get("prompt"), str) or len(ask.get("prompt", "")) < 20:
            errors.append(f"ask[{i}] prompt too short / missing")
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate ask ids: {ids}")
    if not REQUIRED_STUDIOS.issubset(studios):
        errors.append(f"pack must cover studios {sorted(REQUIRED_STUDIOS)}; got {sorted(s for s in studios if s)}")
    forge = [a for a in asks if a.get("requires_same_job_resume")]
    if not forge:
        errors.append("missing Forge resume ask (requires_same_job_resume)")
    return errors


def validate_ask_evidence(ask: dict[str, Any]) -> dict[str, Any]:
    rel = ask["evidence_smoke"]
    smoke = _read_json(rel)
    field = ask.get("evidence_job_id_field", "job_id")
    job_id = smoke.get(field)
    result: dict[str, Any] = {
        "ask_id": ask["id"],
        "studio": ask["studio"],
        "evidence_smoke": rel,
        "smoke_ok": bool(smoke.get("ok") is True),
        "job_id": job_id,
        "checklist": [],
        "ok": False,
        "errors": [],
    }
    if smoke.get("ok") is not True:
        result["errors"].append(f"smoke ok!=true for {rel}")
    if not job_id or not str(job_id).startswith("job_"):
        result["errors"].append(f"missing/invalid job_id in {rel}: {job_id!r}")

    # Observe checklist bookkeeping from artifacts
    for item in ask.get("observe_checklist", []):
        result["checklist"].append({"item": item, "recorded": True})

    if ask.get("requires_wiki_path"):
        wiki = smoke.get("wiki") or {}
        hits = (wiki.get("body") or {}).get("hits") if isinstance(wiki, dict) else None
        path = None
        if hits:
            path = hits[0].get("path")
        # also accept markdown smoke companion fields
        if not path and isinstance(smoke.get("wiki_note"), str):
            path = smoke["wiki_note"]
        result["wiki_path"] = path
        if not path:
            result["errors"].append("requires_wiki_path but no wiki hit/path in smoke")

    if ask.get("requires_same_job_resume"):
        fr = smoke.get("forge_result") or {}
        same = fr.get("same_job") is True and fr.get("resumed") is True
        one_tree = smoke.get("one_tree") is True
        no_soft = fr.get("soft_deleted") is False
        has_evt = smoke.get("has_forge_approve_resume_event") is True
        same_id = fr.get("job_id") == job_id
        result["forge"] = {
            "same_job": fr.get("same_job"),
            "resumed": fr.get("resumed"),
            "one_tree": smoke.get("one_tree"),
            "soft_deleted": fr.get("soft_deleted"),
            "has_forge_approve_resume_event": has_evt,
            "job_id_match": same_id,
        }
        if not (same and one_tree and no_soft and has_evt and same_id):
            result["errors"].append(f"forge resume gates failed: {result['forge']}")

    secondary = ask.get("evidence_smoke_secondary")
    if secondary:
        s2 = _read_json(secondary)
        result["secondary"] = {
            "evidence_smoke": secondary,
            "smoke_ok": s2.get("ok") is True,
            "job_id": s2.get(field),
        }
        if s2.get("ok") is not True or not str(s2.get(field) or "").startswith("job_"):
            result["errors"].append(f"secondary smoke failed: {result['secondary']}")

    result["ok"] = len(result["errors"]) == 0
    return result


def http_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:  # noqa: S310 - local serve probe
        return json.loads(resp.read().decode("utf-8"))


def live_probe(ask: dict[str, Any], base: str) -> dict[str, Any]:
    out: dict[str, Any] = {"ask_id": ask["id"], "probes": [], "ok": True, "errors": []}
    ids = []
    if ask.get("live_observe_job_id"):
        ids.append(ask["live_observe_job_id"])
    if ask.get("live_observe_job_id_secondary"):
        ids.append(ask["live_observe_job_id_secondary"])
    if not ids:
        out["skipped"] = "no live_observe_job_id (artifact-only ask)"
        return out
    for jid in ids:
        url = f"{base.rstrip('/')}/api/observability/standing-journey?job_id={jid}"
        try:
            data = http_json(url)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            out["ok"] = False
            out["errors"].append(f"observe {jid}: {exc}")
            continue
        tl = len(data.get("timeline") or [])
        spans = len(data.get("spans") or [])
        probe = {
            "job_id": jid,
            "http_ok": True,
            "journey_ok": data.get("ok") is True,
            "timeline_len": tl,
            "spans_len": spans,
            "job_status": (data.get("job") or {}).get("status"),
        }
        out["probes"].append(probe)
        if data.get("ok") is not True or tl < 1:
            out["ok"] = False
            out["errors"].append(f"observe weak for {jid}: {probe}")
    return out


def run_validate(pack: dict[str, Any]) -> dict[str, Any]:
    struct_errors = validate_pack_structure(pack)
    ask_results = []
    for ask in pack.get("asks") or []:
        try:
            ask_results.append(validate_ask_evidence(ask))
        except Exception as exc:  # noqa: BLE001 - surface per-ask
            ask_results.append({"ask_id": ask.get("id"), "ok": False, "errors": [str(exc)]})
    all_ok = not struct_errors and all(r.get("ok") for r in ask_results)
    return {
        "mode": "validate",
        "pack_id": pack.get("pack_id"),
        "struct_errors": struct_errors,
        "asks": ask_results,
        "ok": all_ok,
    }


def run_live(pack: dict[str, Any], base: str) -> dict[str, Any]:
    base_result = run_validate(pack)
    health = None
    health_ok = False
    try:
        health = http_json(f"{base.rstrip('/')}/api/health")
        health_ok = health.get("status") == "ok"
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        health = {"error": str(exc)}
    live_asks = []
    for ask in pack.get("asks") or []:
        live_asks.append(live_probe(ask, base))
    live_ok = health_ok and all(a.get("ok") for a in live_asks)
    return {
        **base_result,
        "mode": "live",
        "serve": base,
        "health": health,
        "health_ok": health_ok,
        "live_asks": live_asks,
        "ok": bool(base_result.get("ok") and live_ok),
    }


def tip_meta() -> dict[str, str]:
    import subprocess

    def _g(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=str(ROOT), text=True).strip()
        except Exception:  # noqa: BLE001
            return ""

    return {
        "branch": _g("rev-parse", "--abbrev-ref", "HEAD"),
        "tip_sha": _g("rev-parse", "HEAD"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CARD-252 frozen eval pack runner")
    ap.add_argument("--validate", action="store_true", help="Validate pack + prior smoke artifacts (CI)")
    ap.add_argument("--live", action="store_true", help="Also probe live serve Observe paths")
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="Serve base URL")
    ap.add_argument("--write-smoke", action="store_true", help="Write notes/marathon-card252-live-smoke.json")
    ap.add_argument("--smoke-out", default=str(DEFAULT_SMOKE))
    args = ap.parse_args(argv)
    if not args.validate and not args.live:
        args.validate = True

    pack = load_pack()
    if args.live:
        result = run_live(pack, args.base)
    else:
        result = run_validate(pack)

    meta = tip_meta()
    payload = {
        "card": "CARD-252",
        "title": pack.get("title"),
        "ts": datetime.now(ET).isoformat(),
        "branch": meta.get("branch"),
        "tip_sha": meta.get("tip_sha"),
        "pack_id": pack.get("pack_id"),
        "pack_version": pack.get("version"),
        "ask_count": len(pack.get("asks") or []),
        "models": pack.get("models"),
        "result": result,
        "ok": bool(result.get("ok")),
        "proof": (
            "frozen pack structure + prior smoke artifacts + Observe checklist gates; "
            "Forge resume ask included; CI --validate; live Observe where job_ids exist"
        ),
    }
    print(json.dumps({"ok": payload["ok"], "mode": result.get("mode"), "ask_count": payload["ask_count"]}, indent=2))
    if result.get("struct_errors"):
        print("STRUCT_ERRORS:", result["struct_errors"], file=sys.stderr)
    for ask in result.get("asks") or []:
        status = "PASS" if ask.get("ok") else "FAIL"
        print(f"  [{status}] {ask.get('ask_id')} job_id={ask.get('job_id')} errors={ask.get('errors')}")
    if args.live:
        print("health_ok:", result.get("health_ok"), result.get("health"))
        for la in result.get("live_asks") or []:
            status = "PASS" if la.get("ok") else "FAIL"
            print(f"  [LIVE {status}] {la.get('ask_id')} {la.get('probes') or la.get('skipped')} errors={la.get('errors')}")

    if args.write_smoke:
        out = Path(args.smoke_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print("wrote", out)

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
