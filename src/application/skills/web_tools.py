"""Built-in Web Search and Direct URL Fetch tools [CARD-719].

Zero extra dependencies: uses ``httpx`` and Python's standard ``html.parser`` to:
1. ``fetch_url(url, max_chars=12000)``: Scrape and extract clean readable text/Markdown directly from any link.
2. ``web_search(query, max_results=5)``: Search the web via DuckDuckGo Lite (free, zero API key default),
   Tavily Search API, or Brave Search API (with API keys encrypted in the Credential Vault).
"""

from __future__ import annotations

import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx

from src.application.kernel.tool_registry import ScopedToolRegistry

WEB_SEARCH_SETTINGS_KEY = "web_search_settings"
SUPPORTED_SEARCH_PROVIDERS = ("duckduckgo", "tavily", "brave")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AutoReiv/1.3"
)

_IGNORED_TAGS = frozenset({"script", "style", "noscript", "svg", "template", "nav", "footer", "iframe"})
_BLOCK_TAGS = frozenset({"p", "div", "section", "article", "main", "header", "aside", "blockquote", "pre", "tr", "br", "hr"})
_HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}


class _HTMLTextExtractor(HTMLParser):
    """Lightweight stdlib HTML-to-Markdown/text extractor."""

    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self._in_title = False
        self._ignore_depth = 0
        self._chunks: list[str] = []
        self._current_link_href: Optional[str] = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        t = tag.lower()
        if t in _IGNORED_TAGS:
            self._ignore_depth += 1
            return
        if self._ignore_depth > 0:
            return
        if t == "title":
            self._in_title = True
            return
        if t in _HEADING_TAGS:
            self._chunks.append(f"\n\n{_HEADING_TAGS[t]} ")
        elif t == "li":
            self._chunks.append("\n- ")
        elif t in _BLOCK_TAGS:
            self._chunks.append("\n")
        elif t == "a":
            attr_map = dict(attrs)
            href = (attr_map.get("href") or "").strip()
            if href and not href.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
                if self.base_url:
                    href = urljoin(self.base_url, href)
                self._current_link_href = href
                self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _IGNORED_TAGS:
            if self._ignore_depth > 0:
                self._ignore_depth -= 1
            return
        if self._ignore_depth > 0:
            return
        if t == "title":
            self._in_title = False
            return
        if t == "a" and self._current_link_href is not None:
            label = " ".join("".join(self._current_link_text).split()).strip()
            href = self._current_link_href
            self._current_link_href = None
            self._current_link_text = []
            if label:
                self._chunks.append(f" [{label}]({href}) ")
            return
        if t in _HEADING_TAGS or t in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignore_depth > 0:
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        cleaned = re.sub(r"[ \t\r\f\v]+", " ", data)
        if not cleaned.strip():
            return
        if self._current_link_href is not None:
            self._current_link_text.append(cleaned)
        else:
            self._chunks.append(cleaned)

    def get_extracted(self) -> tuple[str, str]:
        title = " ".join("".join(self.title_parts).split()).strip()
        raw = "".join(self._chunks)
        lines = [line.strip() for line in raw.splitlines()]
        collapsed: list[str] = []
        blank_Streak = 0
        for line in lines:
            if not line:
                blank_Streak += 1
                if blank_Streak <= 1 and collapsed:
                    collapsed.append("")
            else:
                blank_Streak = 0
                collapsed.append(line)
        return title, "\n".join(collapsed).strip()


def extract_html_text(html_content: str, base_url: str = "") -> tuple[str, str]:
    """Return ``(title, clean_text)`` from raw HTML."""
    parser = _HTMLTextExtractor(base_url=base_url)
    parser.feed(html_content or "")
    parser.close()
    return parser.get_extracted()


class _DuckDuckGoHTMLParser(HTMLParser):
    """Parse search results from DuckDuckGo Lite / HTML endpoints."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._in_link = False
        self._link_href = ""
        self._link_text: list[str] = []
        self._in_snippet = False
        self._snippet_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        t = tag.lower()
        attr_map = dict(attrs)
        cls = (attr_map.get("class") or "").lower()
        if t == "a" and ("result-link" in cls or "result__a" in cls):
            href = (attr_map.get("href") or "").strip()
            if href:
                self._in_link = True
                self._link_href = _unwrap_ddg_url(href)
                self._link_text = []
        elif t in ("td", "a", "div", "span") and ("result-snippet" in cls or "result__snippet" in cls):
            self._in_snippet = True
            self._snippet_text = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "a" and self._in_link:
            self._in_link = False
            title = " ".join("".join(self._link_text).split()).strip()
            if title and self._link_href and not self._link_href.startswith("https://duckduckgo.com/y.js"):
                self.results.append({"title": title, "url": self._link_href, "snippet": ""})
        elif self._in_snippet and t in ("td", "a", "div", "span"):
            self._in_snippet = False
            snippet = " ".join("".join(self._snippet_text).split()).strip()
            if snippet and self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._link_text.append(data)
        elif self._in_snippet:
            self._snippet_text.append(data)


def _unwrap_ddg_url(href: str) -> str:
    """Unwrap DuckDuckGo ``//duckduckgo.com/l/?uddg=<encoded_url>`` redirect links."""
    clean = href.strip()
    if clean.startswith("//"):
        clean = "https:" + clean
    parsed = urlparse(clean)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg")
        if uddg and uddg[0]:
            return unquote(uddg[0])
    return clean


def _is_Restricted_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified)


def validate_fetch_url(url: str, allow_private_urls: bool = False) -> Optional[str]:
    """Return an error string if ``url`` is invalid or blocked by SSRF policy, else None."""
    raw = str(url or "").strip()
    if not raw:
        return "URL is required."
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return f"Unsupported URL scheme {parsed.scheme!r}: only http:// and https:// URLs are allowed."
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return "URL is missing a hostname."
    if allow_private_urls:
        return None
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local") or host.endswith(".internal"):
        return (
            f"Blocked loopback/local hostname {host!r}. Enable 'Allow private/LAN URLs' in "
            "Settings -> Connections -> Web Search & Fetch to read local/homelab pages."
        )
    if _is_Restricted_ip(host):
        return (
            f"Blocked private or loopback IP {host!r}. Enable 'Allow private/LAN URLs' in "
            "Settings -> Connections -> Web Search & Fetch to read local/homelab pages."
        )
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for info in infos:
            sockaddr = info[4]
            if sockaddr and _is_Restricted_ip(str(sockaddr[0])):
                return (
                    f"Blocked hostname {host!r} resolving to private/loopback IP {sockaddr[0]!r}. "
                    "Enable 'Allow private/LAN URLs' in Settings -> Connections -> Web Search & Fetch "
                    "to read local/homelab pages."
                )
    except socket.gaierror:
        # DNS resolution failure will be handled at HTTP request time
        pass
    return None


def resolve_web_search_settings(store: Any) -> dict[str, Any]:
    """Load normalized ``web_search_settings`` from ``store``."""
    raw = (store.get_setting(WEB_SEARCH_SETTINGS_KEY) if store is not None else None) or {}
    if not isinstance(raw, dict):
        raw = {}
    provider = str(raw.get("provider") or "duckduckgo").strip().lower()
    if provider not in SUPPORTED_SEARCH_PROVIDERS:
        provider = "duckduckgo"
    credential_id = str(raw.get("credential_id") or "").strip() or None
    allow_private_urls = bool(raw.get("allow_private_urls", False))
    try:
        max_results = max(1, min(15, int(raw.get("max_results") or 5)))
    except (TypeError, ValueError):
        max_results = 5
    return {
        "provider": provider,
        "credential_id": credential_id,
        "allow_private_urls": allow_private_urls,
        "max_results": max_results,
    }


class WebTools:
    """Platform tools for reading web pages directly (``fetch_url``) and searching the web (``web_search``)."""

    def __init__(
        self,
        state_store: Any = None,
        http_get: Optional[Callable[..., Any]] = None,
        http_request: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._store = state_store
        self._http_get = http_get
        self._http_request = http_request

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        if self._http_request is not None:
            return self._http_request(method, url, **kwargs)
        timeout = float(kwargs.pop("timeout", 15.0))
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            return client.request(method, url, **kwargs)

    def _get(self, url: str, headers: dict[str, str], timeout: float = 15.0) -> Any:
        if self._http_get is not None:
            return self._http_get(url, headers=headers, timeout=timeout)
        return self._request("GET", url, headers=headers, timeout=timeout)

    def _resolve_api_key(self, provider: str, credential_id: Optional[str]) -> Optional[str]:
        if self._store is None:
            return None
        candidates = [c for c in (credential_id, f"web-search-{provider}") if c]
        for cid in candidates:
            try:
                cred = self._store.get_credential(cid)
                if cred and getattr(cred, "secret", None):
                    return str(cred.secret).strip()
            except Exception:
                continue
        return None

    def fetch_url(self, url: str, max_chars: int = 12000) -> Dict[str, Any]:
        """Fetch a web page directly by URL and extract clean readable text/Markdown."""
        cfg = resolve_web_search_settings(self._store)
        err = validate_fetch_url(url, allow_private_urls=cfg["allow_private_urls"])
        if err:
            return {"success": False, "url": url, "error": err}

        try:
            cap = max(500, min(50000, int(max_chars or 12000)))
        except (TypeError, ValueError):
            cap = 12000

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json,text/plain,text/markdown;q=0.9,*/*;q=0.8",
        }
        try:
            resp = self._get(url.strip(), headers=headers, timeout=15.0)
        except Exception as exc:
            return {"success": False, "url": url, "error": f"HTTP fetch failed: {exc}"}

        status_code = int(getattr(resp, "status_code", 200) or 200)
        final_url = str(getattr(resp, "url", url) or url)
        if status_code >= 400:
            return {
                "success": False,
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "error": f"HTTP {status_code} returned for {final_url}",
            }

        resp_headers = getattr(resp, "headers", {}) or {}
        content_type = str(resp_headers.get("content-type") or resp_headers.get("Content-Type") or "").lower()
        raw_text = str(getattr(resp, "text", "") or "")

        if "html" in content_type or raw_text.lstrip().lower().startswith(("<!doctype html", "<html")):
            title, body_text = extract_html_text(raw_text, base_url=final_url)
        else:
            title = ""
            body_text = raw_text.strip()

        truncated = len(body_text) > cap
        if truncated:
            body_text = body_text[:cap].rstrip() + "\n...[truncated]"

        return {
            "success": True,
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "title": title,
            "content": body_text,
            "truncated": truncated,
        }

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web using the provider configured in Settings -> Connections."""
        clean_query = str(query or "").strip()
        if not clean_query:
            return {"success": False, "error": "Search query cannot be empty."}

        cfg = resolve_web_search_settings(self._store)
        provider = cfg["provider"]
        try:
            limit = max(1, min(15, int(max_results or cfg["max_results"] or 5)))
        except (TypeError, ValueError):
            limit = cfg["max_results"]

        if provider == "duckduckgo":
            return self._search_duckduckgo(clean_query, limit)

        api_key = self._resolve_api_key(provider, cfg.get("credential_id"))
        if not api_key:
            return {
                "success": False,
                "provider": provider,
                "query": clean_query,
                "error": (
                    f"Web search provider '{provider}' requires an API key. "
                    "Add an API token or switch to 'DuckDuckGo Lite (Free)' in "
                    "Settings -> Connections -> Web Search & Fetch."
                ),
            }

        if provider == "tavily":
            return self._search_tavily(clean_query, limit, api_key)
        if provider == "brave":
            return self._search_brave(clean_query, limit, api_key)
        return {"success": False, "error": f"Unsupported search provider: {provider}"}

    def _search_duckduckgo(self, query: str, max_results: int) -> Dict[str, Any]:
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            resp = self._request(
                "POST",
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers=headers,
                timeout=15.0,
            )
            status = int(getattr(resp, "status_code", 200) or 200)
            if status >= 400:
                return {"success": False, "provider": "duckduckgo", "query": query, "error": f"DuckDuckGo returned HTTP {status}"}
            parser = _DuckDuckGoHTMLParser()
            parser.feed(str(getattr(resp, "text", "") or ""))
            parser.close()
            results = parser.results[:max_results]
            return {
                "success": True,
                "provider": "duckduckgo",
                "query": query,
                "count": len(results),
                "results": results,
            }
        except Exception as exc:
            return {"success": False, "provider": "duckduckgo", "query": query, "error": f"DuckDuckGo search failed: {exc}"}

    def _search_tavily(self, query: str, max_results: int, api_key: str) -> Dict[str, Any]:
        try:
            resp = self._request(
                "POST",
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": max_results},
                headers={"Content-Type": "application/json", "User-Agent": DEFAULT_USER_AGENT},
                timeout=15.0,
            )
            status = int(getattr(resp, "status_code", 200) or 200)
            if status >= 400:
                return {"success": False, "provider": "tavily", "query": query, "error": f"Tavily API returned HTTP {status}"}
            payload = resp.json() if callable(getattr(resp, "json", None)) else {}
            raw_results = payload.get("results") or []
            results = [
                {
                    "title": str(item.get("title") or "").strip(),
                    "url": str(item.get("url") or "").strip(),
                    "snippet": str(item.get("content") or item.get("snippet") or "").strip(),
                }
                for item in raw_results[:max_results]
                if isinstance(item, dict) and item.get("url")
            ]
            return {
                "success": True,
                "provider": "tavily",
                "query": query,
                "count": len(results),
                "results": results,
            }
        except Exception as exc:
            return {"success": False, "provider": "tavily", "query": query, "error": f"Tavily search failed: {exc}"}

    def _search_brave(self, query: str, max_results: int, api_key: str) -> Dict[str, Any]:
        try:
            resp = self._request(
                "GET",
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                    "User-Agent": DEFAULT_USER_AGENT,
                },
                timeout=15.0,
            )
            status = int(getattr(resp, "status_code", 200) or 200)
            if status >= 400:
                return {"success": False, "provider": "brave", "query": query, "error": f"Brave Search API returned HTTP {status}"}
            payload = resp.json() if callable(getattr(resp, "json", None)) else {}
            web_block = payload.get("web") if isinstance(payload, dict) else {}
            raw_results = (web_block.get("results") if isinstance(web_block, dict) else None) or []
            results = [
                {
                    "title": str(item.get("title") or "").strip(),
                    "url": str(item.get("url") or "").strip(),
                    "snippet": str(item.get("description") or item.get("snippet") or "").strip(),
                }
                for item in raw_results[:max_results]
                if isinstance(item, dict) and item.get("url")
            ]
            return {
                "success": True,
                "provider": "brave",
                "query": query,
                "count": len(results),
                "results": results,
            }
        except Exception as exc:
            return {"success": False, "provider": "brave", "query": query, "error": f"Brave search failed: {exc}"}

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="fetch_url",
            description=(
                "Fetch a web page directly from an http:// or https:// URL and return its title and clean "
                "readable text/Markdown. Use this whenever you already have a link."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full http:// or https:// URL to fetch and read.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters of page text to return (default 12000).",
                        "default": 12000,
                    },
                },
                "required": ["url"],
            },
            handler=self.fetch_url,
            risk="read_only",
        )
        registry.register_tool(
            name="web_search",
            description=(
                "Search the web for documentation, current facts, or URLs using the configured search provider "
                "(DuckDuckGo Lite free default, Tavily, or Brave Search)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Focused web search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-15, default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            handler=self.web_search,
            risk="read_only",
        )
