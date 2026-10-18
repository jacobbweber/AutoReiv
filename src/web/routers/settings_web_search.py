"""Settings routes for Web Search & Direct URL Fetch configuration [CARD-719]."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.skills.web_tools import (
    SUPPORTED_SEARCH_PROVIDERS,
    WEB_SEARCH_SETTINGS_KEY,
    resolve_web_search_settings,
)
from src.domain.security.vault import Credential

router = APIRouter(tags=["Settings"])

WEB_SEARCH_PROVIDER_CATALOG = [
    {
        "id": "duckduckgo",
        "name": "DuckDuckGo Lite (Free, No API Key)",
        "requires_key": False,
        "description": "Zero-dependency HTML search via DuckDuckGo Lite. Works out of the box with no account.",
    },
    {
        "id": "tavily",
        "name": "Tavily Search API (Requires Key)",
        "requires_key": True,
        "description": "Search API built for AI agents (1,000 free searches/month). Token stored in Credential Vault.",
    },
    {
        "id": "brave",
        "name": "Brave Search API (Requires Key)",
        "requires_key": True,
        "description": "Independent web search index via Brave Search API. Token stored in Credential Vault.",
    },
]


class WebSearchSettingsUpdate(BaseModel):
    provider: str = "duckduckgo"
    credential_id: Optional[str] = None
    api_key: Optional[str] = None
    allow_private_urls: bool = False
    max_results: int = 5


def _build_web_search_response(store: Any) -> dict[str, Any]:
    cfg = resolve_web_search_settings(store)
    provider = cfg["provider"]
    cred_id = cfg["credential_id"]
    cred_obj = None
    if store is not None:
        for candidate in [c for c in (cred_id, f"web-search-{provider}") if c]:
            try:
                found = store.get_credential(candidate)
                if found and getattr(found, "secret", None):
                    cred_obj = found
                    cred_id = found.id
                    break
            except Exception:
                continue
    return {
        "provider": provider,
        "credential_id": cred_id if cred_obj else cfg["credential_id"],
        "credential_name": getattr(cred_obj, "name", None) if cred_obj else None,
        "has_api_key": bool(cred_obj and getattr(cred_obj, "secret", None)),
        "allow_private_urls": cfg["allow_private_urls"],
        "max_results": cfg["max_results"],
        "providers": WEB_SEARCH_PROVIDER_CATALOG,
    }


@router.get("/api/settings/web-search")
async def get_web_search_settings(request: Request):
    store = getattr(request.app.state, "store", None)
    return _build_web_search_response(store)


@router.put("/api/settings/web-search")
async def update_web_search_settings(req: WebSearchSettingsUpdate, request: Request):
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="State store unavailable.")

    provider = str(req.provider or "duckduckgo").strip().lower()
    if provider not in SUPPORTED_SEARCH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider {provider!r}. Choose from: {', '.join(SUPPORTED_SEARCH_PROVIDERS)}.",
        )

    credential_id = str(req.credential_id or "").strip() or None
    inline_key = str(req.api_key or "").strip()
    if inline_key and not inline_key.startswith("••"):
        target_cred_id = credential_id or f"web-search-{provider}"
        store.save_credential(
            Credential(
                id=target_cred_id,
                name=f"Web Search ({provider.title()})",
                type="api_key",
                secret=inline_key,
                description=f"Encrypted API key for {provider.title()} web search provider",
            )
        )
        credential_id = target_cred_id

    try:
        max_results = max(1, min(15, int(req.max_results or 5)))
    except (TypeError, ValueError):
        max_results = 5

    to_save = {
        "provider": provider,
        "credential_id": credential_id,
        "allow_private_urls": bool(req.allow_private_urls),
        "max_results": max_results,
    }
    store.set_setting(WEB_SEARCH_SETTINGS_KEY, to_save)
    return _build_web_search_response(store)
