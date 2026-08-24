# ADR-0007: Comprehensive Telemetry Aggregation, Per-Agent KPIs, and Tool Reliability Matrix

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 9, 10)

---

## 1. Context & Problem Statement

AutoReiv requires full modern observability into all operations:
1. Global platform usage (total turns, prompt tokens, completion tokens, error rates).
2. Per-agent breakdowns (tokens and turns consumed per agent profile).
3. Tool and skill reliability metrics (success/error ratios and execution duration).
4. Time-series chart aggregations and trace filtering.
5. Zero dependency on external SaaS telemetry providers (like Datadog or Prometheus) to keep AutoReiv lightweight, self-hosted, and offline-first.

---

## 2. Decision Drivers

* **Hermetic Local Execution**: All analytics must run efficiently inside SQLite State Store using optimized indices.
* **Granular Traceability**: Spans are recorded at the turn, LLM call, and tool execution boundaries.
* **Fast Dashboard Feeds**: Aggregate queries must return in under 5ms.

---

## 3. Considered Options

* **Option 1**: External OpenTelemetry collector and Prometheus/Jaeger containers.
* **Option 2**: In-memory ephemeral counters that wipe on reboot.
* **Option 3 (Recommended)**: SQLite indexed telemetry store with SQL aggregation queries, application-layer dashboard service, and structured JSON exporter.

---

## 4. Decision Outcome

Chosen option: **Option 3 (SQLite Indexed Telemetry with Aggregation Service)**, because:
- It maintains zero external dependencies.
- It survives application restarts and power cycles on bare metal (e.g. Nimo Mini PC).
- It provides structured JSON export for external auditing or UI rendering.
