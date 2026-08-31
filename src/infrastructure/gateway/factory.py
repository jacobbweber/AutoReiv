"""
Gateway Provider Factory [REQ-GW-002].
Constructs configured adapters and registers them with MultiProviderGateway.
"""

import os
from typing import Any, Dict, Optional

from src.application.gateway.gateway_service import MultiProviderGateway
from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


class GatewayProviderFactory:
    """Factory creating configured MultiProviderGateway instances."""

    @classmethod
    def create_gateway(
        cls,
        config: Optional[Dict[str, Any]] = None,
    ) -> MultiProviderGateway:
        """
        Create a MultiProviderGateway populated with provider adapters.
        Reads from config dictionary if provided, otherwise os.environ.
        """
        cfg = config if config is not None else os.environ

        timeout_sec = float(cfg.get("GATEWAY_DEFAULT_TIMEOUT_SECONDS", 180.0))
        gateway = MultiProviderGateway()

        # 1. Ollama Local Provider (default enabled)
        ollama_host = cfg.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        ollama_adapter = OllamaProviderAdapter(base_url=ollama_host, timeout=timeout_sec, provider_id="ollama")
        gateway.register_provider(ollama_adapter)

        # 2. LM Studio Local Provider
        lmstudio_host = cfg.get("LMSTUDIO_HOST") or cfg.get("LMSTUDIO_BASE_URL")
        if lmstudio_host:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=cfg.get("LMSTUDIO_API_KEY", ""),
                    base_url=lmstudio_host,
                    timeout=timeout_sec,
                    provider_id="lmstudio",
                )
            )

        # 3. vLLM Self-Hosted Provider
        vllm_host = cfg.get("VLLM_HOST") or cfg.get("VLLM_BASE_URL")
        if vllm_host:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=cfg.get("VLLM_API_KEY", ""),
                    base_url=vllm_host,
                    timeout=timeout_sec,
                    provider_id="vllm",
                )
            )

        # 4. Google Gemini
        gemini_key = cfg.get("GEMINI_API_KEY")
        gemini_base = cfg.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        if gemini_key or "GEMINI_BASE_URL" in cfg:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=gemini_key or "",
                    base_url=gemini_base,
                    timeout=timeout_sec,
                    provider_id="gemini",
                )
            )

        # 5. OpenAI
        openai_key = cfg.get("OPENAI_API_KEY")
        openai_base = cfg.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if openai_key or "OPENAI_BASE_URL" in cfg:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=openai_key or "",
                    base_url=openai_base,
                    timeout=timeout_sec,
                    provider_id="openai",
                )
            )

        # 6. Anthropic Claude
        anthropic_key = cfg.get("ANTHROPIC_API_KEY")
        anthropic_base = cfg.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        if anthropic_key or "ANTHROPIC_BASE_URL" in cfg:
            gateway.register_provider(
                AnthropicProviderAdapter(
                    api_key=anthropic_key or "",
                    base_url=anthropic_base,
                    timeout=timeout_sec,
                    provider_id="anthropic",
                )
            )

        # 7. OpenRouter
        openrouter_key = cfg.get("OPENROUTER_API_KEY")
        if openrouter_key:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=openrouter_key,
                    base_url=cfg.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    timeout=timeout_sec,
                    provider_id="openrouter",
                )
            )

        # 8. Groq Cloud
        groq_key = cfg.get("GROQ_API_KEY")
        if groq_key:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=groq_key,
                    base_url=cfg.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                    timeout=timeout_sec,
                    provider_id="groq",
                )
            )

        # 9. DeepSeek
        deepseek_key = cfg.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=deepseek_key,
                    base_url=cfg.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                    timeout=timeout_sec,
                    provider_id="deepseek",
                )
            )

        # 10. Together AI
        together_key = cfg.get("TOGETHER_API_KEY")
        if together_key:
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=together_key,
                    base_url=cfg.get("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
                    timeout=timeout_sec,
                    provider_id="together",
                )
            )

        # 11. Active / Default provider from stored settings (e.g. Gemini, LM Studio, Anthropic)
        active_pid = cfg.get("default_provider_id") or cfg.get("DEFAULT_PROVIDER_ID")
        if active_pid:
            gateway.default_provider_id = active_pid
            if active_pid not in gateway._providers:
                from src.application.settings.presets import get_preset_by_id

                preset = get_preset_by_id(active_pid)
                active_key = (
                    cfg.get(f"{active_pid.upper()}_API_KEY")
                    or cfg.get(f"{active_pid}_api_key")
                    or cfg.get("openai_api_key")
                    or cfg.get("OPENAI_API_KEY")
                    or ""
                )
                active_url = (
                    cfg.get(f"{active_pid.upper()}_BASE_URL")
                    or cfg.get(f"{active_pid}_base_url")
                    or cfg.get("openai_base_url")
                    or cfg.get("OPENAI_BASE_URL")
                    or (preset.get("default_url") if preset else None)
                    or "https://api.openai.com/v1"
                )
                if active_pid == "anthropic":
                    gateway.register_provider(
                        AnthropicProviderAdapter(
                            api_key=active_key,
                            base_url=active_url,
                            timeout=timeout_sec,
                            provider_id="anthropic",
                        )
                    )
                elif active_pid == "ollama":
                    gateway.register_provider(
                        OllamaProviderAdapter(
                            base_url=active_url,
                            timeout=timeout_sec,
                            provider_id="ollama",
                        )
                    )
                else:
                    gateway.register_provider(
                        OpenAIProviderAdapter(
                            api_key=active_key,
                            base_url=active_url,
                            timeout=timeout_sec,
                            provider_id=active_pid,
                        )
                    )

        return gateway

    @classmethod
    def from_env(cls) -> MultiProviderGateway:
        """Convenience alias for create_gateway()."""
        return cls.create_gateway()
