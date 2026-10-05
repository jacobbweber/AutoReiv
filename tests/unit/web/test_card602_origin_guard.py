"""CARD-602: Origin/Host check on state-changing requests; CORS narrowed to the app and extras."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app
from src.web.origin_guard import (
    SETTING_KEY,
    is_origin_allowed,
    origin_from_referer,
    parse_extra_origins,
)


def test_self_host_and_lan_are_allowed():
    assert is_origin_allowed("http://127.0.0.1:8000", "127.0.0.1:8000", [])
    assert is_origin_allowed("http://192.168.1.99:8000", "192.168.1.99:8000", [])
    assert is_origin_allowed("http://localhost:8000", "localhost:8000", [])


def test_evil_origin_is_rejected_even_when_host_matches_app():
    assert not is_origin_allowed("https://evil.example", "127.0.0.1:8000", [])


def test_extra_configured_origin_is_allowed():
    extras = parse_extra_origins(["https://phone.example:8443", " http://tailnet/ "])
    assert is_origin_allowed("https://phone.example:8443", "127.0.0.1:8000", extras)
    assert "http://tailnet" in extras


def test_missing_origin_is_allowed():
    assert is_origin_allowed(None, "127.0.0.1:8000", [])
    assert is_origin_allowed("", "127.0.0.1:8000", [])


def test_referer_origin_is_parsed():
    assert origin_from_referer("http://127.0.0.1:8000/chat") == "http://127.0.0.1:8000"
    assert origin_from_referer("https://evil.example/x?y=1") == "https://evil.example"
    assert origin_from_referer(None) is None
    assert origin_from_referer("not-a-url") is None


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(tmp_path / "wiki"))
    return TestClient(app), store


def test_post_with_evil_origin_is_forbidden(client):
    c, _ = client
    r = c.post(
        "/api/tools/native/nosuch/disable",
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403
    assert "origin" in r.json()["detail"].lower()


def test_post_without_origin_still_runs(client):
    c, _ = client
    # no Origin: curl/scripts stay allowed; route may 404/4xx on the tool itself
    r = c.post("/api/tools/native/nosuch/disable")
    assert r.status_code != 403


def test_post_from_app_origin_is_not_blocked_by_guard(client):
    c, _ = client
    r = c.post(
        "/api/tools/native/nosuch/disable",
        headers={"Origin": "http://testserver", "Host": "testserver"},
    )
    assert r.status_code != 403


def test_evil_referer_alone_is_forbidden(client):
    c, _ = client
    r = c.post(
        "/api/tools/native/nosuch/disable",
        headers={"Referer": "https://evil.example/attack"},
    )
    assert r.status_code == 403


def test_get_is_not_origin_checked(client):
    c, _ = client
    r = c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert r.status_code == 200


def test_extra_origin_setting_allows_phone_proxy(client):
    c, store = client
    store.set_setting(SETTING_KEY, ["https://phone.proxy:8443"])
    r = c.post(
        "/api/tools/native/nosuch/disable",
        headers={"Origin": "https://phone.proxy:8443"},
    )
    assert r.status_code != 403


def test_cors_preflight_rejects_evil_origin(client):
    c, _ = client
    r = c.options(
        "/api/tools/native/nosuch/disable",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Starlette CORSMiddleware returns 400 when origin not allowed
    assert r.status_code in (400, 403)
    assert r.headers.get("access-control-allow-origin") not in ("*", "https://evil.example")


def test_cors_preflight_allows_app_origin(client):
    c, _ = client
    r = c.options(
        "/api/health",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://testserver"


def test_allowed_origins_settings_api(client):
    c, store = client
    r = c.get("/api/settings/allowed-origins")
    assert r.status_code == 200
    assert r.json()["origins"] == []
    r = c.put("/api/settings/allowed-origins", json={"origins": ["https://phone.example", ""]})
    assert r.status_code == 200
    assert r.json()["origins"] == ["https://phone.example"]
    assert store.get_setting(SETTING_KEY) == ["https://phone.example"]
    bad = c.put("/api/settings/allowed-origins", json={"origins": ["not a url"]})
    assert bad.status_code == 400
