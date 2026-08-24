# ADR-0009: Multi-OS Packaging Docker Compose systemd and Unified CLI Entry Point

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 2, 7, 10, 11)

---

## 1. Context & Problem Statement

AutoReiv needs to run seamlessly across several host environments:
1. **Ubuntu CLI / systemd daemon**: Dedicated mini PC (e.g. Nimo Mini PC 2L with 128GB unified RAM) running Ollama locally.
2. **Windows Desktop / Service**: Local developer workstation.
3. **Docker Compose**: Containerized execution with persistent database (`/data/autoreiv.db`) and wiki documents (`/data/wiki`).
4. **Unified CLI (`autoreiv`)**: Direct terminal interface for server start, diagnostics (`status`), interactive terminal chat, and routine runs.

---

## 2. Decision Drivers

* **Zero Boilerplate**: Single CLI binary/script entry point (`autoreiv`) handling all operations.
* **Persistent Host Storage**: Clear separation of data directories (`./data/wiki`, `./data/autoreiv.db`) for volume mounts.
* **Reliable Daemon Execution**: Native `systemd` unit with auto-restart policies on Linux and PowerShell runners on Windows.

---

## 3. Considered Options

* **Option 1**: Docker-only deployment. (Leaves bare-metal mini PC without native systemd control).
* **Option 2**: Manual python script execution only. (Lacks daemon lifecycle management).
* **Option 3 (Recommended)**: Multi-target deployment suite: Unified CLI + `systemd` daemon unit + Windows runners + Docker Compose with volume mounts.

---

## 4. Decision Outcome

Chosen option: **Option 3 (Multi-Target Deployment Suite)**, providing maximum deployment flexibility for both bare-metal Ubuntu/Windows and containerized Docker environments.
