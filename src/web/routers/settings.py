"""
Settings, LLM Providers, Model Discovery & Hardware Calculator Router [REQ-WEB-004, REQ-SET-001, REQ-SET-006, REQ-MCP-006].
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.application.gateway.ports import LLMProviderPort
from src.domain.settings.models import (
    AgentCustomization,
    HardwareSpecs,
    MCPServerConfig,
    ModelDescriptor,
    ModelPurpose,
    ModelPurposeMatrix,
)

logger = logging.getLogger(__name__)


class ProviderSettingsRequest(BaseModel):
    ollama_host: Optional[str] = "http://127.0.0.1:11434"
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    default_provider_id: Optional[str] = "ollama"
    default_model_id: Optional[str] = "default"


class HardwareFitQueryRequest(BaseModel):
    custom_ram_gb: Optional[float] = None
    custom_vram_gb: Optional[float] = None


router = APIRouter(tags=["Settings"])


@router.get("/api/settings/presets")
async def get_settings_presets():
    from src.application.settings.presets import PROVIDER_PRESETS

    return {"presets": PROVIDER_PRESETS}


@router.get("/api/settings")
async def get_settings(request: Request):
    settings_service = request.app.state.settings_service
    hw_calc = request.app.state.hw_calc
    store = request.app.state.store
    gateway = request.app.state.gateway

    matrix = settings_service.get_purpose_matrix()
    hw = hw_calc.get_hardware_specs()
    overrides = store.list_agent_overrides()
    providers_cfg = store.get_setting("provider_settings") or {
        "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "default_provider_id": getattr(gateway, "default_provider_id", "ollama") or "ollama",
        "default_model_id": getattr(gateway, "default_model_id", "default") or "default",
    }
    return {
        "matrix": matrix.model_dump(),
        "hardware": hw.model_dump(),
        "providers": providers_cfg,
        "customizations": [c.model_dump() for c in overrides],
    }


@router.post("/api/settings/providers")
async def update_provider_settings(request: Request, req: ProviderSettingsRequest):
    store = request.app.state.store
    gateway = request.app.state.gateway

    existing_cfg = store.get_setting("provider_settings") or {}
    merged_cfg = {**existing_cfg, **req.model_dump(exclude_unset=True)}
    store.set_setting("provider_settings", merged_cfg)

    from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
    from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

    if req.ollama_host:
        gateway.register_provider(OllamaProviderAdapter(base_url=req.ollama_host, provider_id="ollama"))

    if (
        req.openai_api_key
        or req.openai_base_url
        or (req.default_provider_id and req.default_provider_id != "ollama")
    ):
        pid = (
            req.default_provider_id
            if (req.default_provider_id and req.default_provider_id != "ollama")
            else "openai"
        )
        gateway.register_provider(
            OpenAIProviderAdapter(
                api_key=req.openai_api_key or "",
                base_url=req.openai_base_url or "https://api.openai.com/v1",
                provider_id=pid,
            )
        )

    if req.default_provider_id:
        gateway.default_provider_id = req.default_provider_id

    if req.default_model_id:
        gateway.default_model_id = req.default_model_id

    return {"status": "saved", "providers": merged_cfg}


@router.post("/api/settings/matrix")
async def update_purpose_matrix(request: Request, data: Dict[str, Any]):
    settings_service = request.app.state.settings_service

    if "purposes" in data and isinstance(data["purposes"], dict):
        raw_purposes = data["purposes"]
    else:
        raw_purposes = {k: v for k, v in data.items() if k != "default_model" and v is not None}

    purposes: Dict[ModelPurpose, str] = {}
    for k, v in raw_purposes.items():
        if v is not None:
            try:
                purposes[ModelPurpose(k)] = str(v)
            except ValueError:
                continue

    matrix = ModelPurposeMatrix(
        default_model=data.get("default_model", "default") or "default",
        purposes=purposes,
    )
    settings_service.save_purpose_matrix(matrix)
    return {"status": "updated", "matrix": matrix.model_dump()}


@router.get("/api/models/discover")
async def discover_models(
    request: Request,
    provider_id: Optional[str] = None,
    host_url: Optional[str] = None,
    api_key: Optional[str] = None,
    available_ram_gib: Optional[float] = None,
):
    from src.application.settings.presets import get_preset_by_id
    from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
    from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

    gateway = request.app.state.gateway
    hw_calc = request.app.state.hw_calc
    pid = provider_id or getattr(gateway, "default_provider_id", "ollama") or "ollama"

    if host_url:
        clean_host = host_url.strip()
        adapter: LLMProviderPort
        if pid == "ollama" or ":11434" in clean_host:
            adapter = OllamaProviderAdapter(base_url=clean_host, provider_id=pid)
        else:
            adapter = OpenAIProviderAdapter(base_url=clean_host, api_key=api_key or "", provider_id=pid)
        gateway.register_provider(adapter)

    try:
        models = await gateway.list_models(provider_id=pid)
    except Exception as e:
        logger.warning(f"Live model discovery failed for provider '{pid}': {e}. Using curated catalog presets.")
        preset = get_preset_by_id(pid)
        preset_models = preset.get("recommended_models", ["default"]) if preset else ["default"]
        models = [
            ModelDescriptor(
                id=f"{pid}/{m}",
                name=m,
                provider=pid,
                param_size_b=1.0
                if "1" in m
                else 3.0
                if "3" in m
                else 7.0
                if "7" in m
                else 8.0
                if "8" in m
                else None,
                quantization="Q4_K_M" if pid == "ollama" else "cloud",
                family=m.split(":")[0] if ":" in m else m,
            )
            for m in preset_models
        ]

    specs = None
    if available_ram_gib is not None:
        specs = HardwareSpecs(
            total_ram_gb=available_ram_gib,
            available_ram_gb=available_ram_gib,
        )

    discovered = []
    for m in models:
        if m.param_size_b:
            report = hw_calc.evaluate_fit(
                param_size_b=m.param_size_b,
                quantization=m.quantization or "Q4_K_M",
                specs=specs,
                model_id=m.id,
            )
            fit_status = report.fit_status.value
            est_ram = report.required_ram_gb
            notes = report.notes
        else:
            fit_status = "cloud" if m.provider != "ollama" else "runnable"
            est_ram = 0.0
            notes = "Cloud hosted model" if m.provider != "ollama" else "Local model"

        discovered.append(
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "param_size_b": m.param_size_b,
                "quantization": m.quantization,
                "family": m.family,
                "estimated_ram_gb": est_ram,
                "fit_status": fit_status,
                "notes": notes,
            }
        )

    return {"models": discovered}


@router.post("/api/settings/models/refresh")
async def refresh_models(request: Request, req: Optional[HardwareFitQueryRequest] = None):
    settings_service = request.app.state.settings_service
    hw = None
    if req and (req.custom_ram_gb or req.custom_vram_gb):
        ram = req.custom_ram_gb or 16.0
        hw = HardwareSpecs(
            total_ram_gb=ram,
            available_ram_gb=ram * 0.8,
            vram_gb=req.custom_vram_gb or 0.0,
            is_unified_memory=(req.custom_ram_gb is not None and req.custom_ram_gb >= 64.0),
        )
    reports = await settings_service.get_model_recommendations(specs_override=hw)
    return [r.model_dump() for r in reports]


@router.post("/api/settings/agents/{agent_id}")
async def customize_agent(request: Request, agent_id: str, custom: AgentCustomization):
    store = request.app.state.store
    custom.agent_id = agent_id
    store.save_agent_override(custom)
    return {"status": "saved", "customization": custom.model_dump()}


@router.get("/api/mcp/servers")
async def list_mcp_servers(request: Request):
    store = request.app.state.store
    servers = store.get_setting("mcp_servers")
    return servers if isinstance(servers, list) else []


@router.post("/api/mcp/servers")
async def save_mcp_server(request: Request, req: MCPServerConfig):
    store = request.app.state.store
    servers = store.get_setting("mcp_servers")
    if not isinstance(servers, list):
        servers = []
    existing_idx = next((i for i, s in enumerate(servers) if s.get("name") == req.name), None)
    server_dict = req.model_dump()
    if existing_idx is not None:
        servers[existing_idx] = server_dict
    else:
        servers.append(server_dict)
    store.set_setting("mcp_servers", servers)
    return {"status": "saved", "name": req.name}
