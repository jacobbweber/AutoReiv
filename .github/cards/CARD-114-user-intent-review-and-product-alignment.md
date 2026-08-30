# [CARD-114] User intent review and product alignment

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/user-intent-review/
> **Labels**: 	ype:docs, 	ype:review

---

## 1. Why / Intent
Jacob is new to software. AutoReiv grew a lot of names (skill, tool, workflow, job, card, routine, agent) and a lot of leftover paths. Before more product work, we need a plain-language map of **what we meant** versus **what the code actually does today**, so Jacob can walk features one by one and tell Grok his intent.

This card is a **review artifact**, not coding work. Do not implement product fixes on this card.

---

## 2. What to Build
- Spec folder docs/specs/user-intent-review/ (short EARS wrapper).
- **SSOT:** docs/specs/user-intent-review/findings.md — numbered, verified against current qa code.
- CHANGELOG Unreleased note that this card opened.
- Local commit only. Do not push. Do not implement product fixes.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Spec folder exists with a short EARS requirements wrapper.
- [x] indings.md is the SSOT: each finding has Plain name, In the code, What we meant, What it actually does today, Why that’s a problem, Severity.
- [x] Review covers kernel/chat/HITL/Forge/packs/ACE/data-dir/SDLC/cards, not only the chat recap.
- [x] Already-known product gaps are stated as findings and checked against code.
- [x] CHANGELOG Unreleased records that CARD-114 opened.
- [x] Local commit only. No product code. No push.

---

## 4. Constraints & Honor Flags
- Work on qa. Do not push. Do not clone.
- Do not implement product fixes on this card.
- Audience: Jacob is new to software. No LangGraph lecture.
- Jacob will next set a plain-language dialogue, then walk features one by one.
