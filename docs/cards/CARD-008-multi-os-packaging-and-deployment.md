# [CARD-008] Multi-OS Packaging & Bare-Metal / Docker Deployment

> **Status**: Done  
> **Milestone**: Milestone 8 (v0.8.0)  
> **Primary Component**: `AutoReiv.Deploy`  
> **Spec Reference**: `docs/specs/packaging-multi-os-deployment/`  
> **ADR Reference**: [`docs/adr/0009-multi-os-packaging-docker-compose-systemd-and-unified-cli-entry-point.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0009-multi-os-packaging-docker-compose-systemd-and-unified-cli-entry-point.md)  
> **Requirements**: `[REQ-DEPLOY-001]` to `[REQ-DEPLOY-006]`

---

## 1. Why / Intent
AutoReiv must be easily deployable on a variety of environments:
- **Ubuntu CLI Bare-Metal** (Target: Nimo Mini PC 2L with 128GB unified memory running local Ollama).
- **Windows 11 Desktop / Background Service** (via native PowerShell/batch scripts).
- **Docker Compose** (for cross-platform containerized hosting with persistent volume mounts).
- **Dedicated CLI (`autoreiv`)** for terminal management, real-time chat, and routine triggers.

---

## 2. What Was Built
- **Unified CLI Tool (`src/cli/main.py`)**: `autoreiv serve`, `autoreiv status`, `autoreiv chat`, and `autoreiv routine [list|run]`.
- **FastAPI Lifespan Routine Scheduler**: Background tick loop automatically boots on web startup and cleans up on shutdown.
- **Ubuntu `systemd` Daemon (`deploy/systemd/`)**: `autoreiv.service` unit with automated installer `install_systemd.sh`.
- **Windows Runners (`deploy/windows/`)**: `run_autoreiv.ps1`, `run_autoreiv.bat`, and `install_windows_service.ps1`.
- **Docker Compose & Multi-Stage Dockerfile**: Non-root container with host volume mounts for `./data/autoreiv.db` and `./data/wiki`.

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-DEPLOY-001]`: Unified CLI parser and subcommands verified.
- [x] `[REQ-DEPLOY-002]`: Interactive terminal chat loop with token streaming verified.
- [x] `[REQ-DEPLOY-003]`: Ubuntu systemd service unit and installer verified.
- [x] `[REQ-DEPLOY-004]`: Native Windows PowerShell and batch runners verified.
- [x] `[REQ-DEPLOY-005]`: Dockerfile and Docker Compose manifests with volume mounts verified.
- [x] `[REQ-DEPLOY-006]`: Automated unit test suite passing (`tests/unit/cli/`).
