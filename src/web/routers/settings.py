"""
Settings, LLM Providers, Model Discovery & Hardware Calculator Router [REQ-WEB-004, REQ-SET-001, REQ-SET-006, REQ-MCP-006].
"""

import logging
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.gateway.ports import LLMProviderPort
from src.application.safety.approval_mode import resolve_approval_mode, save_approval_mode
from src.domain.settings.models import (
    HardwareSpecs,
    MCPServerConfig,
    ModelDescriptor,
    ModelPurpose,
    ModelPurposeMatrix,
)
from src.infrastructure.mcp.client_adapter import MCPClientAdapter, MCPMountError, adapter_start_error
from src.web.mcp_mount_reconcile import (
    lookup_mcp_credential_name,
    mcp_save_http_body,
    mount_errors,
    reconcile_saved_mcp_server,
    resolve_mcp_server_auth,
)
from src.web.routers.settings_data_backup import _data_dir_paths  # noqa: F401 - re-exported for data_dir_migrate
from src.web.routers.settings_data_backup import router as data_backup_router
from src.web.routers.settings_web_search import router as web_search_router

logger = logging.getLogger(__name__)


class ProviderSettingsRequest(BaseModel):
    # Modern per-provider fields [CARD-211, CARD-212]
    provider_id: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    vault_cred_id: Optional[str] = None
    default_model_id: Optional[str] = "default"
    set_as_default: Optional[bool] = True

    # Legacy fields for backward compatibility
    ollama_host: Optional[str] = "http://127.0.0.1:11434"
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    default_provider_id: Optional[str] = None  # CARD-290: no silent ollama default (was overriding provider_id)


class HardwareFitQueryRequest(BaseModel):
    custom_ram_gb: Optional[float] = None
    custom_vram_gb: Optional[float] = None


router = APIRouter(tags=["Settings"])
router.include_router(data_backup_router)
router.include_router(web_search_router)



@router.get("/api/settings/presets")
async def get_settings_presets():
    from src.application.settings.presets import PROVIDER_PRESETS

    return {"presets": PROVIDER_PRESETS}


@router.get("/api/settings")
async def get_settings(request: Request):
    from src.application.settings.presets import PROVIDER_PRESETS
    from src.domain.security.vault import Credential

    settings_service = request.app.state.settings_service
    hw_calc = request.app.state.hw_calc
    store = request.app.state.store
    gateway = request.app.state.gateway

    matrix = settings_service.get_purpose_matrix()
    hw = hw_calc.get_hardware_specs()
    # CARD-570: per-agent model/provider live in one settings key; the secret api_key is not echoed.
    model_settings = store.get_setting("agent_model_settings") or {}
    customizations = [
        {"agent_id": aid, **{k: v for k, v in vals.items() if k != "api_key"}}
        for aid, vals in (model_settings.items() if isinstance(model_settings, dict) else [])
        if isinstance(vals, dict)
    ]
    providers_cfg = store.get_setting("provider_settings") or {
        "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "default_provider_id": getattr(gateway, "default_provider_id", "ollama") or "ollama",
        "default_model_id": getattr(gateway, "default_model_id", "default") or "default",
    }

    # Ensure per-provider map exists and is populated from Vault [CARD-211]
    prov_map = dict(providers_cfg.get("providers") or {})
    default_pid = (
        providers_cfg.get("default_provider_id")
        or getattr(gateway, "default_provider_id", "ollama")
        or "ollama"
    )

    for preset in PROVIDER_PRESETS:
        pid = preset["id"]
        saved = prov_map.get(pid) or {}

        # Check vault credential
        has_key = False
        target_cred_id = saved.get("vault_cred_id") or f"llm-provider-{pid}"
        vault_cred = store.get_credential(target_cred_id)
        if vault_cred and vault_cred.secret:
            has_key = True
        elif pid == default_pid and providers_cfg.get("openai_api_key"):
            # Auto-migrate legacy key into vault
            legacy_key = str(providers_cfg.get("openai_api_key")).strip()
            if legacy_key and not legacy_key.startswith("••"):
                try:
                    store.save_credential(
                        Credential(
                            id=f"llm-provider-{pid}",
                            name=f"LLM Provider: {preset.get('name', pid)}",
                            type="api_key",
                            secret=legacy_key,
                            description=f"Auto-migrated credential for {pid}",
                        )
                    )
                    has_key = True
                    target_cred_id = f"llm-provider-{pid}"
                except Exception as e:
                    logger.warning(f"Failed to auto-migrate legacy key for {pid}: {e}")

        # Base URL resolution
        base_url = saved.get("base_url")
        if not base_url:
            if pid == "ollama":
                base_url = providers_cfg.get("ollama_host") or preset.get("default_url")
            elif pid == default_pid:
                base_url = providers_cfg.get("openai_base_url") or preset.get("default_url")
            else:
                base_url = preset.get("default_url")

        default_model_id = saved.get("default_model_id")
        if not default_model_id:
            if pid == default_pid:
                default_model_id = providers_cfg.get("default_model_id", "default")
            else:
                default_model_id = "default"

        if pid == "gemini" and default_model_id and ("3.8" in default_model_id or "3.5" in default_model_id or "2.5" in default_model_id):
            default_model_id = "gemini-3.6-flash"

        prov_map[pid] = {
            "base_url": base_url,
            "default_model_id": default_model_id,
            "has_key": has_key,
            "key_masked": "••••••••" if has_key else "",
            "vault_cred_id": target_cred_id if has_key else None,
        }

    providers_cfg["providers"] = prov_map

    resp_providers = dict(providers_cfg)
    active_has_key = prov_map.get(default_pid, {}).get("has_key", False)
    if active_has_key or resp_providers.get("openai_api_key"):
        resp_providers["openai_api_key"] = "••••••••" if active_has_key else ""


    resolved_approval = resolve_approval_mode(store=store)
    matrix.approval_mode = resolved_approval
    return {
        "matrix": matrix.model_dump(),
        "approval_mode": resolved_approval,
        "hardware": hw.model_dump(),
        "providers": resp_providers,
        "customizations": customizations,
    }


@router.post("/api/settings/providers")
async def update_provider_settings(request: Request, req: ProviderSettingsRequest):
    from src.application.settings.presets import get_preset_by_id
    from src.domain.security.vault import Credential
    from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter
    from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
    from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

    store = request.app.state.store
    gateway = request.app.state.gateway

    existing_cfg = store.get_setting("provider_settings") or {}
    prov_map = dict(existing_cfg.get("providers") or {})

    pid = req.provider_id or req.default_provider_id or existing_cfg.get("default_provider_id") or "ollama"

    # Base URL resolution
    target_base_url = None
    if req.base_url and req.base_url.strip():
        target_base_url = req.base_url.strip()
    elif pid == "ollama" and req.ollama_host and req.ollama_host.strip():
        target_base_url = req.ollama_host.strip()
    elif req.openai_base_url and req.openai_base_url.strip():
        target_base_url = req.openai_base_url.strip()
    elif pid in prov_map and prov_map[pid].get("base_url"):
        target_base_url = prov_map[pid]["base_url"]
    else:
        pr = get_preset_by_id(pid)
        target_base_url = pr.get("default_url") if pr else "http://127.0.0.1:11434"

    # Key resolution & Vault persistence [CARD-211, CARD-212]
    incoming_key = req.api_key if req.api_key is not None else req.openai_api_key
    has_key = False
    active_key = ""
    target_vault_cred_id = None

    if req.vault_cred_id and req.vault_cred_id.strip() and req.vault_cred_id.strip() != "direct":
        # Bind to existing Vault credential
        target_vault_cred_id = req.vault_cred_id.strip()
        existing_cred = store.get_credential(target_vault_cred_id)
        if existing_cred and existing_cred.secret:
            has_key = True
            active_key = existing_cred.secret
    elif incoming_key is not None and str(incoming_key).strip() and not str(incoming_key).strip().startswith("••"):
        clean_key = str(incoming_key).strip()
        pr = get_preset_by_id(pid)
        name = pr.get("name", pid) if pr else pid
        target_vault_cred_id = f"llm-provider-{pid}"
        cred = Credential(
            id=target_vault_cred_id,
            name=f"LLM Provider: {name}",
            type="api_key",
            secret=clean_key,
            description=f"Vault credential for {name}",
        )
        store.save_credential(cred)
        has_key = True
        active_key = clean_key
    else:
        if req.vault_cred_id == "direct":
            target_vault_cred_id = f"llm-provider-{pid}"
        else:
            target_vault_cred_id = prov_map.get(pid, {}).get("vault_cred_id") or f"llm-provider-{pid}"
        existing_cred = store.get_credential(target_vault_cred_id)
        if existing_cred and existing_cred.secret:
            has_key = True
            active_key = existing_cred.secret
        elif pid == existing_cfg.get("default_provider_id") and existing_cfg.get("openai_api_key"):
            leg_key = str(existing_cfg.get("openai_api_key")).strip()
            if leg_key and not leg_key.startswith("••"):
                has_key = True
                active_key = leg_key

    saved_model = req.default_model_id or prov_map.get(pid, {}).get("default_model_id") or "default"
    if pid == "gemini" and saved_model and ("3.8" in saved_model or "3.5" in saved_model or "2.5" in saved_model):
        saved_model = "gemini-3.6-flash"
    prov_map[pid] = {
        "base_url": target_base_url,
        "default_model_id": saved_model,
        "has_key": has_key,
        "key_masked": "••••••••" if has_key else "",
        "vault_cred_id": target_vault_cred_id if has_key else None,
    }
    existing_cfg["providers"] = prov_map

    # CARD-290: provider + model stick as one unit when this save is the active default.
    # Never leave default_provider on ollama while model id is vLLM (or any other pid).
    set_default = True if req.set_as_default is None else bool(req.set_as_default)
    explicit_default_prov = "default_provider_id" in req.model_fields_set and bool(req.default_provider_id)
    if explicit_default_prov or set_default:
        # Prefer explicitly sent default_provider_id; otherwise bind to the provider being edited (pid).
        chosen_default = req.default_provider_id if explicit_default_prov else pid
        existing_cfg["default_provider_id"] = chosen_default
        gateway.default_provider_id = chosen_default
        if saved_model:
            existing_cfg["default_model_id"] = saved_model
            gateway.default_model_id = saved_model

    if pid == "ollama":
        existing_cfg["ollama_host"] = target_base_url
    else:
        existing_cfg["openai_base_url"] = target_base_url

    # Mask plaintext key in settings store if moving to vault
    if has_key:
        existing_cfg["openai_api_key"] = ""

    store.set_setting("provider_settings", existing_cfg)

    # Register provider with gateway using decrypted active_key
    if pid == "ollama" or ":11434" in target_base_url:
        gateway.register_provider(OllamaProviderAdapter(base_url=target_base_url, provider_id="ollama"))
    elif pid == "anthropic":
        gateway.register_provider(
            AnthropicProviderAdapter(
                api_key=active_key,
                base_url=target_base_url,
                provider_id="anthropic",
            )
        )
    else:
        gateway.register_provider(
            OpenAIProviderAdapter(
                api_key=active_key,
                base_url=target_base_url,
                provider_id=pid,
            )
        )

    resp_cfg = dict(existing_cfg)
    resp_cfg["openai_api_key"] = "••••••••" if has_key else ""
    return {"status": "saved", "providers": resp_cfg}


@router.post("/api/settings/matrix")
async def update_purpose_matrix(request: Request, data: Dict[str, Any]):
    settings_service = request.app.state.settings_service

    skip_keys = {
        "default_model",
        "default_context_window",
        "model_context_windows",
        "purposes",
        "max_concurrent_generations",
        "approval_mode",
    }
    if "purposes" in data and isinstance(data["purposes"], dict):
        raw_purposes = data["purposes"]
    else:
        raw_purposes = {k: v for k, v in data.items() if k not in skip_keys and v is not None}

    purposes: Dict[ModelPurpose, str] = {}
    for k, v in raw_purposes.items():
        if v is not None:
            try:
                purposes[ModelPurpose(k)] = str(v)
            except ValueError:
                continue

    raw_default_ctx = data.get("default_context_window")
    default_ctx = None
    if raw_default_ctx not in (None, "", 0, "0"):
        try:
            default_ctx = int(raw_default_ctx)
        except (TypeError, ValueError):
            default_ctx = None

    model_windows: Dict[str, int] = {}
    raw_windows = data.get("model_context_windows") or {}
    if isinstance(raw_windows, dict):
        for mk, mv in raw_windows.items():
            try:
                parsed = int(mv)
            except (TypeError, ValueError):
                continue
            if mk and parsed > 0:
                model_windows[str(mk)] = parsed

    if "max_concurrent_generations" not in data or data.get("max_concurrent_generations") is None:
        slots = 1
    else:
        raw_slots = data.get("max_concurrent_generations")
        if isinstance(raw_slots, bool):
            raise HTTPException(
                status_code=400,
                detail="max_concurrent_generations must be an integer between 1 and 3",
            )
        try:
            slots = int(raw_slots)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="max_concurrent_generations must be an integer between 1 and 3",
            ) from None
        if slots < 1 or slots > 3:
            raise HTTPException(
                status_code=400,
                detail="max_concurrent_generations must be an integer between 1 and 3",
            )


    store = getattr(request.app.state, "store", None)
    if "approval_mode" in data and store is not None:
        raw_approval = data.get("approval_mode")
        try:
            saved_info = save_approval_mode(
                store,
                str(raw_approval).strip() if raw_approval not in (None, "") else None,
            )
            resolved_approval = saved_info["mode"]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
    else:
        resolved_approval = resolve_approval_mode(store=store)

    matrix = ModelPurposeMatrix(
        default_model=data.get("default_model", "default") or "default",
        default_context_window=default_ctx,
        purposes=purposes,
        model_context_windows=model_windows,
        max_concurrent_generations=slots,
        approval_mode=resolved_approval,
    )
    settings_service.save_purpose_matrix(matrix)
    return {"status": "updated", "matrix": matrix.model_dump(), "approval_mode": resolved_approval}


@router.get("/api/models/discover")
async def discover_models(
    request: Request,
    provider_id: Optional[str] = None,
    host_url: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    available_ram_gib: Optional[float] = None,
):
    from src.application.settings.presets import get_preset_by_id
    from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter
    from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
    from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

    gateway = request.app.state.gateway
    hw_calc = request.app.state.hw_calc
    pid = provider_id or getattr(gateway, "default_provider_id", "ollama") or "ollama"

    target_url = host_url or base_url
    header_key = None
    if hasattr(request, "headers") and request.headers:
        header_key = request.headers.get("x-provider-api-key") or request.headers.get("X-Provider-Api-Key")
    clean_key = (header_key or api_key or "").strip()
    store = getattr(request.app.state, "store", None)
    if (not clean_key or clean_key.startswith("••")) and store:
        prov_settings = store.get_setting("provider_settings") or {}
        prov_map = prov_settings.get("providers", {})
        target_cred_id = prov_map.get(pid, {}).get("vault_cred_id") or f"llm-provider-{pid}"
        cred = store.get_credential(target_cred_id)
        if cred and cred.secret:
            clean_key = cred.secret

    if target_url:
        clean_host = target_url.strip()
        adapter: LLMProviderPort
        if pid == "ollama" or ":11434" in clean_host:
            adapter = OllamaProviderAdapter(base_url=clean_host, provider_id=pid)
        elif pid == "anthropic":
            adapter = AnthropicProviderAdapter(base_url=clean_host, api_key=clean_key, provider_id=pid)
        else:
            adapter = OpenAIProviderAdapter(base_url=clean_host, api_key=clean_key, provider_id=pid)
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
                param_size_b=1.0 if "1" in m else 3.0 if "3" in m else 7.0 if "7" in m else 8.0 if "8" in m else None,
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

    # CARD-475: remember which models the provider says can view images, then resolve
    # each model (override > provider > name guess > text-only) for the checkbox.
    from src.application.gateway.model_capabilities import (
        METADATA_SETTING,
        OVERRIDES_SETTING,
        ModelCapabilityResolver,
        merge_vision_metadata,
    )

    if store is not None:
        try:
            store.set_setting(METADATA_SETTING, merge_vision_metadata(store.get_setting(METADATA_SETTING), models))
        except Exception as e:
            logger.warning("Could not save model vision metadata: %s", e)
    resolver = ModelCapabilityResolver(settings_getter=store.get_setting if store is not None else None)
    overrides = (store.get_setting(OVERRIDES_SETTING) if store is not None else None) or {}

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
                "can_view_images": resolver.can_view_images(m.id),
                "vision_source": resolver.vision_source(m.id),
                "vision_override": overrides.get(m.id) if isinstance(overrides, dict) else None,
            }
        )

    return {"models": discovered}


class ModelVisionOverride(BaseModel):
    model_id: str
    vision: Optional[bool] = None


@router.post("/api/settings/model-capabilities")
async def set_model_vision_override(request: Request, body: ModelVisionOverride):
    """Per-model "Can view images" checkbox [CARD-475, D2]. ``vision: null`` clears the override."""
    from src.application.gateway.model_capabilities import OVERRIDES_SETTING, ModelCapabilityResolver

    model_id = (body.model_id or "").strip()
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    store = request.app.state.store
    overrides = dict(store.get_setting(OVERRIDES_SETTING) or {})
    if body.vision is None:
        overrides.pop(model_id, None)
    else:
        overrides[model_id] = bool(body.vision)
    store.set_setting(OVERRIDES_SETTING, overrides)
    resolver = ModelCapabilityResolver(settings_getter=store.get_setting)
    return {
        "model_id": model_id,
        "can_view_images": resolver.can_view_images(model_id),
        "vision_source": resolver.vision_source(model_id),
    }


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


@router.post("/api/models/probe-local")
async def probe_local_models(request: Request, body: Optional[Dict[str, Any]] = None):
    """Scan local inference ports (8000, 8006, 11434) and configured local URLs for /v1/models [CARD-703]."""
    from src.application.models.local_probe import activate_discovered_model, probe_local_endpoints

    payload = body or {}
    store = getattr(request.app.state, "store", None)
    gateway = getattr(request.app.state, "gateway", None)

    explicit_activate = payload.get("activate")
    if isinstance(explicit_activate, dict) and explicit_activate.get("model") and explicit_activate.get("base_url"):
        activated = activate_discovered_model(
            store,
            gateway,
            provider_id=str(explicit_activate.get("provider_id") or "vllm"),
            base_url=str(explicit_activate["base_url"]),
            model=str(explicit_activate["model"]),
        )
        return {"status": "activated", "activated": activated}

    raw_ports = payload.get("ports")
    raw_extra = payload.get("extra_urls")
    extra_urls = [str(u) for u in raw_extra if str(u).strip()] if isinstance(raw_extra, list) else None

    result = probe_local_endpoints(store=store, ports=raw_ports, extra_urls=extra_urls)
    activated_info = None
    if bool(payload.get("auto_activate")) and result["models"]:
        first = result["models"][0]
        activated_info = activate_discovered_model(
            store,
            gateway,
            provider_id=first["provider_id"],
            base_url=first["base_url"],
            model=first["model"],
        )
    result["activated"] = activated_info
    return result


# CARD-506: POST /api/settings/agents/{id} removed; Agent Studio saves through PUT /api/agents/{id}.


@router.get("/api/settings/mcp")
@router.get("/api/mcp/servers")
async def list_mcp_servers(request: Request):
    """List configured MCP servers with active mounted status [REQ-MCP-005]."""
    store = request.app.state.store
    servers = store.get_setting("mcp_servers")
    server_list = servers if isinstance(servers, list) else []

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    active_map = mcp_manager.get_mounted_servers() if mcp_manager else {}
    errors = mount_errors(mcp_manager)

    result = []
    for s in server_list:
        name = s.get("name")
        active_info = active_map.get(name)
        result.append(
            {
                **s,
                "credential_name": lookup_mcp_credential_name(s.get("credential_id"), store),
                "is_mounted": active_info is not None,
                "tool_count": active_info.get("tool_count", 0) if active_info else 0,
                "tools": active_info.get("tools", []) if active_info else [],
                "last_error": None if active_info else errors.get(name),  # CARD-516
            }
        )
    return result


@router.post("/api/settings/mcp")
@router.post("/api/mcp/servers")
async def save_mcp_server(request: Request, req: MCPServerConfig):
    """Save an MCP server. Mount when enabled, unmount when disabled [REQ-MCP-005, CARD-424]."""
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

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    data_dir = getattr(request.app.state, "data_dir", None)
    if not data_dir:
        paths = getattr(request.app.state, "data_dir_paths", None)
        if paths is not None and getattr(paths, "root", None):
            data_dir = str(paths.root)
    agent_reg = getattr(request.app.state, "registry", None) or getattr(request.app.state, "agent_reg", None)
    outcome = await reconcile_saved_mcp_server(
        mcp_manager,
        req,
        store=store,
        data_dir=data_dir,
        agent_registry=agent_reg,
        agent_id="autoreiv",
    )
    if outcome["failure"] != "mount" and req.enabled and outcome["tools"]:
        try:
            from src.infrastructure.mcp.companion_author import author_mcp_companion_skill

            author_mcp_companion_skill(
                server_name=req.name,
                tools=outcome["tools"],
                url=req.url,
                data_dir=data_dir,
            )
        except Exception as e:
            return {
                "status": "saved",
                "name": req.name,
                "mounted": False,
                "error": f"Configuration saved, but tool mounting failed: {e}",
            }

    return mcp_save_http_body(
        req.name,
        outcome,
        mount_error="Configuration saved, but tool mounting failed",
    )


@router.delete("/api/settings/mcp/{name}")
@router.delete("/api/mcp/servers/{name}")
async def delete_mcp_server(request: Request, name: str):
    """Unmount and delete an MCP server configuration [REQ-MCP-005]."""
    store = request.app.state.store
    servers = store.get_setting("mcp_servers")
    if isinstance(servers, list):
        servers = [s for s in servers if s.get("name") != name]
        store.set_setting("mcp_servers", servers)

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    if mcp_manager:
        await mcp_manager.unmount_server(name)

    return {"status": "deleted", "name": name}


@router.post("/api/settings/mcp/test")
@router.post("/api/mcp/servers/test")
async def test_mcp_server_connection(request: Request, req: MCPServerConfig):
    """
    Diagnostic probe executing transient stdio handshake and tool discovery without persistence [REQ-MCP-008].
    """
    store = getattr(request.app.state, "store", None)
    resolved_auth = resolve_mcp_server_auth(req, store)
    start_time = time.perf_counter()
    adapter = MCPClientAdapter(
        server_name=req.name or "test-server",
        command=req.command,
        env=resolved_auth["env"],
        transport=req.transport,
        url=req.url,
        headers=resolved_auth["headers"],
        timeout_seconds=10.0,
    )
    try:
        tools = await adapter.list_tools()
        start_error = adapter_start_error(adapter)
        if start_error:
            raise MCPMountError(start_error)  # CARD-516: not "ok, 0 tools"
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "ok",
            "latency_ms": round(latency_ms, 2),
            "tools_count": len(tools),
            "tools": [t.model_dump() for t in tools],
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"MCP probe test failed for '{req.name}': {e}")
        return {
            "status": "error",
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
        }
    finally:
        await adapter.close()


