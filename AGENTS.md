# AGENTS.md — AutoReiv coding-assistant governance

> **Human**: Visionary, Product Owner, Final QA.  
> **AI coding assistant** (Cursor / Grok Bot / Antigravity): Principal engineer for SDLC — specs, TDD, verification, docs.  
> **Not** AutoReiv product packs. Product agents live under `platform-packs/` → user-data packs.

---

## Where things live (read the right file)

| Place | Owns |
| --- | --- |
| **This file (`AGENTS.md`)** | High-level governance only |
| **`.agents/rules/`** | Granular coding rules (globs / always-on / model-decision) |
| **`.agents/skills/`** | On-demand runbooks (preflight, TDD, RTM, ADR, serve, honesty gate) |
| **`steering/`** | AutoReiv **product**: `product.md`, `tech.md`, `structure.md`, `roadmap.md` |
| **`docs/specs/`** + **`docs/adr/`** | Kiro-style feature contracts and lasting decisions |
| **`docs/cards/`** | Active work cards (Three Beats) |

---

## How we walk cards with Jacob

This wins over conflicting older “continue alone = approval” wording.

- **Voice**: Plain sentences. What he sees and what it is for. Real technical names. Exact folder/path and the reply phrase he should use (`continue` / `build` / `merge to qa`). No tip/green-red/shorthand aimed at him.
- **One primitive at a time**: agent, skill, tool, job, pack, Studio.
- **Three beats before code**: (1) what he means (2) what AutoReiv does now (3) what will change.
- **Cards**: Scaffold Ready → he says **build** → implement → In Review → he live-tests. Long roadmaps stay in `steering/roadmap.md`.
- Details: `.agents/rules/human-engagement.md` (always on).

---

## 5 hard invariants (non-negotiable)

1. **No code without an active card** — see `.agents/rules/single-card.md`.
2. **One card / one plan** — no multi-feature `implementation_plan.md`.
3. **Spec + visual/API contract + Socratic options before tests/code** — see `.agents/rules/sdd-ears.md` and skill `sdd-workflow`.
4. **Strict red-green-refactor TDD** — see `.agents/rules/tdd-invariants.md` and skill `tdd-cycle`.
5. **Session hygiene** — `feat/*` from `qa`; conventional commits; update `CHANGELOG.md` `[Unreleased]`; do not push/merge/tag unless he asks; do not reset local `qa` to origin.

---

## Runtime product locks (do not reverse)

- Skill = one `SKILL.md` runbook. Tool = one callable. Pack = packaging of **one** agent. Name is **Platform**, not Global.
- Chat still lists that agent’s ticked tools every turn.
- `<agent>_storage.db` ≠ `<agent>_memory.db` — both under **user data** `packs/<id>/`, never the git checkout.
- Checkout hygiene: `.agents/rules/checkout-hygiene.md`.  
- `.agents/` vs packs: `.agents/rules/agents-vs-packs.md`.

---

## Definition of Done (pointer)

Before In Review / merge: follow `.agents/rules/definition-of-done.md` and run skill **`preflight`**. Control-plane tips also need skill **`honesty-smoke-gate`**. Serve restart: skill **`serve-hygiene`**.

---

## Single entry file

**`AGENTS.md` only** at repo root. Do not add parallel constitutions (`GEMINI.md`, `PROJECT.md`, etc.).
