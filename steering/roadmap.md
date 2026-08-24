# AutoReiv Master Engineering Roadmap (v0.1.0 - v1.0.0)

> **Repository**: `jacobbweber/AutoReiv`  
> **Target Release**: Production Multi-Agent SRE & Knowledge Platform (v1.0.0)  
> **Branch Strategy**: Features cut from `qa` (`feat/*`), merged to `qa`, and promoted to `main`.

---

## 🗺️ Milestone Evolution

### Phase 1: Local-First Core Foundations (Completed & Merged to `qa`)
- [x] **Milestone 1 (v0.1.0)**: Multi-Provider LLM Gateway, Ollama/OpenAI Adapters, Streaming Demuxer (`<think>`).
- [x] **Milestone 2 (v0.2.0)**: Agent Kernel ReAct Engine, Scoped Tool Registry, SQLite WAL State Persistence.
- [x] **Milestone 3 (v0.3.0)**: 4 Built-in Day-1 Agents (General Assistant, Linux Sysadmin, Librarian, System Agent) & Scoped Skills.
- [x] **Milestone 4 (v0.4.0)**: Autonomous Routine Engine, Cron/Interval Schedule Matcher, Background Scheduler.
- [x] **Milestone 5 (v0.5.0)**: Settings Studio, Live Model Discovery, Hermes-style Purpose Matrix, 128GB Nimo PC RAM Calculator, Provider URL/Token Credentials.
- [x] **Milestone 6 (v0.6.0)**: Analytical Observability & KPI Dashboard Backend, Sub-millisecond SQLite Spans, Tool Reliability Matrix, JSON Trace Dumps.
- [x] **Milestone 7 (v0.7.0)**: Responsive Web & Mobile Front-Door, Real-Time SSE Streaming, Collapsible Reasoning Drawers, One-Click PARA-Wiki Exporter.
- [x] **Milestone 8 (v0.8.0)**: Multi-OS Packaging & Deployment, Unified CLI `autoreiv`, Ubuntu `systemd` daemon, Windows service/runners, Docker Compose with volume mounts.

---

### Phase 2: Frontend Modularization, Quality Gates & Stability Remediation
- [x] **Milestone 9 (v0.9.0 - P0 Critical Safety)**:
  - [x] **CARD-031**: Frontend Modularization Foundation & Baseline Quality Gates (ES modules, try/catch isolated `initApp()`, defensive `$(id)` DOM helpers, Playwright zero-console-error smoke test gate, Vitest pure utils test suite).
  - [x] **CARD-032**: Playwright CI/Pre-Flight Gate Integration & Multi-Studio Navigation Smoke Suite.
  - [x] **CARD-033**: Defensive DOM Query & Null-Safety Audit across all Studio interfaces.



- [ ] **Milestone 10 (v0.10.0 - P1 Quality & Testability)**:
  - [x] **CARD-034**: ESLint & Prettier Static Analysis Pipeline for Frontend.
  - [x] **CARD-035**: Comprehensive Unit Test Suite for Frontend Pure Logic (Vitest: mind-map physics, state reducers, token formatters).
  - [x] **CARD-036**: Gateway, Wiki & Settings End-to-End API Contract Integration Tests.
  - **CARD-037**: Steering & Product Documentation Truth Sync (`product.md`, `steering/roadmap.md`).

- [ ] **Milestone 11 (v0.11.0 - P2 UX Hardening & Resilience)**:
  - **CARD-038**: Mobile & Keyboard Accessibility (ARIA roles, focus traps, screen-reader landmarks).
  - **CARD-039**: Performance Budgets, Module Bundling & First-Paint Optimization.
  - **CARD-040**: User-Visible Error Boundary Toasts & Offline/Degraded Backend Messaging.

---

### Phase 3: Enterprise Agentic Cognition, Security & Multi-Agent Architecture
- [ ] **Milestone 12 (v0.12.0)**: Context Window Compaction, Episodic Fact Memory Store, and Resilience Hardening (Exponential Backoff + Jitter, Connection Pooling, Streaming Cycle Detection).
- [ ] **Milestone 13 (v0.13.0)**: Ephemeral Subprocess Sandbox, Dangerous Command Safety Guardrails, and Human-In-The-Loop (HITL) State Parking & Resume Engine.
- [ ] **Milestone 14 (v0.14.0)**: Multi-Agent Inter-Agent Handoff Protocol (A2A 5-Key Envelope) and Supervisor Delegation Orchestration.
- [ ] **Milestone 15 (v0.15.0)**: Model Context Protocol (MCP) Standard Client Adapter and Dynamic Intent-Driven Skill Manual Loader.

