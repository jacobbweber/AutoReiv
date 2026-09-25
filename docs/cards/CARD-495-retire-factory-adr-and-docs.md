---
id: CARD-495
title: "Retire the Agent Training Factory (1/4): ADR-0060 and steering docs"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-496
  - CARD-497
  - CARD-498
  - CARD-472
  - CARD-417
  - CARD-418
  - CARD-386
  - CARD-368
  - CARD-306
labels:
  - type:product
  - area:factory
  - area:docs
  - P1
---

# [CARD-495] Retire the Agent Training Factory (1/4): ADR-0060 and steering docs

> **Status**: Ready
> **Created**: 2026-09-25 (replaces the earlier CARD-495 "training loop has no front door", written the same day)
> **Series**: CARD-495 (ADR and docs), then CARD-496 (UI shell), CARD-497 (backend), CARD-498 (data). Build in that order; each lands on its own branch.
> **Related**: CARD-472 (keep-and-fix chat wiring), CARD-417/418 and ADR-0057 (three Studios), CARD-386 (already deleted the Factory runs and pipeline views), CARD-368 (gaps to the backlog), CARD-306
> **Labels**: `type:product`, `area:factory`, `area:docs`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** "We built Agent, Skill and Tool Studios so we no longer need the Factory." The Factory concept is retired: no Factory screen, no autonomous training loop, no Lab Monitor. Improvement happens through the Studios, the Developer, Teach and Observability.

**Beat 2: What the docs say now.**
- ADR-0057 L54 calls the Factory scaffolder "transitional", and L37 rejects "Keep all-in-one Factory". But no ADR retires it.
- ADR-0056 L144 still says "Factory is the sole writer of skill bodies and tool bindings", which has been false since CARD-418 moved that to Skill Studio.
- `steering/product.md` L53 lists "factory" as a current studio. `roadmap.md` L81-82 frames CARD-386/387 as the Factory overhaul. `structure.md` L41 is silent.
- CARD-306 L9/L17 promise "Factory Train button + handshake modal retained", which CARD-386 already undid.

**Beat 3: What will change.**
- A new **ADR-0060 "Retire the Agent Training Factory"**. It amends ADR-0056 L144 (Skill Studio is the writer), completes ADR-0057 §4.1 (L54), and supersedes ADR-0048 (autonomous pack factory) and ADR-0049's Factory framing.
- It records the replacement path and the order of CARD-496..498.
- Update `steering/product.md` (studio list without "factory"; Agent Forge Studio described as Agent Studio), `roadmap.md` (a retirement entry), and `structure.md`.
- Mark CARD-159/164/171/182/195/351 as superseded in the ADR's table (the card files stay as history).

**Beat 4: What dies.** The idea that the Factory owns training, in any doc.

## 2. Acceptance criteria (EARS)

- **[REQ-495-001]** THE SYSTEM docs SHALL contain `docs/adr/0060-retire-agent-training-factory.md` (Accepted after Jacob's review) that names what dies, the replacement path per need, the data policy (CARD-498) and the order CARD-496..498.
- **[REQ-495-002]** `steering/product.md`, `roadmap.md` and `structure.md` SHALL NOT list a Factory studio as current.
- **[REQ-495-003]** ADR-0056 SHALL carry a dated amendment note that Skill Studio (not Factory) writes skill bodies and bindings.

## 3. ADR-0060 draft plan (not the ADR itself)

**Memory note (keep):** On 2026-09-25 at 3:44 PM ET, Jacob confirmed retiring the Factory concept ("We built Agent, Skill and Tool Studios so we no longer need the Factory, but we have other mechanisms for training and improvement") and accepted every recommendation in the CARD-472 revised report:
- CARD-472 is keep-and-fix only.
- The retirement is CARD-495..498.
- Teach stays as a Skills feature.
- Needs-tool escalation goes to a Developer chat (Tools Studio fallback).
- Factory data is exported on startup, then the tables are dropped a release later.

Evidence gathered in that planning pass:
- Factory Studio (`factory.js`, 251 lines) saves nothing; its only call is `GET /api/agents`.
- The Lab Monitor and training popup are reachable only from an existing job.
- Jacob's live DB has 0 rows in all `factory_*` tables and 0 capability gaps (read-only check).
- The `autoreiv` pack's `agent-authoring` skill still grants `launch_factory_training`.

**Replacement path for the ADR:**

| Need | Before (Factory) | After |
|------|------------------|-------|
| Agent identity, prompt, skill on/off | Factory col 1 (unsaved) and Agent Studio | **Agent Studio** |
| Author or refine a skill | Factory workshop | **Skill Studio** (Developer-mediated Build/Review, CARD-420/422) |
| New tool | 8-phase loop / `launch_factory_training` | **Tools Studio** form, then Developer (native or MCP lane, CARD-423) |
| A failed turn becomes a lesson | Teach escalation to Factory | **Teach** proposal (skill), or "Ask Developer to build this tool" (CARD-472) |
| Capability gap | Backlog "Open Training Factory" | Agent Studio backlog: **Open in Skill Studio** or **Ask Developer** (CARD-496) |
| Operational tuning | Factory phases | **Observability** friction and architectural proposals |

**ADR outline:** Context (ADR-0057 transitional; CARD-386 already removed runs/pipeline) → Drivers ("no theatre Studios without durable state", ADR-0057 L28) → Options (keep the thin shell / re-home the loop / retire; **retire chosen**) → Consequences (routes moved, tables exported then dropped, tests pruned under ADR-0055).

## 4. Tests

Docs only. Add a Vitest/pytest docs contract that `steering/product.md` has no `factory` in its current-studio list, and that ADR-0060 exists and mentions CARD-496..498.

## 5. Runbook

Read ADR-0060 and the steering diffs. The Factory is not described as a current studio anywhere in `steering/`.
