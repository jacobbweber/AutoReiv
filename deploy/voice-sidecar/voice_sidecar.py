#!/usr/bin/env python3
"""AutoReiv optional voice sidecar (stdlib only).

Wraps two local CLIs so AutoReiv can offer a Talk button without depending on them:
  POST /stt     raw audio body (webm/ogg/wav/...) -> {"text": "..."}   (VOICE_STT_CMD AUDIOFILE)
  POST /tts     {"text": "...", "voice": "af_heart"} -> audio/wav      (VOICE_TTS_CMD OUT.wav TEXT)
  GET  /health  -> {"ok": true, "stt": bool, "tts": bool}

Bind to localhost or the docker bridge only (default 172.17.0.1:8790), never the public internet.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("VOICE_HOST", "172.17.0.1")
PORT = int(os.environ.get("VOICE_PORT", "8790"))
STT_CMD = os.environ.get("VOICE_STT_CMD", os.path.expanduser("~/.local/bin/whisper-stt"))
TTS_CMD = os.environ.get("VOICE_TTS_CMD", os.path.expanduser("~/.local/bin/kokoro-say"))
MAX_AUDIO = int(os.environ.get("VOICE_MAX_AUDIO_BYTES", str(25 * 1024 * 1024)))
MAX_TEXT = int(os.environ.get("VOICE_MAX_TEXT_CHARS", "4000"))
TIMEOUT = int(os.environ.get("VOICE_TIMEOUT_SECONDS", "120"))


def _available(cmd: str) -> bool:
    return bool(cmd) and (os.access(cmd, os.X_OK) or shutil.which(cmd) is not None)


class Handler(BaseHTTPRequestHandler):
    server_version = "AutoReivVoice/1.0"

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self, limit: int) -> bytes | None:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > limit:
            return None
        return self.rfile.read(n)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            return self._json(200, {"ok": True, "stt": _available(STT_CMD), "tts": _available(TTS_CMD)})
        self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")
        if path == "/stt":
            return self._stt()
        if path == "/tts":
            return self._tts()
        self._json(404, {"error": "not found"})

    def _stt(self):
        data = self._body(MAX_AUDIO)
        if not data:
            return self._json(400, {"error": "empty or too-large audio body"})
        with tempfile.NamedTemporaryFile(suffix=".audio") as f:
            f.write(data)
            f.flush()
            try:
                r = subprocess.run([STT_CMD, f.name], capture_output=True, text=True, timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                return self._json(504, {"error": "transcription timed out"})
        if r.returncode != 0:
            return self._json(500, {"error": "transcription failed", "detail": r.stderr[-500:]})
        self._json(200, {"text": r.stdout.strip()})

    def _tts(self):
        raw = self._body(64 * 1024)
        try:
            payload = json.loads(raw or b"{}")
        except ValueError:
            return self._json(400, {"error": "invalid json"})
        text = str(payload.get("text") or "").strip()[:MAX_TEXT]
        if not text:
            return self._json(400, {"error": "text is required"})
        env = dict(os.environ)
        voice = str(payload.get("voice") or "").strip()
        if voice.replace("_", "").isalnum():
            env["KOKORO_VOICE"] = voice
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.wav")
            try:
                r = subprocess.run([TTS_CMD, out, text], capture_output=True, text=True, timeout=TIMEOUT, env=env)
            except subprocess.TimeoutExpired:
                return self._json(504, {"error": "speech timed out"})
            if r.returncode != 0 or not os.path.exists(out):
                return self._json(500, {"error": "speech failed", "detail": r.stderr[-500:]})
            with open(out, "rb") as fh:
                wav = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

    def log_message(self, fmt, *args):
        print("voice-sidecar:", fmt % args, flush=True)


if __name__ == "__main__":
    print(f"voice-sidecar listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
