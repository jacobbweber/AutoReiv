r"""CARD-584: apply Jacob's 2026-09-29 model plan to a running AutoReiv (real serve or throwaway) through its API.

One model per machine, so nothing ever makes a machine swap models:
- Spark (vLLM gateway :8099) serves only nemotron-3.5-lightning. It is the platform default; AutoReiv, Tutor,
  Toolsmith and Direct inherit it. Context = what the gateway reports for it (262144 on 2026-09-29).
- Nimo (Ollama :11434) serves only qwen3.8:latest. Architect and Developer use it (agent overrides, context 262144)
  and share the Nimo generation pool (CARD-585).
- No agent, purpose or context-window entry names another model on either machine (the plan check fails otherwise).

Nothing on Spark or Nimo is changed. Usage:
    .venv\Scripts\python.exe scripts/apply_model_plan.py --base http://127.0.0.1:8770 [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import httpx

SPARK_URL = "http://192.168.1.218:8099/v1"
SPARK_BACKEND_URL = "http://192.168.1.218:8006/v1"  # vLLM behind the gateway (serves the loaded model)
NIMO_URL = "http://192.168.1.29:11434"
SPARK_MODEL = "nemotron-3.5-lightning"
NIMO_MODEL = "qwen3.8:latest"
NIMO_CONTEXT = 262144
FALLBACK_CONTEXT = 262144  # vLLM behind the gateway reported max_model_len 262144 for nemotron on 2026-09-29
INHERIT_AGENTS = ("autoreiv", "tutor", "toolsmith", "direct")
NIMO_AGENTS = ("architect", "developer")
RETIRED_MODELS = ("qwen3.8-27b-fp8",)  # was Architect on Spark; loading it on Spark swaps nemotron out
NIMO_AGENT = {"provider": "ollama", "model": NIMO_MODEL, "api_base_url": NIMO_URL, "context_window": NIMO_CONTEXT}
ALL_AGENTS = INHERIT_AGENTS + NIMO_AGENTS


def gateway_context(urls: List[str], model: str, fallback: int) -> Tuple[int, str]:
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


def build_changes(settings: Dict[str, Any], agents: Dict[str, Dict[str, Any]], ctx: int,
                  spark_url: str = SPARK_URL) -> List[Tuple[str, str, Dict[str, Any]]]:
    """API calls (method, path, body) that bring ``settings``/``agents`` to the plan. Pure; no network."""
    matrix = dict(settings.get("matrix") or {})
    provider_body = {
        "provider_id": "vllm", "default_provider_id": "vllm", "base_url": spark_url,
        "openai_base_url": spark_url, "default_model_id": SPARK_MODEL, "set_as_default": True,
    }
    windows = {k: v for k, v in (matrix.get("model_context_windows") or {}).items() if k not in RETIRED_MODELS}
    windows.update({SPARK_MODEL: ctx, NIMO_MODEL: NIMO_CONTEXT})
    purposes = {k: v for k, v in (matrix.get("purposes") or {}).items() if str(v) not in RETIRED_MODELS}
    matrix_body = {
        "default_model": SPARK_MODEL,
        "default_context_window": matrix.get("default_context_window"),
        "purposes": purposes,
        "model_context_windows": windows,
        "max_concurrent_generations": matrix.get("max_concurrent_generations") or 1,
    }
    changes = [("POST", "/api/settings/providers", provider_body), ("POST", "/api/settings/matrix", matrix_body)]
    for aid in NIMO_AGENTS:
        a = dict(agents[aid])
        if any(a.get(k) != v for k, v in NIMO_AGENT.items()):
            a.update(NIMO_AGENT)
            changes.append(("PUT", f"/api/agents/{aid}", a))
    for aid in INHERIT_AGENTS:
        a = dict(agents[aid])
        if (a.get("provider") or "default") != "default" or (a.get("model") or "default") != "default":
            a.update({"provider": "default", "model": "default", "api_base_url": None, "context_window": None})
            changes.append(("PUT", f"/api/agents/{aid}", a))
    return changes


def plan_problems(settings: Dict[str, Any], agents: Dict[str, Dict[str, Any]]) -> List[str]:
    """Everything that would make Spark or Nimo load a second model (empty list = plan holds)."""
    problems: List[str] = []
    prov = settings.get("providers") or {}
    matrix = settings.get("matrix") or {}
    if prov.get("default_provider_id") != "vllm" or prov.get("default_model_id") != SPARK_MODEL:
        problems.append(f"platform default is {prov.get('default_provider_id')}/{prov.get('default_model_id')}, "
                        f"not vllm/{SPARK_MODEL}")
    if matrix.get("default_model") not in (None, "", SPARK_MODEL):
        problems.append(f"matrix default_model is {matrix.get('default_model')}")
    for name, model in (matrix.get("purposes") or {}).items():
        if model and str(model) not in (SPARK_MODEL, NIMO_MODEL):
            problems.append(f"purpose {name} uses {model}")
    for aid in ALL_AGENTS:
        a = agents.get(aid) or {}
        provider, model = a.get("provider") or "default", a.get("model") or "default"
        if aid in NIMO_AGENTS:
            if provider != "ollama" or model != NIMO_MODEL:
                problems.append(f"{aid} is {provider}/{model}, not ollama/{NIMO_MODEL}")
        elif provider not in ("default", "vllm") or model not in ("default", SPARK_MODEL):
            problems.append(f"{aid} is {provider}/{model}, not the Spark default {SPARK_MODEL}")
    return problems


def fetch(base: str) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    settings = httpx.get(f"{base}/api/settings", timeout=30).json()
    agents = {}
    for aid in ALL_AGENTS:
        body = httpx.get(f"{base}/api/agents/{aid}", timeout=30).json()
        agents[aid] = body.get("agent") or body
    return settings, agents


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--spark-url", default=SPARK_URL)
    ap.add_argument("--backend-url", default=SPARK_BACKEND_URL)
    ap.add_argument("--context", type=int, default=FALLBACK_CONTEXT, help="used when the gateway does not report one")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="only report plan problems (exit 1 if any)")
    args = ap.parse_args(argv)
    base = args.base.rstrip("/")

    settings, agents = fetch(base)
    if args.check:
        problems = plan_problems(settings, agents)
        print("\n".join(f"PROBLEM: {p}" for p in problems) or "plan holds: Spark nemotron only, Nimo qwen3.8 only")
        return 1 if problems else 0
    prov = settings.get("providers") or {}
    print(f"before: default {prov.get('default_provider_id')}/{prov.get('default_model_id')}; "
          f"windows {(settings.get('matrix') or {}).get('model_context_windows')}")
    ctx, source = gateway_context([args.spark_url, args.backend_url], SPARK_MODEL, args.context)
    print(f"{SPARK_MODEL} context {ctx} ({source})")

    for method, path, body in build_changes(settings, agents, ctx, args.spark_url):
        short = {k: body.get(k) for k in ("provider", "model", "api_base_url", "context_window", "default_model_id",
                                          "default_model", "model_context_windows") if k in body}
        print(f"{'would ' if args.dry_run else ''}{method} {path} {json.dumps(short)}")
        if not args.dry_run:
            r = httpx.request(method, f"{base}{path}", json=body, timeout=60)
            if r.status_code >= 400:
                print(f"  FAILED {r.status_code}: {r.text[:300]}")
                return 1
    if args.dry_run:
        return 0
    settings, agents = fetch(base)
    for aid in ALL_AGENTS:
        a = agents[aid]
        print(f"  {aid}: {a.get('provider')}/{a.get('model')} ctx {a.get('context_window')}")
    problems = plan_problems(settings, agents)
    print("\n".join(f"PROBLEM: {p}" for p in problems) or "plan holds: Spark nemotron only, Nimo qwen3.8 only")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
