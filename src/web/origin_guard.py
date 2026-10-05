"""Owner-route Origin / Host guard and CORS allow-list [CARD-602].

The app is unauthenticated. Browsers send ``Origin`` (or ``Referer``) on
cross-site calls; without a check, any page open in Jacob's browser can POST
to owner-only routes. Requests with no Origin (curl, scripts, same-process
tests) stay allowed. Extra origins (phone reverse proxy, etc.) live in the
``allowed_origins`` setting.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SETTING_KEY = "allowed_origins"
MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def parse_extra_origins(raw: Any) -> List[str]:
    """Normalize a settings value to a list of absolute http(s) origins (no trailing slash)."""
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        return []
    out: List[str] = []
    for item in items:
        text = str(item or "").strip().rstrip("/")
        if not text:
            continue
        parsed = urlparse(text)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"origin must be an absolute http(s) URL, got {item!r}")
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in out:
            out.append(origin)
    return out


def origin_from_referer(referer: Optional[str]) -> Optional[str]:
    if not referer:
        return None
    parsed = urlparse(referer.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def self_origins_for_host(host_header: Optional[str]) -> set[str]:
    host = (host_header or "").strip().lower()
    if not host:
        return set()
    return {f"http://{host}", f"https://{host}"}


def is_origin_allowed(
    origin: Optional[str],
    host_header: Optional[str],
    extras: Sequence[str],
) -> bool:
    """True when there is no Origin, or it matches the request Host / configured extras."""
    if not origin:
        return True
    origin = origin.strip().rstrip("/")
    if not origin:
        return True
    allowed = set(self_origins_for_host(host_header))
    allowed.update(extras)
    # TestClient uses base_url http://testserver with Host testserver (no port)
    return origin.lower() in {a.lower() for a in allowed}


def request_origin(request: Request) -> Optional[str]:
    origin = (request.headers.get("origin") or "").strip() or None
    if origin:
        return origin.rstrip("/")
    return origin_from_referer(request.headers.get("referer"))


def extras_from_store(store: Any) -> List[str]:
    if store is None or not hasattr(store, "get_setting"):
        return []
    try:
        return parse_extra_origins(store.get_setting(SETTING_KEY) or [])
    except ValueError:
        return []


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """Reject mutating requests whose Origin/Referer is not this app or an extra."""

    def __init__(self, app, store_getter: Optional[Callable[[], Any]] = None):
        super().__init__(app)
        self._store_getter = store_getter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in MUTATING:
            origin = request_origin(request)
            if origin:
                store = None
                if self._store_getter is not None:
                    try:
                        store = self._store_getter()
                    except Exception:  # noqa: BLE001 - fail closed on extras only
                        store = None
                if store is None:
                    store = getattr(request.app.state, "store", None)
                extras = extras_from_store(store)
                host = request.headers.get("host")
                if not is_origin_allowed(origin, host, extras):
                    return JSONResponse(
                        {"detail": f"Origin not allowed: {origin}"},
                        status_code=403,
                    )
        return await call_next(request)


def cors_allow_origin_regex(extras: Iterable[str] = ()) -> str:
    """Regex for localhost, loopback, and RFC1918 LAN hosts, plus exact extra origins.

    Used by Starlette CORSMiddleware so evil sites fail preflight. Extras are
    escaped and OR'd in; missing extras still match LAN via the host patterns.
    """
    import re

    parts = [
        r"https?://localhost(:\d+)?",
        r"https?://127\.0\.0\.1(:\d+)?",
        r"https?://0\.0\.0\.0(:\d+)?",
        r"https?://testserver(:\d+)?",  # FastAPI TestClient
        r"https?://192\.168(?:\.\d{1,3}){2}(:\d+)?",
        r"https?://10(?:\.\d{1,3}){3}(:\d+)?",
        r"https?://172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}(:\d+)?",
    ]
    for origin in extras:
        parts.append(re.escape(origin.rstrip("/")))
    return r"^(" + "|".join(parts) + r")$"


class SettingsAwareCORSMiddleware(CORSMiddleware):
    """CORSMiddleware whose allow-list also includes ``allowed_origins`` from settings [CARD-602]."""

    def __init__(self, app, store_getter: Optional[Callable[[], Any]] = None, **kwargs):
        super().__init__(app, **kwargs)
        self._store_getter = store_getter

    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        store = None
        if self._store_getter is not None:
            try:
                store = self._store_getter()
            except Exception:  # noqa: BLE001
                store = None
        extras = extras_from_store(store)
        return any(origin.rstrip("/").lower() == e.lower() for e in extras)
