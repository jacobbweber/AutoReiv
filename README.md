# AutoReiv

Local-first control plane for a roster of independent AI agents. You run it on your machine (or on the LAN). Chat, routines, settings, wiki, and HITL approvals stay on disk. Models can be local Ollama, a LAN host, or a cloud provider.

**Status:** Educational and a work in progress. The aim is a fully functional, production-ready control plane. I am learning while I build it, so features and behavior can change. Treat the current state as real software that is still being hardened, not a finished release.

This repository is the product. It is **not** the Agentic SDLC GitHub template that originally scaffolded it.

**Repo:** https://github.com/jacobbweber/AutoReiv

The teaching path that led here lives in [script-to-agent-labs](https://github.com/jacobbweber/script-to-agent-labs) (`demos/autoreiv` points back at this repo).

---

## Quick Start

### Prerequisites

- **Python**: Version **3.10, 3.11, or 3.12** (Python 3.12 recommended).
  - **Windows**: Install via terminal: `winget install Python.Python.3.12` or download from [python.org](https://www.python.org/downloads/). *(Important: check "Add python.exe to PATH" during installation)*.
  - **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install python3 python3-venv python3-pip git`
- **Git**: [git-scm.com](https://git-scm.com/) or `winget install Git.Git`

---

### 1. Clone the Repository

```bash
# 1. Make the directory where you want to keep AutoReiv
mkdir path-you-want
cd path-you-want

# 2. Clone the code into the current folder
git clone https://github.com/jacobbweber/AutoReiv.git .
```

---

### 2. Create & Enter the Virtual Environment (`.venv`)

Isolate your Python dependencies in a local `.venv` folder:

#### **Windows (PowerShell)**:
```powershell
# 1. Create the virtual environment folder
python -m venv .venv

# 2. Allow script execution if restricted (only needed once per terminal session)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# 3. Enter (activate) the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install AutoReiv and its dependencies in editable mode
pip install -e .
```
*(When activated, your PowerShell prompt will show `(.venv)` at the beginning).*

#### **Windows (Command Prompt / CMD)**:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

#### **Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

### 3. Run with Auto-Reload

Start the FastAPI server and routine engine in development mode with live reload:

- **Unified CLI (Cross-Platform)**:
  ```bash
  autoreiv serve --reload --host 0.0.0.0 --port 8000
  # Or directly via Python:
  python -m src.cli.main serve --reload
  ```

- **Windows Native Launcher**:
  ```powershell
  .\deploy\windows\run_autoreiv.ps1 -Reload
  ```

Open **http://127.0.0.1:8000** in your browser.

---

### 4. Install as a Background Service

Run AutoReiv continuously on startup in the background:

- **Windows Service (via NSSM)**:
  ```powershell
  # Run from an Administrator PowerShell prompt:
  .\deploy\windows\install_windows_service.ps1
  ```

- **Linux systemd Daemon (Ubuntu / Debian)**:
  ```bash
  # Run as root:
  sudo ./deploy/systemd/install_systemd.sh

  # Check status & logs:
  sudo systemctl status autoreiv.service
  sudo journalctl -u autoreiv.service -f
  ```

---

### 5. Docker Compose

Run fully containerized with persistent storage volumes:

```bash
# Build and run in detached mode
docker compose up -d --build

# View logs
docker compose logs -f
```

---

## What you get

A FastAPI backend and a vanilla SPA with eight studios:

| Studio | What it is for |
|---|---|
| **Chat** | Multi-session streaming chat. Pick an agent. HITL cards when a tool needs approval. |
| **Routines** | Scheduled jobs (cron or interval). Pause, trigger, history. |
| **Observability** | Turns, tokens, latency, logs. |
| **Agent Forge** | Create and edit agent profiles, prompts, tone, allowed tools. |
| **Settings** | Providers (Ollama, OpenAI, and others), model discovery, purpose matrix. |
| **Docs** | Built-in architecture and ADR viewer. |
| **Projects** | Coding project folders under `projects_root`. Separate from wiki. |
| **Wiki** | Local markdown vault, graph, mind map, inbox. |

Defaults on Windows:

- UI / API: `http://127.0.0.1:8000` (bound `0.0.0.0:8000` so LAN browsers work)
- Health: `GET /health` and `GET /api/health`
- SQLite: `data/autoreiv.db`
- Wiki: `data/wiki`

---

## Configuration

Copy `.env.example` to `.env` if you want file-based settings. Typical local / lab values:

```env
HOST=0.0.0.0
PORT=8000
AUTOREIV_DATA_DIR=
# AUTOREIV_DB_PATH=
# AUTOREIV_WIKI_PATH=
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

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
platform-packs/          always-installed Platform Agent Packs (Assistant, AutoReiv)
agent-packs/             optional specialist catalog (not loaded on startup)
tests/                   pytest, vitest, Playwright smoke
```

---

## Agent Packs

Assistant and AutoReiv ship in [`platform-packs/`](platform-packs/) and always install into `$DATA_DIR/packs/` on launch if missing. Optional specialists live in [`agent-packs/`](agent-packs/) (Agent Studio Import, or AutoReiv `import_agent_pack`). The app does not scan `agent-packs/` on startup. See [`docs/agent-packs.md`](docs/agent-packs.md).
