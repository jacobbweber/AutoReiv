# [CARD-116] Research first-class per-agent memory (agent brain)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/per-agent-memory/
> **Labels**: `type:research`, `type:docs`

---

## 1. Why / Intent
Jacob's intent (2026-08-30): each agent needs an **independent brain**, first-class — not one markdown file shared by all agents, and not only Chat session history.

Today AutoReiv has chat transcripts (session persistence plus `history_retention_days`) and a shared episodic fact store (CARD-042, entity/key auto-recall). CARD-114 Finding 22 already notes ACE playbook notes are snapshots, not a second brain. Alignment talks pointed at the same gap: agents do not have their own lasting memory.

This card is **exploratory research** (what system to build). It is not a coding card and does not pick a vendor.

---

## 2. What to Build
Research only. Do not implement product Python/JS on this card.

- Decide what a first-class per-agent brain is, versus session history and versus a single shared memory file.
- Study Hermes `MEMORY.md` / `USER.md` as **prior art**, not a spec to copy blindly.
- Agent Studio, per agent: fine-tune controls for how long facts live and other levers, with **hard min/max**.
- Related reading: CARD-114 findings on memory; alignment talks; existing specs `agent-kernel-memory`, `episodic-memory-and-auto-recall`, `agent-session-history-retention` (chat prune is not the brain).
- Short spec stub: `docs/specs/per-agent-memory/requirements.md` (research constraints only).
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Research outcome names what system to build for a first-class per-agent brain. No vendor is selected on this card.
- [ ] Independent per-agent brain is distinguished from Chat session history and from one markdown file for all agents.
- [ ] Agent Studio per-agent levers (how long facts live and other controls) include hard min/max; later design must honor those bounds.
- [ ] Hermes `MEMORY.md` / `USER.md` studied as prior art, not copied blindly. CARD-114 memory findings and alignment talks are accounted for.
- [ ] No product Python/JS. Status stays **Ready** (backlog) until research is accepted. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Do not pick a vendor (vector DB, hosted memory SaaS, LangGraph, etc.) in this card.
- Do not treat Hermes MEMORY.md/USER.md, CARD-042 episodic facts, or ACE notes as the design.
- Session history retention (`history_retention_days`) is related but is not the agent brain.
