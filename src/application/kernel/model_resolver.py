"""
Agent Provider & Model Cascade Resolution [REQ-MODEL-003, CARD-156, CARD-712].
"""

from __future__ import annotations

from typing import Any

from src.domain.kernel.models import AgentProfile

KNOWN_PROVIDERS = {
    "ollama",
    "gemini",
    "openai",
    "anthropic",
    "lmstudio",
    "vllm",
    "openrouter",
    "deepseek",
    "groq",
}


def is_model_compatible_with_provider(model: str, provider_id: str) -> bool:
    """Return True when ``model`` is compatible with ``provider_id``."""
    if not model or model == "default":
        return False
    if "/" in model:
        pid, _ = model.split("/", 1)
        return pid.lower() == provider_id.lower()
    if provider_id == "ollama":
        return True
    if ":" in model:
        return False
    return True


def resolve_agent_model(agent: AgentProfile, state_store: Any, gateway: Any) -> str:
    """
    Simplified Provider & Model Cascade Resolution [REQ-MODEL-003]:
    1. Agent explicit provider and model (if not 'default')
    2. Agent explicit model override (if not 'default')
    3. Global Default provider + model from Settings (provider_settings)
    4. Gateway default_model_id / fallback
    """
    agent_provider = getattr(agent, "provider", "default")
    raw_agent_provider = str(agent_provider or "").strip().lower()
    raw_agent_model = str(agent.model or "").strip()

    # 1. Agent explicit provider override [CARD-214]
    if raw_agent_provider and raw_agent_provider != "default":
        if (
            raw_agent_model
            and raw_agent_model.lower() != "default"
            and raw_agent_model.lower() not in KNOWN_PROVIDERS
        ):
            if "/" in raw_agent_model:
                return raw_agent_model
            return f"{raw_agent_provider}/{raw_agent_model}"

        if state_store:
            prov_data = state_store.get_setting("provider_settings")
            if isinstance(prov_data, dict):
                provider_map = prov_data.get("providers") or {}
                p_cfg = provider_map.get(raw_agent_provider) or {}
                p_model = p_cfg.get("default_model_id")
                if isinstance(p_model, str) and p_model and p_model != "default":
                    if "/" in p_model:
                        return p_model
                    return f"{raw_agent_provider}/{p_model}"

        return f"{raw_agent_provider}/default"

    # 2. Agent explicit model override (without explicit provider)
    if raw_agent_model and raw_agent_model.lower() != "default" and raw_agent_model.lower() not in KNOWN_PROVIDERS:
        return raw_agent_model

    # 3. Global Default provider + model from Settings Studio
    if state_store:
        prov_data = state_store.get_setting("provider_settings")
        if isinstance(prov_data, dict):
            def_model = prov_data.get("default_model_id")
            if isinstance(def_model, str) and def_model and def_model != "default":
                return def_model
            def_prov = prov_data.get("default_provider_id")
            if isinstance(def_prov, str) and def_prov and def_prov != "default":
                return f"{def_prov}/default"

    # 4. Gateway defaults
    if gateway:
        gw_def = getattr(gateway, "default_model_id", None)
        if isinstance(gw_def, str) and gw_def and gw_def != "default":
            return gw_def
        gw_prov = getattr(gateway, "default_provider_id", None)
        if isinstance(gw_prov, str) and gw_prov:
            return f"{gw_prov}/default"
    return "default"


def ensure_agent_provider_adapter(agent: AgentProfile, gateway: Any) -> None:
    """Register or update custom provider adapter for agent via GatewayProviderFactory [CARD-156, CARD-712]."""
    if not gateway:
        return
    prov = getattr(agent, "provider", "default")
    if not prov or prov == "default":
        return
    api_base_url = getattr(agent, "api_base_url", None)
    api_key = getattr(agent, "api_key", None)
    if not api_base_url and not api_key:
        return

    from src.infrastructure.gateway.factory import GatewayProviderFactory

    adapter = GatewayProviderFactory.create_adapter(
        provider_id=str(prov).strip().lower(),
        base_url=(api_base_url or "").strip(),
        api_key=(api_key or "").strip(),
    )
    gateway.register_provider(adapter)
