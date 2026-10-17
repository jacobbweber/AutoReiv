"""Local inference port auto-probing for Models / Settings Studio and startup [CARD-703].

Adapted from Agent-OS (agent_os/local_setup.py, docs/architecture-comparison-crucible-agent-os.md §6 & §7.2):
- Scans standard local inference ports (8000, 8006, 11434 by default, or AUTOREIV_PROBE_PORTS) plus any
  configured local/LAN provider URLs.
- Queries OpenAI-compatible GET /v1/models with a short 1.0s timeout.
- Filters out non-model HTTP servers (e.g. 404s or non-list payloads) and returns structured server + model cards.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Iterable, Mapping, Sequence

DEFAULT_PROBE_PORTS: tuple[int, ...] = (8000, 8006, 11434)
PROBE_PORTS_ENV = "AUTOREIV_PROBE_PORTS"
DEFAULT_PROBE_TIMEOUT_SECONDS = 1.0


def parse_probe_ports(raw: str | Iterable[int] | None = None) -> list[int]:
    """Parse a comma/space-separated port list or iterable of ints, falling back to DEFAULT_PROBE_PORTS."""
    source: Any = raw
    if source is None:
        source = os.environ.get(PROBE_PORTS_ENV, "")
    ports: list[int] = []
    if isinstance(source, str):
        tokens = re.split(r"[\s,;]+", source.strip())
    elif isinstance(source, Iterable):
        tokens = [str(item) for item in source]
    else:
        tokens = []
    for tok in tokens:
        clean = str(tok).strip()
        if not clean:
            continue
        try:
            val = int(clean)
        except ValueError:
            continue
        if 1 <= val <= 65535 and val not in ports:
            ports.append(val)
    return ports if ports else list(DEFAULT_PROBE_PORTS)


def _infer_provider_id(port: int | None, url: str = "") -> str:
    lower = url.lower()
    if port == 11434 or ":11434" in lower or "ollama" in lower:
        return "ollama"
    if port == 1234 or ":1234" in lower or "lmstudio" in lower:
        return "lmstudio"
    return "vllm"


def _normalize_target_from_url(raw_url: str, default_provider: str | None = None) -> dict[str, Any] | None:
    clean = str(raw_url or "").strip().rstrip("/")
    if not clean:
        return None
    if not clean.startswith(("http://", "https://")):
        clean = f"http://{clean}"
    parsed = urllib.parse.urlparse(clean)
    if not parsed.hostname:
        return None
    host = parsed.hostname
    port = parsed.port
    scheme = parsed.scheme or "http"
    provider_id = default_provider or _infer_provider_id(port, clean)
    host_port = f"{host}:{port}" if port else host
    if provider_id == "ollama":
        base_url = f"{scheme}://{host_port}"
    else:
        base_url = clean if clean.endswith("/v1") else f"{scheme}://{host_port}/v1"
    models_url = f"{scheme}://{host_port}/v1/models"
    return {
        "provider_id": provider_id,
        "host": host,
        "port": port or (11434 if provider_id == "ollama" else 8000),
        "base_url": base_url,
        "models_url": models_url,
    }


def build_probe_targets(
    ports: Sequence[int] | None = None,
    *,
    extra_urls: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Build deduplicated probe targets from ports and optional extra URLs."""
    resolved_ports = parse_probe_ports(ports)
    seen_models_urls: set[str] = set()
    targets: list[dict[str, Any]] = []

    for port in resolved_ports:
        provider_id = _infer_provider_id(port)
        base_url = f"http://127.0.0.1:{port}" if provider_id == "ollama" else f"http://127.0.0.1:{port}/v1"
        models_url = f"http://127.0.0.1:{port}/v1/models"
        if models_url not in seen_models_urls:
            seen_models_urls.add(models_url)
            targets.append(
                {
                    "provider_id": provider_id,
                    "host": "127.0.0.1",
                    "port": port,
                    "base_url": base_url,
                    "models_url": models_url,
                }
            )

    for raw in extra_urls or []:
        target = _normalize_target_from_url(raw)
        if target and target["models_url"] not in seen_models_urls:
            seen_models_urls.add(target["models_url"])
            targets.append(target)

    return targets


def _default_http_get(url: str, timeout: float) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 200))
            raw = resp.read().decode("utf-8", errors="replace")
            return status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        return int(exc.code), {}


def _extract_model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    items = payload.get("data")
    if not isinstance(items, list):
        items = payload.get("models")
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        mid = str(item.get("id") or item.get("name") or "").strip()
        if mid and mid not in out:
            out.append(mid)
    return out


def probe_single_endpoint(
    target: Mapping[str, Any],
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    http_get: Callable[[str, float], tuple[int, Any]] | None = None,
) -> dict[str, Any] | None:
    """Probe a single /v1/models target and return server metadata when live models are found."""
    getter = http_get or _default_http_get
    models_url = str(target.get("models_url") or "")
    if not models_url:
        return None
    started = time.monotonic()
    try:
        status, payload = getter(models_url, float(timeout))
    except Exception:
        return None
    latency_ms = round((time.monotonic() - started) * 1000.0, 1)
    if status != 200:
        return None
    model_ids = _extract_model_ids(payload)
    if not model_ids:
        return None
    return {
        "provider_id": str(target.get("provider_id") or "vllm"),
        "host": str(target.get("host") or "127.0.0.1"),
        "port": int(target.get("port") or 0),
        "base_url": str(target.get("base_url") or ""),
        "models_url": models_url,
        "models": model_ids,
        "default_model": model_ids[0],
        "latency_ms": latency_ms,
    }


def _configured_local_urls(store: Any) -> list[str]:
    urls: list[str] = []
    if store is not None and hasattr(store, "get_setting"):
        try:
            prov_cfg = store.get_setting("provider_settings") or {}
            providers = prov_cfg.get("providers") if isinstance(prov_cfg, Mapping) else {}
            if isinstance(providers, Mapping):
                for pid, entry in providers.items():
                    if pid in ("ollama", "vllm", "lmstudio") and isinstance(entry, Mapping):
                        burl = str(entry.get("base_url") or "").strip()
                        if burl and burl not in urls:
                            urls.append(burl)
        except Exception:
            pass
    for env_key in ("AUTOREIV_QA_VLLM_URL", "OLLAMA_HOST"):
        env_val = os.environ.get(env_key, "").strip()
        if env_val and env_val not in urls:
            urls.append(env_val)
    return urls


def probe_local_endpoints(
    *,
    store: Any = None,
    ports: Sequence[int] | None = None,
    extra_urls: Sequence[str] | None = None,
    timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    http_get: Callable[[str, float], tuple[int, Any]] | None = None,
) -> dict[str, Any]:
    """Scan local ports and configured local/LAN provider URLs for OpenAI-compatible /v1/models endpoints."""
    resolved_ports = parse_probe_ports(ports)
    combined_extra = list(extra_urls or [])
    for url in _configured_local_urls(store):
        if url not in combined_extra:
            combined_extra.append(url)

    targets = build_probe_targets(resolved_ports, extra_urls=combined_extra)
    servers: list[dict[str, Any]] = []
    flat_models: list[dict[str, Any]] = []

    for target in targets:
        hit = probe_single_endpoint(target, timeout=timeout, http_get=http_get)
        if hit is None:
            continue
        servers.append(hit)
        for model_name in hit["models"]:
            flat_models.append(
                {
                    "provider_id": hit["provider_id"],
                    "host": hit["host"],
                    "port": hit["port"],
                    "base_url": hit["base_url"],
                    "models_url": hit["models_url"],
                    "model": model_name,
                    "latency_ms": hit["latency_ms"],
                    "label": f"{model_name} ({hit['provider_id']} @ {hit['host']}:{hit['port']})",
                }
            )

    return {
        "scanned_ports": resolved_ports,
        "scanned_urls": [t["models_url"] for t in targets],
        "servers": servers,
        "models": flat_models,
        "total_servers": len(servers),
        "total_models": len(flat_models),
    }


def activate_discovered_model(
    store: Any,
    gateway: Any = None,
    *,
    provider_id: str,
    base_url: str,
    model: str,
) -> dict[str, str]:
    """Persist and register a discovered local provider endpoint and default model."""
    clean_pid = str(provider_id or "ollama").strip().lower()
    clean_url = str(base_url or "").strip()
    clean_model = str(model or "default").strip()

    if store is not None and hasattr(store, "get_setting") and hasattr(store, "set_setting"):
        prov_cfg = dict(store.get_setting("provider_settings") or {})
        providers = dict(prov_cfg.get("providers") or {})
        entry = dict(providers.get(clean_pid) or {})
        entry["base_url"] = clean_url
        entry["default_model_id"] = clean_model
        providers[clean_pid] = entry
        prov_cfg["default_provider_id"] = clean_pid
        prov_cfg["default_model_id"] = clean_model
        if clean_pid == "ollama":
            prov_cfg["ollama_host"] = clean_url
        else:
            prov_cfg["openai_base_url"] = clean_url
        prov_cfg["providers"] = providers
        store.set_setting("provider_settings", prov_cfg)

        matrix_cfg = dict(store.get_setting("purpose_matrix") or store.get_setting("model_purpose_matrix") or {})
        matrix_cfg["default_model"] = clean_model
        purposes = dict(matrix_cfg.get("purposes") or {})
        purposes.setdefault("general", clean_model)
        matrix_cfg["purposes"] = purposes
        store.set_setting("purpose_matrix", matrix_cfg)
        store.set_setting("model_purpose_matrix", matrix_cfg)

    if gateway is not None:
        try:
            from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
            from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

            if clean_pid == "ollama":
                adapter = OllamaProviderAdapter(base_url=clean_url, provider_id=clean_pid)
            else:
                adapter = OpenAIProviderAdapter(base_url=clean_url, api_key="EMPTY", provider_id=clean_pid)
            if hasattr(gateway, "register_provider"):
                gateway.register_provider(adapter)
            gateway.default_provider_id = clean_pid
            gateway.default_model_id = clean_model
        except Exception:
            pass

    return {
        "provider_id": clean_pid,
        "base_url": clean_url,
        "model": clean_model,
    }
