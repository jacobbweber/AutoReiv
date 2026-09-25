"""CARD-475 operator contract: an image never breaks a chat session.

A fake Spark-like OpenAI gateway answers like the real one: an image request to
a text-only model gets HTTP 200 text/event-stream with a bare JSON error line.

REQ-475-001/004: image turn on text-only nemotron -> a real reply plus an
attachment_notice, no empty row; the next "Hi" answers.
REQ-475-002: image turn on a vision-marked model -> the image goes out once; the
next turn carries none.
REQ-475-005: a model wrongly marked vision is rejected, retried once without images.
REQ-475-006/007: a session poisoned before the fix (image turn + empty assistant
row) answers "Hi" and the thread view hides the empty row.

Temp user-data only [ADR-0055]. No live Spark, no live AppData.
"""

from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
TEXT_ONLY = "nemotron-3.5-lightning"
VISION = "gemma-4-26b-a4b"
D6 = (
    "This model can't view images, so it only saw the file name `shot.png`. "
    "Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures."
)


class FakeSpark:
    def __init__(self):
        self.requests: list[dict] = []
        spark = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_GET(self):
                body = json.dumps(
                    {
                        "data": [
                            {"id": TEXT_ONLY, "description": "Fast text model"},
                            {"id": VISION, "description": "Gemma 4 multimodal (text + image)"},
                        ]
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                spark.requests.append(payload)
                images = sum(
                    1
                    for m in payload.get("messages", [])
                    if isinstance(m.get("content"), list)
                    for part in m["content"]
                    if part.get("type") == "image_url"
                )
                model = payload.get("model", "")
                if images and model != VISION:
                    body = (
                        json.dumps({"error": {"message": f"{model} is not a multimodal model", "code": 400}}).encode()
                        + b"\n"
                    )
                else:
                    text = f"Reply from {model} (images seen: {images})"
                    frames = [
                        {"choices": [{"delta": {"content": text}}]},
                        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                    ]
                    body = b"".join(f"data: {json.dumps(f)}\n\n".encode() for f in frames) + b"data: [DONE]\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def image_counts(self) -> list[int]:
        out = []
        for p in self.requests:
            out.append(
                sum(
                    1
                    for m in p.get("messages", [])
                    if isinstance(m.get("content"), list)
                    for part in m["content"]
                    if part.get("type") == "image_url"
                )
            )
        return out

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def spark_client(operator_client):
    client, store, wiki = operator_client
    spark = FakeSpark()
    gateway = client.app.state.gateway
    gateway.register_provider(OpenAIProviderAdapter(base_url=spark.url, provider_id="vllm", api_key=""))
    gateway.default_provider_id = "vllm"
    store.set_setting(
        "provider_settings",
        {"default_provider_id": "vllm", "default_model_id": TEXT_ONLY, "providers": {"vllm": {"base_url": spark.url}}},
    )
    gateway.default_model_id = f"vllm/{TEXT_ONLY}"
    try:
        yield client, store, spark
    finally:
        spark.close()


def _use_model(client, store, model: str) -> None:
    client.app.state.gateway.default_model_id = f"vllm/{model}"
    settings = store.get_setting("provider_settings") or {}
    settings["default_model_id"] = model
    store.set_setting("provider_settings", settings)


def _session(client) -> str:
    res = client.post("/api/sessions", json={"agent_id": "direct", "title": "CARD-475 contract"})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _upload(client, session_id: str) -> dict:
    res = client.post(
        "/api/chat/upload",
        files={"file": ("shot.png", PNG, "image/png")},
        data={"session_id": session_id},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _send(client, session_id: str, content: str, attachments=None) -> list[tuple[str, dict]]:
    body = {"agent_id": "direct", "session_id": session_id, "content": content, "approval_mode": "ask"}
    if attachments:
        body["attachments"] = attachments
    events: list[tuple[str, dict]] = []
    with client.stream("POST", "/api/chat/stream", json=body) as res:
        assert res.status_code == 200
        current = "message"
        for line in res.iter_lines():
            if line.startswith("event:"):
                current = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                try:
                    events.append((current, json.loads(line[5:].strip())))
                except json.JSONDecodeError:
                    events.append((current, {"raw": line}))
    return events


def _text(events) -> str:
    return "".join(d.get("text", "") for e, d in events if e == "token")


def _empty_rows(store, session_id: str):
    return [
        m
        for m in store.get_messages(session_id=session_id)
        if m.role == Role.ASSISTANT and not (m.content or "").strip() and not m.tool_calls
    ]


def test_image_on_text_only_model_replies_with_notice_and_next_hi_answers(spark_client):
    client, store, spark = spark_client
    sid = _session(client)
    att = _upload(client, sid)

    events = _send(client, sid, "what is this?", [att])
    notices = [d for e, d in events if e == "attachment_notice"]
    assert notices and notices[0]["message"] == D6
    assert f"Reply from {TEXT_ONLY} (images seen: 0)" in _text(events)
    assert not [d for e, d in events if e == "error"]
    assert spark.image_counts() == [0]
    assert _empty_rows(store, sid) == []

    events = _send(client, sid, "Hi")
    assert f"Reply from {TEXT_ONLY}" in _text(events)
    assert not [d for e, d in events if e == "attachment_notice"]
    assert spark.image_counts() == [0, 0]


def test_vision_marked_model_gets_the_image_once(spark_client):
    client, store, spark = spark_client
    res = client.post("/api/settings/model-capabilities", json={"model_id": f"vllm/{VISION}", "vision": True})
    assert res.status_code == 200, res.text
    _use_model(client, store, VISION)
    sid = _session(client)
    att = _upload(client, sid)

    events = _send(client, sid, "what is this?", [att])
    assert f"Reply from {VISION} (images seen: 1)" in _text(events)
    assert not [d for e, d in events if e == "attachment_notice"]
    events = _send(client, sid, "Hi")
    assert f"Reply from {VISION} (images seen: 0)" in _text(events)
    assert spark.image_counts() == [1, 0]


def test_wrongly_marked_model_is_retried_once_without_images(spark_client):
    client, store, spark = spark_client
    res = client.post("/api/settings/model-capabilities", json={"model_id": f"vllm/{TEXT_ONLY}", "vision": True})
    assert res.status_code == 200, res.text
    sid = _session(client)
    att = _upload(client, sid)

    events = _send(client, sid, "what is this?", [att])
    assert [d["message"] for e, d in events if e == "attachment_notice"] == [D6]
    assert f"Reply from {TEXT_ONLY} (images seen: 0)" in _text(events)
    assert spark.image_counts() == [1, 0]
    assert _empty_rows(store, sid) == []


def test_session_poisoned_before_the_fix_answers_hi_and_hides_empty_rows(spark_client, tmp_path):
    client, store, spark = spark_client
    sid = _session(client)
    att = _upload(client, sid)
    # The live shape: image turn, then the empty assistant row the old code saved.
    poisoned = (
        f"what is this?\n\n---\n![shot.png]({att['url']})\n"
        f"*(Attached Image: `shot.png`, {len(PNG)} bytes, format: `image/png`, Local Path: `{att['path']}`)*"
    )
    store.save_message(session_id=sid, agent_id="direct", message=ChatMessage(role=Role.USER, content=poisoned))
    store.save_message(session_id=sid, agent_id="direct", message=ChatMessage(role=Role.ASSISTANT, content=""))

    events = _send(client, sid, "Hi")
    assert f"Reply from {TEXT_ONLY} (images seen: 0)" in _text(events)
    assert not [d for e, d in events if e == "error"]

    thread = client.get(f"/api/sessions/{sid}/messages").json()
    assert not [
        m for m in thread if m["role"] == "assistant" and not (m["content"] or "").strip() and not m["tool_calls"]
    ]
    assert thread[-1]["content"].startswith(f"Reply from {TEXT_ONLY}")


def test_discover_reports_vision_and_saves_provider_metadata(spark_client):
    client, store, spark = spark_client
    res = client.get("/api/models/discover", params={"provider_id": "vllm", "host_url": spark.url})
    assert res.status_code == 200, res.text
    models = {m["name"]: m for m in res.json()["models"]}
    assert models[VISION]["can_view_images"] is True
    assert models[VISION]["vision_source"] == "provider"
    assert models[TEXT_ONLY]["can_view_images"] is False

    res = client.post("/api/settings/model-capabilities", json={"model_id": f"vllm/{TEXT_ONLY}", "vision": True})
    assert res.status_code == 200
    models = {
        m["name"]: m
        for m in client.get("/api/models/discover", params={"provider_id": "vllm", "host_url": spark.url}).json()[
            "models"
        ]
    }
    assert models[TEXT_ONLY]["can_view_images"] is True
    assert models[TEXT_ONLY]["vision_source"] == "override"

    res = client.post("/api/settings/model-capabilities", json={"model_id": f"vllm/{TEXT_ONLY}", "vision": None})
    assert res.status_code == 200
    models = {
        m["name"]: m
        for m in client.get("/api/models/discover", params={"provider_id": "vllm", "host_url": spark.url}).json()[
            "models"
        ]
    }
    assert models[TEXT_ONLY]["vision_source"] == "default"
