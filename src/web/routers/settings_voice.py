"""Optional Voice / Talk settings and proxy routes.

Voice is OFF unless an operator sets a sidecar endpoint URL and enables it in
Settings. AutoReiv never contacts the sidecar at startup, so it is not a
required dependency. When disabled, the proxy routes return 404 voice_disabled.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

router = APIRouter(tags=["Settings"])

VOICE_SETTINGS_KEY = "voice_settings"
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_TEXT_CHARS = 4000


class VoiceSettingsUpdate(BaseModel):
    enabled: bool = False
    endpoint_url: Optional[str] = None
    voice: Optional[str] = None
    auto_speak: bool = True


def _store(request: Request) -> Any:
    return getattr(request.app.state, "store", None)


def resolve_voice_settings(store: Any) -> dict[str, Any]:
    raw: Any = None
    if store is not None:
        try:
            raw = store.get_setting(VOICE_SETTINGS_KEY)
        except Exception:
            raw = None
    raw = raw if isinstance(raw, dict) else {}
    url = str(raw.get("endpoint_url") or "").strip().rstrip("/")
    return {
        "enabled": bool(raw.get("enabled")) and bool(url),
        "endpoint_url": url,
        "voice": str(raw.get("voice") or "").strip(),
        "auto_speak": raw.get("auto_speak", True) is not False,
    }


def _validate_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Voice endpoint must be an http(s) URL, e.g. http://host.docker.internal:8790")
    return url


def _active(request: Request) -> dict[str, Any]:
    cfg = resolve_voice_settings(_store(request))
    if not cfg["enabled"]:
        raise HTTPException(status_code=404, detail={"code": "voice_disabled", "message": "Voice is not configured. Set a voice endpoint in Settings > Voice / Talk."})
    return cfg


@router.get("/api/settings/voice")
async def get_voice_settings(request: Request):
    return resolve_voice_settings(_store(request))


@router.put("/api/settings/voice")
async def update_voice_settings(req: VoiceSettingsUpdate, request: Request):
    store = _store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="State store unavailable.")
    url = _validate_url(req.endpoint_url or "")
    voice = str(req.voice or "").strip()
    if voice and not voice.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Voice name may only contain letters, numbers and underscores.")
    store.set_setting(
        VOICE_SETTINGS_KEY,
        {"enabled": bool(req.enabled), "endpoint_url": url, "voice": voice, "auto_speak": bool(req.auto_speak)},
    )
    return resolve_voice_settings(store)


@router.get("/api/voice/status")
async def voice_status(request: Request):
    """Cheap check the chat UI uses to decide whether to show the Talk button."""
    cfg = resolve_voice_settings(_store(request))
    out = {"enabled": cfg["enabled"], "auto_speak": cfg["auto_speak"], "reachable": False}
    if not cfg["enabled"]:
        return out
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{cfg['endpoint_url']}/health")
        data = r.json() if r.status_code == 200 else {}
        out["reachable"] = bool(data.get("ok"))
        out["stt"] = bool(data.get("stt"))
        out["tts"] = bool(data.get("tts"))
    except Exception as exc:  # sidecar down is a normal state, not an error
        out["error"] = f"Voice endpoint unreachable: {type(exc).__name__}"
    return out


@router.post("/api/voice/transcribe")
async def voice_transcribe(request: Request):
    cfg = _active(request)
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="No audio received.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Recording too large.")
    ctype = request.headers.get("content-type") or "application/octet-stream"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{cfg['endpoint_url']}/stt", content=audio, headers={"Content-Type": ctype})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Voice endpoint unreachable: {type(exc).__name__}")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Transcription failed (HTTP {r.status_code}).")
    return JSONResponse({"text": str(r.json().get("text") or "").strip()})


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@router.post("/api/voice/speak")
async def voice_speak(req: SpeakRequest, request: Request):
    cfg = _active(request)
    text = (req.text or "").strip()[:MAX_TEXT_CHARS]
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")
    body = {"text": text}
    voice = (req.voice or cfg["voice"] or "").strip()
    if voice:
        body["voice"] = voice
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{cfg['endpoint_url']}/tts", json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Voice endpoint unreachable: {type(exc).__name__}")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Speech failed (HTTP {r.status_code}).")
    return Response(content=r.content, media_type=r.headers.get("content-type", "audio/wav"))
