"""Optional voice sidecar settings + proxy routes."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.routers.settings_voice import router


class _Store:
    def __init__(self):
        self.d = {}

    def get_setting(self, k, default=None):
        return self.d.get(k, default)

    def set_setting(self, k, v):
        self.d[k] = v


def _client():
    app = FastAPI()
    app.state.store = _Store()
    app.include_router(router)
    return TestClient(app)


def test_voice_off_by_default_and_proxies_disabled():
    c = _client()
    assert c.get("/api/settings/voice").json()["enabled"] is False
    assert c.get("/api/voice/status").json() == {"enabled": False, "auto_speak": True, "reachable": False}
    r = c.post("/api/voice/speak", json={"text": "hi"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "voice_disabled"
    assert c.post("/api/voice/transcribe", content=b"x").status_code == 404


def test_enabled_requires_url_and_validates():
    c = _client()
    assert c.put("/api/settings/voice", json={"enabled": True}).json()["enabled"] is False
    assert c.put("/api/settings/voice", json={"enabled": True, "endpoint_url": "ftp://x"}).status_code == 400
    r = c.put("/api/settings/voice", json={"enabled": True, "endpoint_url": "http://127.0.0.1:9/"})
    assert r.json() == {"enabled": True, "endpoint_url": "http://127.0.0.1:9", "voice": "", "auto_speak": True}
    s = c.get("/api/voice/status").json()
    assert s["enabled"] is True and s["reachable"] is False
    assert c.post("/api/voice/speak", json={"text": "hi"}).status_code == 502
