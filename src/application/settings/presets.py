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
        "recommended_models": ["llama3.2:1b", "llama3.2:3b", "qwen2.5-coder:7b", "deepseek-r1:8b", "mistral:7b"],
    },
    {
        "id": "lmstudio",
        "name": "LM Studio (Local)",
        "default_url": "http://127.0.0.1:1234/v1",
        "requires_key": False,
        "adapter_type": "openai_compatible",
        "description": "Local OpenAI-compatible inference server with GUI model management",
        "recommended_models": [
            "default",
            "qwen2.5-coder-7b-instruct",
            "llama-3.2-3b-instruct",
            "deepseek-r1-distill-qwen-7b",
        ],
    },
    {
        "id": "vllm",
        "name": "vLLM (Self-Hosted)",
        "default_url": "http://127.0.0.1:8000/v1",
        "requires_key": False,
        "adapter_type": "openai_compatible",
        "description": "High-throughput self-hosted GPU inference engine",
        "recommended_models": [
            "default",
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen2.5-Coder-32B-Instruct",
        ],
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "default_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Google Gemini 3.5 Flash, Gemini 3.7 Flash, and Flash-Lite models",
        "recommended_models": [
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest",
            "gemini-3.7-flash",
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "default_url": "https://api.openai.com/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "GPT-4o, GPT-4o-mini, o1, and o3-mini reasoning models",
        "recommended_models": ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1"],
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "default_url": "https://api.anthropic.com/v1",
        "requires_key": True,
        "adapter_type": "anthropic",
        "description": "Claude 3.7 Sonnet, Claude 3.5 Sonnet, and Haiku models",
        "recommended_models": [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "default_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Unified routing across 200+ models with a single API key",
        "recommended_models": [
            "anthropic/claude-3.7-sonnet",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-r1",
        ],
    },
    {
        "id": "groq",
        "name": "Groq Cloud",
        "default_url": "https://api.groq.com/openai/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Ultra-low latency Llama, Mixtral, and DeepSeek LPUs",
        "recommended_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "deepseek-r1-distill-llama-70b",
            "mixtral-8x7b-32768",
        ],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "default_url": "https://api.deepseek.com/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "DeepSeek-V3 and DeepSeek-R1 reasoning models",
        "recommended_models": ["deepseek-chat", "deepseek-reasoner"],
    },
    {
        "id": "together",
        "name": "Together AI",
        "default_url": "https://api.together.xyz/v1",
        "requires_key": True,
        "adapter_type": "openai_compatible",
        "description": "Open-source fine-tunes and high-throughput inference",
        "recommended_models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-R1",
        ],
    },
]


def get_preset_by_id(preset_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a provider preset by identifier."""
    for p in PROVIDER_PRESETS:
        if p["id"] == preset_id:
            return p
    return None
