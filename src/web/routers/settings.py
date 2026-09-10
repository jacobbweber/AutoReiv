"""
Settings, LLM Providers, Model Discovery & Hardware Calculator Router [REQ-WEB-004, REQ-SET-001, REQ-SET-006, REQ-MCP-006].
"""

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
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
from src.infrastructure.data.backup import DataDirBackupService, DataDirRestoreError
from src.infrastructure.mcp.client_adapter import MCPClientAdapter

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
    default_provider_id: Optional[str] = "ollama"


class HardwareFitQueryRequest(BaseModel):
    custom_ram_gb: Optional[float] = None
    custom_vram_gb: Optional[float] = None


router = APIRouter(tags=["Settings"])


@router.get("/api/data-dir")
async def get_data_dir(request: Request):
    """Resolved user data directory paths [REQ-DATA-001, REQ-DATA-002]."""
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        return {"root": "", "db_path": "", "wiki_path": "", "skills_path": ""}
    return {
        "root": str(paths.root),
        "db_path": str(paths.db_path),
        "wiki_path": str(paths.wiki_path),
        "skills_path": str(paths.skills_path),
    }


def _data_dir_paths(request: Request):
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="Data directory is not resolved")
    return paths


@router.post("/api/data-dir/backup")
async def backup_data_dir(request: Request):
    """Zip the resolved data dir and return it as a download [REQ-DATA-007]."""
    paths = _data_dir_paths(request)
    dest = DataDirBackupService(paths).backup()
    return FileResponse(
        path=str(dest),
        media_type="application/zip",
        filename=dest.name,
        headers={"X-Backup-Path": str(dest)},
    )


@router.post("/api/data-dir/restore")
async def restore_data_dir(
    request: Request,
    archive: UploadFile = File(...),
    confirm: bool = Form(False),
):
    """Replace the data dir from a zip. Requires confirm=true [REQ-DATA-008]."""
    paths = _data_dir_paths(request)
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Restore requires confirm=true; live tree unchanged",
        )
    suffix = Path(archive.filename or "restore.zip").suffix or ".zip"
    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "wb") as handle:
            while True:
                chunk = await archive.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        DataDirBackupService(paths).restore(tmp_path, confirm=True)
    except DataDirRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    return {"status": "restored", "root": str(paths.root)}



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
    overrides = store.list_agent_overrides()
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

    return {
        "matrix": matrix.model_dump(),
        "hardware": hw.model_dump(),
        "providers": resp_providers,
        "customizations": [c.model_dump() for c in overrides],
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
    prov_map[pid] = {
        "base_url": target_base_url,
        "default_model_id": saved_model,
        "has_key": has_key,
        "key_masked": "••••••••" if has_key else "",
        "vault_cred_id": target_vault_cred_id if has_key else None,
    }
    existing_cfg["providers"] = prov_map

    if req.default_provider_id or req.set_as_default:
        chosen_default = req.default_provider_id or pid
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
        gateway.register_provider(OllamaProviderAdapter(base_url=target_base_url, timeout=180.0, provider_id="ollama"))
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

    raw_slots = data.get("max_concurrent_generations", 1)
    try:
        slots = int(raw_slots)
    except (TypeError, ValueError):
        slots = 1
    if slots < 1 or slots > 3:
        slots = 1

    matrix = ModelPurposeMatrix(
        default_model=data.get("default_model", "default") or "default",
        default_context_window=default_ctx,
        purposes=purposes,
        model_context_windows=model_windows,
        max_concurrent_generations=slots,
    )
    settings_service.save_purpose_matrix(matrix)
    return {"status": "updated", "matrix": matrix.model_dump()}


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
    clean_key = (api_key or "").strip()
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


@router.get("/api/settings/mcp")
@router.get("/api/mcp/servers")
async def list_mcp_servers(request: Request):
    """List configured MCP servers with active mounted status [REQ-MCP-005]."""
    store = request.app.state.store
    servers = store.get_setting("mcp_servers")
    server_list = servers if isinstance(servers, list) else []

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    active_map = mcp_manager.get_mounted_servers() if mcp_manager else {}

    result = []
    for s in server_list:
        name = s.get("name")
        active_info = active_map.get(name)
        result.append(
            {
                **s,
                "is_mounted": active_info is not None,
                "tool_count": active_info.get("tool_count", 0) if active_info else 0,
                "tools": active_info.get("tools", []) if active_info else [],
            }
        )
    return result


@router.post("/api/settings/mcp")
@router.post("/api/mcp/servers")
async def save_mcp_server(request: Request, req: MCPServerConfig):
    """Save and mount an MCP server configuration [REQ-MCP-005]."""
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

    mounted_tools = []
    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    if mcp_manager and req.enabled:
        try:
            tools = await mcp_manager.mount_server(
                name=req.name,
                command=req.command,
                env=req.env,
            )
            mounted_tools = [t.name for t in tools]
        except Exception as e:
            return {
                "status": "saved",
                "name": req.name,
                "mounted": False,
                "error": f"Configuration saved, but tool mounting failed: {e}",
            }

    return {
        "status": "saved",
        "name": req.name,
        "mounted": True,
        "tools_count": len(mounted_tools),
        "tools": mounted_tools,
    }


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
    start_time = time.perf_counter()
    adapter = MCPClientAdapter(
        server_name=req.name or "test-server",
        command=req.command,
        env=req.env,
        timeout_seconds=10.0,
    )
    try:
        tools = await adapter.list_tools()
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
