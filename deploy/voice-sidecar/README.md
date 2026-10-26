# Optional voice sidecar (Talk button)

AutoReiv does not need voice. The chat Talk button only appears when
**Settings > Voice / Talk** has an endpoint URL, is enabled, and the endpoint answers `/health`.

Any service with this contract works:

| Route | Request | Response |
|---|---|---|
| `GET /health` | – | `{"ok": true, "stt": bool, "tts": bool}` |
| `POST /stt` | raw audio body (webm/ogg/wav) | `{"text": "..."}` |
| `POST /tts` | `{"text": "...", "voice": "af_heart"}` | `audio/wav` |

`voice_sidecar.py` is a stdlib reference that shells out to local CLIs
(`VOICE_STT_CMD`, default `~/.local/bin/whisper-stt`; `VOICE_TTS_CMD`, default `~/.local/bin/kokoro-say`).
Both run on CPU.

## Spark install (user systemd)

```bash
cp deploy/voice-sidecar/voice_sidecar.py ~/voice/voice_sidecar.py
cp deploy/voice-sidecar/autoreiv-voice.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now autoreiv-voice
curl http://172.17.0.1:8790/health
```

It binds to the docker bridge (`172.17.0.1:8790`), not the LAN. The AutoReiv
container reaches it through the existing `extra_hosts: host.docker.internal:host-gateway`,
so set the endpoint to `http://host.docker.internal:8790`.

Browser mic access requires HTTPS or `localhost` (e.g. an SSH tunnel to port 8000).
