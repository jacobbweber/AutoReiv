---
id: CARD-495
title: "The autonomous training loop has no front door: you can't start or list jobs, and Lab Monitor opens only from a job you just started"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-472
  - CARD-306
  - CARD-159
  - CARD-270
labels:
  - type:product
  - area:factory
  - area:frontend
  - P2
---

# [CARD-495] The autonomous training loop has no front door

> **Status**: Ready (needs Jacob's product call before planning code)
> **Created**: 2026-09-25
> **Observed during**: CARD-472 planning (end-to-end check of the training handshake), qa `f895c0cc`
> **Related**: CARD-472 (fixes the modal buttons), CARD-306 (keep-one: training lives in the Factory), CARD-159 (handshake), CARD-270 (gap status)

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine and plan. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes |

## Four Beats

**Beat 1: What Jacob means.** If AutoReiv can train an agent in the background (the Factory "autonomous loop"), there should be one obvious place to start a run, see past runs and open their Lab Monitor. If that loop isn't product anymore, it should go away cleanly.

**Beat 2: What AutoReiv does now.**
- The backend is live and durable:
  - `POST/GET /api/agent_training_factory/jobs`, `GET /jobs/{id}`, `/step`, `/promote` and `DELETE` (`routers/agent_training_factory.py` L237-439). Creating a job returned 200 with a `job_id` in the CARD-472 repro; jobs are stored in the DB.
  - `POST /api/agents/{id}/gaps/{gap}/train` (`routers/gaps.py` L117) also exists.
- The UI has no entry point:
  - CARD-306 removed the Chat "Train agent" switch and said "Training Factory owns training".
  - Factory Studio (`factory.js`) builds agents and assigns skills, but has no "start training", no job list and no Lab Monitor button.
  - Forge's Lab Monitor button (`forge/lab_monitor.js` L563-574) and the gap "Open Training Factory" button (`forge/tools.js` L88-100) both just open Factory Studio.
  - Lab Monitor opens only from an `open-lab-drawer-btn` link in chat (`chat/render.js` L780), which is written when a job starts.
  - The only UI that starts a job is the training modal, which opens only from Lab Monitor → Retry.
  - Nothing in the UI calls the gap `/train` endpoint.

**Beat 3: What will change (depends on D1).**
- (a) **Rehome:** Factory Studio gets a "Training runs" panel. It lists jobs from `GET /jobs`, has a **Train this agent** button that opens the existing handshake modal for the selected agent, and each row opens Lab Monitor. The gap "Open Training Factory" button pre-fills from the gap (or calls the gap `/train` endpoint).
- (b) **Retire:** remove the handshake modal, Lab Monitor, the Retry flow, the gap `/train` endpoint and the jobs router, together with their tests. Keep the skill distill/adopt path (Teach), which is the live way agents learn today.

**Beat 4: What dies.** A backend feature that nobody can reach from the UI.

## Acceptance criteria (EARS, for option a)

- **[REQ-495-001]** WHEN Jacob opens Factory Studio with an agent selected, THE SYSTEM SHALL list that agent's training runs (newest first) with status. Each row SHALL open Lab Monitor on that job.
- **[REQ-495-002]** WHEN Jacob clicks **Train this agent**, THE SYSTEM SHALL open the handshake modal targeted at that agent, and Start SHALL create a job through `POST /api/agent_training_factory/jobs`.
- **[REQ-495-003]** WHEN Jacob clicks "Open Training Factory" on a capability gap, THE SYSTEM SHALL open Factory Studio on that agent with the gap's intent pre-filled in the handshake.

## Decisions

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Rehome or retire the autonomous loop | (a) rehome in Factory Studio; (b) retire the loop, UI and endpoints | **Jacob's call.** Lean **(a)**: the backend works and saves jobs, CARD-306 already named the Factory as the owner, and the UI pieces (modal, Lab Monitor, Retry) exist once CARD-472 lands. Choose (b) if Teach/Skill Studio is now the intended way to improve agents |
| D2 | Gap → train | (a) pre-fill the modal from the gap; (b) call the gap `/train` endpoint directly | **(a)**: one launch path, one set of tests |

## Test plan (sketch)

Vitest for the Factory runs panel (list render, row → `openLabMonitorDrawer`, Train → modal with the agent), and smoke on desktop and phone: Factory → Train → Start → Lab Monitor shows the job. pytest only if option (b) removes routers (drop their tests and assert 404).

## Runbook (option a)

Open Factory Studio, pick an agent and click **Train this agent**, then Launch. Lab Monitor shows the new run, and it appears in the runs list. Reload: it's still listed.
