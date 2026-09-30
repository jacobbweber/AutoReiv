"""CARD-584: model plan = one model per machine (Spark nemotron only; Nimo qwen3.8 only for Architect + Developer)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "apply_model_plan.py"


def _mod():
    spec = importlib.util.spec_from_file_location("apply_model_plan_card584", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _before():
    settings = {
        "providers": {"default_provider_id": "vllm", "default_model_id": "qwen3.8-27b-fp8"},
        "matrix": {"default_model": "qwen3.8-27b-fp8", "purposes": {"summary": "qwen3.8-27b-fp8"},
                   "model_context_windows": {"qwen3.8-27b-fp8": 262144}, "max_concurrent_generations": 1},
    }
    agents = {aid: {"id": aid, "provider": "default", "model": "default"} for aid in
              ("autoreiv", "tutor", "toolsmith", "direct")}
    agents["tutor"] = {"id": "tutor", "provider": "vllm", "model": "qwen3.8-27b-fp8"}
    agents["architect"] = {"id": "architect", "provider": "vllm", "model": "qwen3.8-27b-fp8", "context_window": 262144}
    agents["developer"] = {"id": "developer", "provider": "ollama", "model": "qwen3.8:latest",
                           "api_base_url": "http://192.168.1.29:11434", "context_window": 262144}
    return settings, agents


def _apply(settings, agents, changes):
    for _method, path, body in changes:
        if path == "/api/settings/providers":
            settings["providers"] = {"default_provider_id": body["default_provider_id"],
                                     "default_model_id": body["default_model_id"]}
        elif path == "/api/settings/matrix":
            settings["matrix"] = body
        else:
            agents[path.rsplit("/", 1)[1]] = body


def test_architect_moves_to_nimo_and_nothing_names_the_retired_spark_model():
    m = _mod()
    settings, agents = _before()
    assert m.plan_problems(settings, agents)
    changes = m.build_changes(settings, agents, ctx=262144)
    paths = [p for _, p, _ in changes]
    assert "/api/agents/architect" in paths and "/api/agents/developer" not in paths  # Developer already on plan
    _apply(settings, agents, changes)
    assert m.plan_problems(settings, agents) == []
    arch = agents["architect"]
    assert (arch["provider"], arch["model"], arch["api_base_url"], arch["context_window"]) == (
        "ollama", "qwen3.8:latest", "http://192.168.1.29:11434", 262144)
    assert agents["tutor"]["provider"] == "default" and agents["tutor"]["model"] == "default"
    assert settings["providers"]["default_model_id"] == "nemotron-3.5-lightning"
    assert settings["matrix"]["default_model"] == "nemotron-3.5-lightning"
    assert settings["matrix"]["model_context_windows"] == {"nemotron-3.5-lightning": 262144, "qwen3.8:latest": 262144}
    assert settings["matrix"]["purposes"] == {}
    assert "qwen3.8-27b-fp8" not in repr((settings, agents))


def test_gateway_reported_context_is_used():
    m = _mod()
    settings, agents = _before()
    changes = m.build_changes(settings, agents, ctx=131072)
    matrix = next(b for _, p, b in changes if p == "/api/settings/matrix")
    assert matrix["model_context_windows"]["nemotron-3.5-lightning"] == 131072


def test_plan_is_idempotent():
    m = _mod()
    settings, agents = _before()
    _apply(settings, agents, m.build_changes(settings, agents, ctx=262144))
    again = [p for _, p, _ in m.build_changes(settings, agents, ctx=262144)]
    assert again == ["/api/settings/providers", "/api/settings/matrix"]


def test_problems_name_every_swap_risk():
    m = _mod()
    settings, agents = _before()
    _apply(settings, agents, m.build_changes(settings, agents, ctx=262144))
    agents["developer"]["model"] = "qwen3-coder:latest"
    agents["toolsmith"] = {"provider": "vllm", "model": "gemma-4-26b-a4b"}
    settings["matrix"]["purposes"] = {"vision": "gemma-4-26b-a4b"}
    problems = " | ".join(m.plan_problems(settings, agents))
    assert "developer is ollama/qwen3-coder:latest" in problems
    assert "toolsmith is vllm/gemma-4-26b-a4b" in problems
    assert "purpose vision uses gemma-4-26b-a4b" in problems
