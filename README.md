# AutoReiv

Local-first control plane for a roster of independent AI agents. You run it on your machine (or on the LAN). Chat, routines, settings, wiki, and HITL approvals stay on disk. Models can be local Ollama, a LAN host, or a cloud provider.

**Status:** Educational and a work in progress. The aim is a fully functional, production-ready control plane. I am learning while I build it, so features and behavior can change. Treat the current state as real software that is still being hardened, not a finished release.

This repository is the product. It is **not** the Agentic SDLC GitHub template that originally scaffolded it.

**Repo:** https://github.com/jacobbweber/AutoReiv

The teaching path that led here lives in [script-to-agent-labs](https://github.com/jacobbweber/script-to-agent-labs) (`demos/autoreiv` points back at this repo).

---

## What you get

A FastAPI backend and a vanilla SPA with seven studios:

| Studio | What it is for |
|---|---|
| **Chat** | Multi-session streaming chat. Pick an agent. HITL cards when a tool needs approval. |
| **Routines** | Scheduled jobs (cron or interval). Pause, trigger, history. |
| **Observability** | Turns, tokens, latency, logs. |
| **Agent Forge** | Create and edit agent profiles, prompts, tone, allowed tools. |
| **Settings** | Providers (Ollama, OpenAI, and others), model discovery, purpose matrix. |
| **Docs** | Built-in architecture and ADR viewer. |
| **Wiki** | Local markdown vault, graph, mind map, inbox. |

Defaults on Windows (Jarvis):

- UI / API: `http://127.0.0.1:8000` (bound `0.0.0.0:8000` so LAN browsers work)
- Health: `GET /health` and `GET /api/health`
- SQLite: `data/autoreiv.db`
- Wiki: `data/wiki`

---

## Run it (Windows)

From the repo root, PowerShell:

```powershell
.\deploy\windows\run_autoreiv.ps1 -Reload
```

Then open `http://127.0.0.1:8000` and hard-refresh if you just pulled UI changes.

Useful flags: `-HostIP 0.0.0.0`, `-Port 8000`, `-Reload`. Override DB or wiki with `-DbPath` / `-WikiPath`.

Copy `.env.example` to `.env` if you want file-based settings. Typical local / lab values:

```
HOST=0.0.0.0
PORT=8000
AUTOREIV_DB_PATH=./data/autoreiv.db
AUTOREIV_WIKI_PATH=./data/wiki
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.8:latest
```

On this lab, Ollama often lives on Nimo at `http://192.168.1.29:11434`. Set that in Settings or `OLLAMA_HOST`. Do not commit `.env` or API keys.

---

## Layout

```
src/web/                 FastAPI app + static studios
src/application/         kernel, gateway, HITL, skills, settings
src/domain/              agents, memory, wiki, routines, safety
src/infrastructure/      SQLite, Ollama / OpenAI adapters
deploy/windows/          run_autoreiv.ps1
data/                    created at runtime (db + wiki)
steering/                product / tech / structure notes
docs/                    specs, ADRs, RTM
tests/                   pytest, vitest, Playwright smoke
```
