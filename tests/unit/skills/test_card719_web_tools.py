"""CARD-719: Web Search & URL Fetch skill, tools, SSRF guard, and Settings API contract."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.kernel.tool_access import READ, tool_access
from src.infrastructure.content import store as content_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


def test_shipped_web_search_skill_and_autoreiv_binding(tmp_path: Path):
    """platform/skills/web-search/SKILL.md binds fetch_url and web_search and is ticked on AutoReiv."""
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    try:
        st = content_store.get_store()
        skill = st.skills.load("web-search")
        assert skill is not None
        assert "fetch_url" in skill.tools
        assert "web_search" in skill.tools

        autoreiv = st.agents.load("autoreiv")
        assert autoreiv is not None
        assert "web-search" in autoreiv.skills

        allowed = resolve_allowed_tools({"id": "autoreiv", "allowed_skill": autoreiv.skills})
        assert "fetch_url" in allowed
        assert "web_search" in allowed

        # Both tools are labeled READ in tool_access for planning phase safety [CARD-674]
        assert tool_access("fetch_url") == READ
        assert tool_access("web_search") == READ
    finally:
        content_store.reset_store()


def test_fetch_url_extracts_html_and_blocks_ssrf_by_default(tmp_path: Path):
    """fetch_url strips scripts/styles, extracts title and readable text, and blocks private/loopback URLs unless enabled."""
    from src.application.skills.web_tools import WebTools

    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    sample_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>AutoReiv Docs - Getting Started</title>
        <script>console.log("secret script");</script>
        <style>body { color: red; }</style>
      </head>
      <body>
        <nav>Navigation Menu</nav>
        <main>
          <h1>Welcome to AutoReiv</h1>
          <p>AutoReiv is a hybrid execution platform. Read the <a href="https://example.com/guide">User Guide</a>.</p>
          <ul>
            <li>Zero extra dependencies</li>
            <li>Vault encrypted tokens</li>
          </ul>
        </main>
        <footer>Footer copyright</footer>
      </body>
    </html>
    """

    def fake_get(url: str, headers: dict, timeout: float):
        resp = MagicMock()
        resp.status_code = 200
        resp.url = url
        resp.headers = {"content-type": "text/html; charset=utf-8"}
        resp.text = sample_html
        return resp

    tools = WebTools(state_store=store, http_get=fake_get)

    # 1. Public HTTPS URL succeeds and extracts clean structured text without script/style noise
    res = tools.fetch_url("https://example.com/docs")
    assert res["success"] is True
    assert res["title"] == "AutoReiv Docs - Getting Started"
    assert "Welcome to AutoReiv" in res["content"]
    assert "Zero extra dependencies" in res["content"]
    assert "User Guide" in res["content"]
    assert "secret script" not in res["content"]
    assert "color: red" not in res["content"]

    # 2. Negative assertion: Loopback / localhost URL is blocked by SSRF guard by default
    blocked = tools.fetch_url("http://127.0.0.1:8000/api/settings")
    assert blocked["success"] is False
    assert "private" in blocked["error"].lower() or "loopback" in blocked["error"].lower()

    # 3. Enabling allow_private_urls in web_search_settings allows LAN/local HTTP URLs
    store.set_setting("web_search_settings", {"provider": "duckduckgo", "allow_private_urls": True})
    allowed_local = tools.fetch_url("http://127.0.0.1:8000/api/health")
    assert allowed_local["success"] is True


def test_web_search_duckduckgo_tavily_and_brave_providers(tmp_path: Path):
    """web_search supports zero-key DuckDuckGo Lite by default and Vault-authenticated Tavily/Brave providers."""
    from src.application.skills.web_tools import WebTools
    from src.domain.security.vault import Credential

    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    ddg_html = """
    <html><body>
      <table>
        <tr>
          <td><a class="result-link" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Fhtml.parser.html">html.parser — Simple HTML and XHTML parser</a></td>
        </tr>
        <tr>
          <td class="result-snippet">This module defines a class HTMLParser which serves as the basis for parsing text files formatted in HTML.</td>
        </tr>
      </table>
    </body></html>
    """

    calls: list[dict] = []

    def fake_request(method: str, url: str, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        resp = MagicMock()
        resp.status_code = 200
        if "duckduckgo.com" in url:
            resp.text = ddg_html
            return resp
        if "api.tavily.com" in url:
            resp.json.return_value = {
                "results": [
                    {
                        "title": "Tavily AI Search",
                        "url": "https://tavily.com/docs",
                        "content": "Search API built for AI agents.",
                    }
                ]
            }
            return resp
        if "api.search.brave.com" in url:
            resp.json.return_value = {
                "web": {
                    "results": [
                        {
                            "title": "Brave Search API",
                            "url": "https://brave.com/search/api/",
                            "description": "Independent search index API.",
                        }
                    ]
                }
            }
            return resp
        raise AssertionError(f"Unexpected URL {url}")

    tools = WebTools(state_store=store, http_request=fake_request)

    # 1. Default zero-key DuckDuckGo Lite search
    ddg_res = tools.web_search("python html.parser", max_results=3)
    assert ddg_res["success"] is True
    assert ddg_res["provider"] == "duckduckgo"
    assert len(ddg_res["results"]) == 1
    assert ddg_res["results"][0]["title"] == "html.parser — Simple HTML and XHTML parser"
    assert ddg_res["results"][0]["url"] == "https://docs.python.org/3/library/html.parser.html"
    assert "HTMLParser" in ddg_res["results"][0]["snippet"]

    # 2. Negative assertion: selecting Tavily without a Vault credential fails with an actionable message
    store.set_setting("web_search_settings", {"provider": "tavily", "credential_id": None})
    missing_key = tools.web_search("ai agents")
    assert missing_key["success"] is False
    assert "Settings -> Connections" in missing_key["error"]

    # 3. Tavily with encrypted Vault credential succeeds
    store.save_credential(
        Credential(id="web-search-tavily", name="Tavily Key", type="api_key", secret="tvly-secret-123")
    )
    store.set_setting("web_search_settings", {"provider": "tavily", "credential_id": "web-search-tavily"})
    tavily_res = tools.web_search("ai agents", max_results=3)
    assert tavily_res["success"] is True
    assert tavily_res["provider"] == "tavily"
    assert tavily_res["results"][0]["url"] == "https://tavily.com/docs"
    assert calls[-1]["json"]["api_key"] == "tvly-secret-123"

    # 4. Brave with encrypted Vault credential succeeds
    store.save_credential(
        Credential(id="web-search-brave", name="Brave Key", type="api_key", secret="bsa-secret-456")
    )
    store.set_setting("web_search_settings", {"provider": "brave", "credential_id": "web-search-brave"})
    brave_res = tools.web_search("brave index", max_results=3)
    assert brave_res["success"] is True
    assert brave_res["provider"] == "brave"
    assert brave_res["results"][0]["url"] == "https://brave.com/search/api/"
    assert calls[-1]["headers"]["X-Subscription-Token"] == "bsa-secret-456"


def test_web_search_settings_api_encrypts_inline_token_in_vault(tmp_path: Path):
    """PUT /api/settings/web-search stores inline API tokens in the Credential Vault and never persists plaintext in settings."""
    from src.web.routers.settings_web_search import router as web_search_router

    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    app = FastAPI()
    app.state.store = store
    app.include_router(web_search_router)
    client = TestClient(app)

    # 1. Default GET returns duckduckgo
    get_res = client.get("/api/settings/web-search")
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["provider"] == "duckduckgo"
    assert body["allow_private_urls"] is False

    # 2. PUT with inline api_key encrypts it into Vault and persists only credential_id in settings
    put_res = client.put(
        "/api/settings/web-search",
        json={
            "provider": "tavily",
            "api_key": "tvly-inline-token-999",
            "allow_private_urls": True,
            "max_results": 5,
        },
    )
    assert put_res.status_code == 200
    saved = put_res.json()
    assert saved["provider"] == "tavily"
    assert saved["credential_id"] == "web-search-tavily"
    assert saved["has_api_key"] is True
    assert saved["allow_private_urls"] is True

    # Negative assertion: raw setting in SQLite does not contain the plaintext token
    raw_setting = store.get_setting("web_search_settings")
    assert "tvly-inline-token-999" not in str(raw_setting)
    vault_cred = store.get_credential("web-search-tavily")
    assert vault_cred is not None
    assert vault_cred.secret == "tvly-inline-token-999"
