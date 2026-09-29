"""CARD-580: test_provider_connectivity probes the configured providers, not OLLAMA_HOST."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.application.skills.system_agent_tools import SystemAgentTools
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _tools(provider_settings=None, agent_model_settings=None):
    store = SQLiteStateStore(db_path=":memory:")
    if provider_settings is not None:
        store.set_setting("provider_settings", provider_settings)
    if agent_model_settings is not None:
        store.set_setting("agent_model_settings", agent_model_settings)
    return SystemAgentTools(store=store, telemetry=TelemetryCollector(store=store))


def _ok(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    return r


SPARK = {
    "default_provider_id": "vllm",
    "default_model_id": "qwen3.8-27b-fp8",
    "providers": {"vllm": {"base_url": "http://192.168.1.218:8099/v1", "default_model_id": "qwen3.8-27b-fp8"}},
}


def test_no_args_probes_the_configured_default_provider_not_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
    tools = _tools(SPARK)
    with patch("httpx.get", return_value=_ok({"data": [{"id": "qwen3.8-27b-fp8"}]})) as g:
        res = tools.test_provider_connectivity()
    assert g.call_args_list[0].args[0] == "http://192.168.1.218:8099/v1/models"
    assert res["provider_id"] == "vllm"
    assert res["reachable"] is True
    assert res["endpoint_source"] == "settings"


def test_no_args_also_probes_each_agent_override_endpoint(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
    overrides = {"developer": {"provider": "ollama", "model": "qwen3.8:latest", "api_base_url": "http://192.168.1.29:11434"}}
    tools = _tools(SPARK, overrides)

    def fake_get(url, **_kw):
        if url.endswith("/api/tags"):
            return _ok({"models": [{"name": "qwen3.8:latest"}]})
        return _ok({"data": [{"id": "qwen3.8-27b-fp8"}]})

    with patch("httpx.get", side_effect=fake_get) as g:
        res = tools.test_provider_connectivity()
    urls = [c.args[0] for c in g.call_args_list]
    assert "http://192.168.1.29:11434/api/tags" in urls
    assert not any("0.0.0.0" in u for u in urls)
    ov = res["agent_overrides"][0]
    assert ov["agent_id"] == "developer" and ov["reachable"] is True and ov["model"] == "qwen3.8:latest"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0.0.0.0", "http://127.0.0.1:11434"),
        ("http://0.0.0.0", "http://127.0.0.1:11434"),
        ("0.0.0.0:11500", "http://127.0.0.1:11500"),
        ("http://192.168.1.29:11434", "http://192.168.1.29:11434"),
    ],
)
def test_ollama_bind_address_becomes_probeable(raw, expected):
    assert SystemAgentTools._normalize_probe_url(raw, "ollama") == expected


def test_explicit_ollama_without_settings_uses_normalized_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
    tools = _tools({"providers": {}})
    with patch("httpx.get", return_value=_ok({"models": []})) as g:
        tools.test_provider_connectivity(provider_id="ollama")
    assert "0.0.0.0" not in g.call_args_list[0].args[0]


def test_saved_provider_base_url_wins_over_legacy_and_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
    cfg = {"ollama_host": "http://10.0.0.5:11434", "providers": {"ollama": {"base_url": "http://192.168.1.29:11434"}}}
    tools = _tools(cfg)
    with patch("httpx.get", return_value=_ok({"models": []})) as g:
        res = tools.test_provider_connectivity(provider_id="ollama")
    assert g.call_args_list[0].args[0] == "http://192.168.1.29:11434/api/tags"
    assert res["endpoint"] == "http://192.168.1.29:11434"
