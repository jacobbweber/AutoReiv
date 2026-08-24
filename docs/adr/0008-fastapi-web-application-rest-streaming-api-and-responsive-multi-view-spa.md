# ADR-0008: FastAPI Web Application REST/SSE Streaming API and Responsive Multi-View SPA

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 2, 7, 10, 11)

---

## 1. Context & Problem Statement

AutoReiv needs an intuitive, responsive web and mobile front-door:
1. Interactive real-time streaming chat with reasoning token breakdown (`<think>`) and live tool invocation progress.
2. Segregated chat histories per agent profile (General Assistant, Linux Sysadmin, Librarian, System Agent).
3. One-click "Export to Wiki" and "Copy" actions on messages and threads.
4. Embedded Settings Studio (live Ollama/OpenAI model picker, purpose matrix, hardware RAM slider).
5. Observability KPI dashboard and Autonomous Routine controls.
6. Zero Node.js / NPM build toolchain friction (runs directly on Python server).

---

## 2. Decision Drivers

* **Zero-Build Simplicity**: Single lightweight Python server (`uvicorn` + `fastapi`) serving static modern HTML5/JS without requiring heavy webpack/vite/node installs.
* **Server-Sent Events (SSE)**: Standard HTTP streaming supported natively across all desktop and mobile browsers.
* **Path-Jailed Document Safety**: Wiki exports write securely to dedicated directories.

---

## 3. Considered Options

* **Option 1**: Separate Node.js/React frontend with reverse proxy.
* **Option 2**: Command-line only interface (TUI).
* **Option 3 (Recommended)**: Integrated FastAPI application serving REST & SSE endpoints with responsive single-page application (SPA).

---

## 4. Decision Outcome

Chosen option: **Option 3 (Integrated FastAPI with Responsive SPA and SSE Streaming)**, because:
- It eliminates multi-process build friction.
- It deploys seamlessly in Docker, `systemd`, or standalone Windows/Linux terminals.
- It provides native streaming, wiki export, and live dashboard metrics.
