# Requirements Specification: Multi-OS Packaging & Bare-Metal / Docker Deployment

> **Spec Status**: Implemented  
> **Target Release**: Milestone 8 (v0.8.0)  
> **Primary Component**: `AutoReiv.Deploy`  
> **Applicable ADRs**: `docs/adr/0009-multi-os-packaging-docker-compose-systemd-and-unified-cli-entry-point.md`

---

## 1. Executive Summary & Intent

Milestone 8 delivers production deployment packaging for AutoReiv across multiple OS targets (Ubuntu CLI on the Nimo Mini PC 2L, Windows 11/Service, and Docker Compose with volume mounts), anchored by a unified CLI entry point (`autoreiv`).

---

## 2. User Stories & EARS Functional Requirements

### [REQ-DEPLOY-001]: Unified CLI Entry Point (`autoreiv`)
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator runs 'autoreiv [serve|status|chat|routine]' via the terminal THE SYSTEM SHALL execute the designated runtime mode with structured flags and exit codes.`
- **Acceptance Criteria**:
  - [ ] `autoreiv serve --port 8000` launches the FastAPI web server and routine tick engine.
  - [ ] `autoreiv status` outputs detected hardware specs, database connectivity, and registered agents.
  - [ ] `autoreiv routine list` and `autoreiv routine run <id>` manage routines from the CLI.

### [REQ-DEPLOY-002]: Environment Configuration & Path Overrides
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL read runtime configuration from .env and environment variables, supporting custom paths for AUTOREIV_DB_PATH, AUTOREIV_WIKI_PATH, OLLAMA_HOST, and PORT.`
- **Acceptance Criteria**:
  - [ ] Given custom `AUTOREIV_WIKI_PATH` and `AUTOREIV_DB_PATH`, when initialized, then state store and wiki service write to the specified paths.

### [REQ-DEPLOY-003]: Ubuntu / systemd Daemon Service
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide a systemd service unit file (autoreiv.service) and automated installer script configured for persistent background execution on Ubuntu Linux hosts.`
- **Acceptance Criteria**:
  - [ ] Given `deploy/systemd/autoreiv.service`, includes restart policies, working directory, and environment variable bindings.

### [REQ-DEPLOY-004]: Windows Service & Script Runners
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide PowerShell and batch scripts (run_autoreiv.ps1, run_autoreiv.bat, install_windows_service.ps1) for native Windows execution.`
- **Acceptance Criteria**:
  - [ ] Given `deploy/windows/run_autoreiv.ps1`, when executed, activates virtualenv and launches the server.

### [REQ-DEPLOY-005]: Docker & Docker Compose Containerization
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide a multi-stage Dockerfile and docker-compose.yml mounting host volumes for persistent database (/data/autoreiv.db) and wiki notes (/data/wiki).`
- **Acceptance Criteria**:
  - [ ] Given `docker-compose.yml`, defines volumes for `./data/wiki` and `./data/autoreiv.db`, connects to host Ollama, and exposes port 8000.

### [REQ-DEPLOY-006]: Concurrent Background Routine Scheduler in Server Mode
- **Type**: State-Driven
- **EARS Statement**: `WHILE the web server is running THE SYSTEM SHALL execute the async background routine scheduler loop concurrently with FastAPI HTTP request handling.`
- **Acceptance Criteria**:
  - [ ] When the FastAPI app starts up via `lifespan`, then begins background scheduler tick task and cancels cleanly upon shutdown.

---

## 3. Non-Functional & Boundary Constraints

- **Minimal Image Size**: Docker image uses Python slim base with multi-stage caching.
- **Graceful Shutdown**: All background scheduler loops capture `SIGTERM`/`SIGINT` and shut down without corrupting SQLite WAL transactions.
