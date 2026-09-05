---
id: CARD-135
title: "Show Me the Journey: Execution Progress Timeline & Goal Journey Inspector"
status: Done
priority: Medium
created: 2026-09-02
owner: Antigravity
description: "Interactive visual timeline and journey drawer for complex chat and goal turns, displaying what milestones the agent planned, what tools and actions were taken, what facts were discovered, and what steps remain."
---

# CARD-135: Show Me the Journey — Execution Progress Timeline & Goal Journey Inspector

## 1. Context & Motivation
When an agent works through multi-step goals or complex execution loops, users want a quick, intuitive way to see the "journey" of how the agent arrived at its result:
- What plan did it formulate?
- What tools did it execute along the way (and in what order)?
- What intermediate facts or decisions were made?
- What step is currently active or next?

## 2. Invariants & UI Contract
- **Access Point**: A "Show Journey" action button (`#chatShowJourneyBtn`) on active chat sessions and goal execution headers.
- **Drawer / Inspector View**: A slide-out panel or collapsible timeline showing:
  1. **Goal / Objective Summary**: The target intent.
  2. **Step-by-Step Chronology**: Milestones (Pending, In Progress, Completed, Failed).
  3. **Tool Execution Badges**: Compact pill badges showing tool name, arguments summary, and execution duration.
  4. **Key Discoveries**: Artifacts generated or facts learned during the run.
- **Zero Overhead for Simple Chats**: Single-turn casual conversations remain lightweight with no timeline clutter unless opened.

## 3. Vertical Slices

### Slice 1: Backend Journey Synthesis API
- Endpoint `GET /api/chat/sessions/{session_id}/journey` aggregating:
  - Plan steps from `plan_engine` or messages history.
  - Tool calls, durations, and outputs from session messages and telemetry spans.
  - Artifact references generated in that session.

### Slice 2: Frontend Journey Timeline Component
- Journey drawer modal/panel (`#chatJourneyDrawer`) in `#view-chat`.
- Interactive vertical timeline showing milestone cards with status indicators (emerald check, indigo spinner, amber warning).
- Expandable step details for tool calls and sub-tasks.

### Slice 3: Verification & Automated Tests
- Pytest integration tests for journey aggregation API.
- Vitest unit tests for timeline rendering and state transitions.
