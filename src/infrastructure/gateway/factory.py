"""
Gateway Provider Factory [REQ-GW-002].
Constructs configured adapters and registers them with MultiProviderGateway.
"""

import os
from typing import Any, Dict, Optional

from src.application.gateway.gateway_service import MultiProviderGateway
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

        timeout_sec = float(cfg.get("GATEWAY_DEFAULT_TIMEOUT_SECONDS", 60.0))
        gateway = MultiProviderGateway()

        # 1. Ollama Local Provider (default enabled)
        ollama_host = cfg.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        ollama_adapter = OllamaProviderAdapter(base_url=ollama_host, timeout=timeout_sec)
        gateway.register_provider(ollama_adapter)

        # 2. OpenAI-Compatible Provider
        openai_key = cfg.get("OPENAI_API_KEY")
        openai_base = cfg.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if openai_key or "OPENAI_BASE_URL" in cfg:
            openai_adapter = OpenAIProviderAdapter(
                api_key=openai_key or "",
                base_url=openai_base,
                timeout=timeout_sec,
            )
            gateway.register_provider(openai_adapter)

        return gateway

    @classmethod
    def from_env(cls) -> MultiProviderGateway:
        """Convenience alias for create_gateway()."""
        return cls.create_gateway()
