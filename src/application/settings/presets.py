"""
Provider Preset Registry [REQ-SET-001].
Standard LLM provider presets with default base URLs and adapter specifications.
"""

from typing import Any, Dict, List, Optional

PROVIDER_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "default_url": "http://127.0.0.1:11434",
        "requires_key": False,
        "adapter_type": "ollama",
        "description": "Local offline models with zero setup",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "default_url": "https://api.openai.com/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "GPT-4o, GPT-4o-mini, and o1 reasoning models",
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "default_url": "https://api.anthropic.com/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Claude 3.5 Sonnet and Haiku via OpenAI proxy / SDK",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "default_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Unified routing across 200+ models with a single API key",
    },
    {
        "id": "groq",
        "name": "Groq Cloud",
        "default_url": "https://api.groq.com/openai/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Ultra-low latency Llama and Mixtral LPUs",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "default_url": "https://api.deepseek.com/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "DeepSeek-V3 and DeepSeek-R1 reasoning models",
    },
    {
        "id": "together",
        "name": "Together AI",
        "default_url": "https://api.together.xyz/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Open-source fine-tunes and high-throughput inference",
    },
    {
        "id": "vllm",
        "name": "vLLM / Local OpenAI Compatible",
        "default_url": "http://127.0.0.1:8000/v1",
        "requires_key": False,
        "adapter_type": "openai_compatible",
        "description": "High-throughput self-hosted vLLM or LM Studio server",
    },
]


def get_preset_by_id(preset_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a provider preset by identifier."""
    for p in PROVIDER_PRESETS:
        if p["id"] == preset_id:
            return p
    return None
