---
id: CARD-504
title: "Needs-tool proposal card is titled \"Synthesized Skill\" instead of the missing tool"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-500
  - CARD-472
  - CARD-497
labels:
  - type:bug
  - area:chat
  - area:skills
  - P3
---

# [CARD-504] Needs-tool proposal card is titled "Synthesized Skill" instead of the missing tool

> **Status**: Ready
> **Created**: 2026-09-25 (found in the CARD-500 scratch repro)
> **Related**: CARD-500 (card shows `name` and `plain_summary`), CARD-472 (Ask Developer handoff), CARD-497 (`factory_escalation` rename)
> **Labels**: `type:bug`, `area:chat`, `area:skills`, `P3`
> **Note (CARD-520, 2026-09-26)**: the distill result key is now `tool_escalation` (old stored rows migrated at startup). Read `tool_escalation` first; `readToolEscalation()` in `modules/studios/tool_escalation.js` also reads the old key for one release.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** When Teach decides the agent needs a new tool, the card title tells me which tool.

**Beat 2: What AutoReiv does now.** A needs-tool distill answer has `name: null` and `skill_id: null`; the tool name is only in `factory_escalation.suggested_tool_name`. `renderSkillProposalCard` (`src/web/static/modules/studios/chat/render.js` L245) falls back to "Synthesized Skill", so the card reads "Skill Proposal: Synthesized Skill" above "Ask Developer to build this tool". Seen in `scratch/c500_desktop.json` (`needsToolCard.title`) after CARD-500. The empty "View Raw Runbook (SKILL.md)" section also shows, with nothing inside.

**Beat 3: What will change.** A needs-tool card is titled "Needs a tool: <suggested_tool_name>" (or "Needs a new tool" when no name was given) and hides the empty runbook section. Skill cards are unchanged.

**Beat 4: What dies.** The placeholder title and the empty runbook drop-down on needs-tool cards.

## 2. Acceptance criteria (EARS)

- **[REQ-504-001]** WHILE a proposal has `needs_tool: true`, THE card title SHALL read "Needs a tool: <factory_escalation.suggested_tool_name>", or "Needs a new tool" when that is empty.
- **[REQ-504-002]** WHILE a proposal has no `runbook_markdown`, THE card SHALL NOT show "View Raw Runbook (SKILL.md)".
- **[REQ-504-003]** `render.js` SHALL NOT grow (CARD-456 line cap).

## 3. Decisions (recommendations; Jacob to confirm or change)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Title wording | "Needs a tool: X" / "Tool request: X" / keep "Skill Proposal" prefix | **"Needs a tool: X"**: says what happened in plain words |
| D2 | Where the tool name comes from | `factory_escalation.suggested_tool_name` now / wait for CARD-497 rename | **Read both** `tool_escalation` and `factory_escalation` so CARD-497 does not break it |

## 4. Failing-tests-first plan

- Vitest: needs-tool proposal with `suggested_tool_name: 'get_city_weather'` renders "Needs a tool: get_city_weather", not "Synthesized Skill"; without a name renders "Needs a new tool"; no `runbook_markdown` renders no "View Raw Runbook".
- Smoke: extend TC-36 so the needs-tool fixture title reads "Needs a tool: get_tc36_tool" (desktop and phone).

## 5. Runbook (Jarvis, after build)

1. Desktop http://127.0.0.1:8000 (Ctrl+F5): in a chat, click Teach on a reply, type a lesson that needs a tool the agent lacks (for example "look up live weather for my city"), click Distill.
2. If the card offers "Ask Developer to build this tool", its title reads "Needs a tool: <name>" and there is no empty "View Raw Runbook" section.
3. Phone http://192.168.1.99:8000: same check.

## 6. Out of scope

- Adopt going live: CARD-502. Distill timeout: CARD-503. Factory rename: CARD-497.
