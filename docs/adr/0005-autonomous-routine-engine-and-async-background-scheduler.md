# ADR-0005: Autonomous Routine Engine and Async Background Scheduler

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 4, 7, 12)

---

## 1. Context & Problem Statement

AutoReiv is designed as a hybrid platform: users interact with agents directly via chat, and agents run autonomous scheduled activities (routines) without human prompts (e.g. morning briefing, daily server metrics, nightly wiki hygiene).

We need an execution framework that evaluates due schedules, runs autonomous turns through `AgentKernel`, persists execution history in SQLite, and captures performance telemetry without blocking interactive chat threads.

---

## 2. Decision Drivers

* **Non-Blocking Concurrency**: The scheduler tick loop must run in an `asyncio` task without stalling API response times.
* **Hermetic & Isolated Sessions**: Each routine execution should create a dedicated ephemeral session in `SQLiteStateStore` so autonomous message traces don't pollute active human chat sessions.
* **Deterministic & Robust Error Handling**: If an autonomous routine fails (e.g. LLM timeout or tool error), the scheduler logs the failure to `routine_runs` and continues running remaining schedules without crashing.

---

## 3. Considered Options

* **Option 1**: System OS `cron` invoking external CLI commands per routine.
* **Option 2**: Heavy third-party distributed task queue (Celery + Redis).
* **Option 3 (Recommended)**: In-process asynchronous `RoutineScheduler` backed by embedded SQLite state and interval/cron matchers.

---

## 4. Decision Outcome

Chosen option: **Option 3 (In-Process Asynchronous RoutineScheduler)**, because:
- It runs with zero external dependencies (no Redis/RabbitMQ required), fitting seamlessly on bare metal Ubuntu (Nimo PC), Windows, or lightweight Docker Compose.
- It shares the unified `AgentKernel`, `ScopedToolRegistry`, and `TelemetryCollector`.
- It enables instant manual triggers via the same service API.
