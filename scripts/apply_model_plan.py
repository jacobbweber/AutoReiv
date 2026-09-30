r"""CARD-584: apply Jacob's 2026-09-29 model plan to a running AutoReiv (real serve or throwaway) through its API.

Plan:
- Platform default (AutoReiv, Tutor, Toolsmith, Direct inherit it): nemotron-3.5-lightning on the Spark gateway
  (vLLM swap gateway :8099), context = what the gateway reports for it (262144 on 2026-09-29).
- Architect: qwen3.8-27b-fp8 on the same gateway (agent override), context 262144.
- Developer: unchanged (Nimo Ollama qwen3.8:latest, 262144); only checked.

Nothing on Spark or Nimo is changed. Usage:
    .venv\Scripts\python.exe scripts/apply_model_plan.py --base http://127.0.0.1:8770 [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import httpx

SPARK_URL = "http://192.168.1.218:8099/v1"
SPARK_BACKEND_URL = "http://192.168.1.218:8006/v1"  # vLLM behind the swap gateway (serves the loaded model)
DEFAULT_MODEL = "nemotron-3.5-lightning"
ARCHITECT_MODEL = "qwen3.8-27b-fp8"
ARCHITECT_CONTEXT = 262144
FALLBACK_CONTEXT = 262144  # vLLM behind the gateway reported max_model_len 262144 for nemotron on 2026-09-29
INHERIT_AGENTS = ("autoreiv", "tutor", "toolsmith", "direct")
DEVELOPER = {"provider": "ollama", "model": "qwen3.8:latest", "context_window": 262144}


def gateway_context(urls: list[str], model: str, fallback: int) -> tuple[int, str]:
    """max_model_len reported for ``model``: the gateway listing, then vLLM behind it (when that model is loaded)."""
    for url in urls:
        try:
            data = httpx.get(f"{url}/models", timeout=15).json().get("data") or []
        except Exception as exc:  # noqa: BLE001
            print(f"  ({url}/models unavailable: {exc})")
            continue
        for item in data:
            if item.get("id") == model and int(item.get("max_model_len") or 0) > 0:
                return int(item["max_model_len"]), f"{url}/models"
    return fallback, "fallback (vLLM max_model_len seen 2026-09-29)"


def agent(base: str, agent_id: str) -> Dict[str, Any]:
    body = httpx.get(f"{base}/api/agents/{agent_id}", timeout=30).json()
    return body.get("agent") or body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--spark-url", default=SPARK_URL)
    ap.add_argument("--backend-url", default=SPARK_BACKEND_URL)
    ap.add_argument("--context", type=int, default=FALLBACK_CONTEXT, help="used when the gateway does not report one")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    settings = httpx.get(f"{base}/api/settings", timeout=30).json()
    prov = settings.get("providers") or {}
    matrix = dict(settings.get("matrix") or {})
    print(f"before: default {prov.get('default_provider_id')}/{prov.get('default_model_id')}; "
          f"windows {matrix.get('model_context_windows')}")
    ctx, source = gateway_context([args.spark_url, args.backend_url], DEFAULT_MODEL, args.context)
    print(f"{DEFAULT_MODEL} context {ctx} ({source})")

    provider_body = {
        "provider_id": "vllm", "default_provider_id": "vllm", "base_url": args.spark_url,
        "openai_base_url": args.spark_url, "default_model_id": DEFAULT_MODEL, "set_as_default": True,
    }
    windows = dict(matrix.get("model_context_windows") or {})
    windows.update({DEFAULT_MODEL: ctx, ARCHITECT_MODEL: ARCHITECT_CONTEXT})
    matrix_body = {
        "default_model": DEFAULT_MODEL,
        "default_context_window": matrix.get("default_context_window"),
        "purposes": matrix.get("purposes") or {},
        "model_context_windows": windows,
        "max_concurrent_generations": matrix.get("max_concurrent_generations") or 1,
    }
    changes = [("POST", "/api/settings/providers", provider_body), ("POST", "/api/settings/matrix", matrix_body)]

    arch = agent(base, "architect")
    arch.update({"provider": "vllm", "model": ARCHITECT_MODEL, "api_base_url": None, "context_window": ARCHITECT_CONTEXT})
    changes.append(("PUT", "/api/agents/architect", arch))
    for aid in INHERIT_AGENTS:
        a = agent(base, aid)
        if (a.get("provider") or "default") != "default" or (a.get("model") or "default") != "default":
            a.update({"provider": "default", "model": "default", "api_base_url": None, "context_window": None})
            changes.append(("PUT", f"/api/agents/{aid}", a))

    for method, path, body in changes:
        short = {k: body.get(k) for k in ("provider", "model", "context_window", "default_model_id", "default_model",
                                          "model_context_windows") if k in body}
        print(f"{'would ' if args.dry_run else ''}{method} {path} {json.dumps(short)}")
        if not args.dry_run:
            r = httpx.request(method, f"{base}{path}", json=body, timeout=60)
            if r.status_code >= 400:
                print(f"  FAILED {r.status_code}: {r.text[:300]}")
                return 1

    dev = agent(base, "developer")
    dev_ok = all(dev.get(k) == v for k, v in DEVELOPER.items())
    print(f"developer: {dev.get('provider')}/{dev.get('model')} ctx {dev.get('context_window')} "
          f"({'as planned' if dev_ok else 'DIFFERENT from the plan, not changed'})")
    if not args.dry_run:
        after = httpx.get(f"{base}/api/settings", timeout=30).json()
        print(f"after: default {after['providers'].get('default_provider_id')}/{after['providers'].get('default_model_id')}; "
              f"windows {after['matrix'].get('model_context_windows')}")
        for aid in ("architect",) + INHERIT_AGENTS:
            a = agent(base, aid)
            print(f"  {aid}: {a.get('provider')}/{a.get('model')} ctx {a.get('context_window')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
