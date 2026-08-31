# [CARD-130] Surfacing Per-Agent Telemetry and Token Cost Metrics in Agent Studio and Observability

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-006; CARD-016; CARD-129
> **Labels**: `type:feat`, `type:ui`, `type:observability`

---

## 1. Why / Intent
In Agent Studio, selecting an agent (e.g. `Assistant`) currently renders `0` across all 5 stat cards under "Agent Telemetry & Lifetime Stats" because the UI client expects flat properties on the KPI response rather than traversing `data.agents`. Additionally, while CARD-129 added backend token cost estimation, estimated dollar costs (`$`) and Time-To-First-Token (TTFT) are not yet surfaced in either Observability Studio or Agent Studio.

---

## 2. What to Build

### Slice 1: Agent Studio Per-Agent Telemetry Binding
- Fix `loadAgentTelemetry(agentId)` in `src/web/static/modules/studios/forge.js` to correctly extract that agent's stats from `data.agents` (matching `agent.id` and legacy aliases like `general-assistant` $\rightarrow$ `assistant`).
- Add an **Est. Cost ($)** stat card under "Agent Telemetry & Lifetime Stats" in `src/web/templates/index.html` and bind it in `forge.js`.

### Slice 2: Observability Studio Cost & TTFT Cards
- Add an **Est. Cost ($)** and **Avg TTFT (ms)** card to the top metric overview row in Observability Studio (`src/web/templates/index.html` and `src/web/static/modules/studios/observability.js`).
- Add an **Est. Cost ($)** column to the "Per-Agent KPI Breakdown" table in Observability Studio.

### Slice 3: Domain & Repository Model Alignment
- Extend `AgentKPISummary` in `src/domain/observability/models.py` with `estimated_cost_usd: float`.
- Update `get_agent_kpi_breakdown()` in `src/infrastructure/memory/repositories/telemetry.py` to calculate `estimated_cost_usd` per agent based on total tokens consumed.
- Update `/api/observability/kpi` in `src/web/routers/observability.py` to optionally filter overview KPIs if `?agent_id=` query param is provided.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Selecting an agent in Agent Studio immediately populates real lifetime turns, tokens, tool calls, error rate, avg latency, and estimated cost ($).
- [x] Observability Studio displays global Estimated Cost ($) and Avg TTFT (ms) in the top metric overview row.
- [x] Observability Studio "Per-Agent KPI Breakdown" table includes an "Est. Cost" column.
- [x] Legacy agent ID aliases (e.g. `general-assistant` $\leftrightarrow$ `assistant`) resolve correctly in telemetry queries.
- [x] Full automated test suite passes (backend pytest + frontend vitest).
- [x] Local commit on `qa`. Card status `In Review` after code.

---

## 4. Constraints
- Work on `qa`. Do not push or tag unless explicitly asked.
- Zero regression on existing telemetry APIs or database schemas.
- Single card in focus.
