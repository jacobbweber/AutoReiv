# [CARD-332] Assistant constitution Wiki scrub

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: Clarify vs CARD-269 agent instructions backfill before build
> **Labels**: type:feature, P1, Assistant, Wiki, Constitution, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Drop **Wiki-specific operating instructions** from Assistant (brain dump Addition 6).
2. Assistant stays the **general day-to-day helper**.
3. Wiki work stays with the **Wiki agent** — not smuggled into Assistant constitution.

### Beat 2: What AutoReiv Does Now
1. Assistant constitution / instructions may still carry Wiki-specific operating guidance.
2. CARD-269 agent instructions backfill may overlap (fold vs standalone unclear).
3. Risk of two agents owning Wiki operating procedure, or Assistant remaining Wiki-shaped.

### Beat 3: What Will Change
1. Scrub Wiki-specific operating instructions out of Assistant.
2. Leave Wiki operating procedure with Wiki agent.
3. Confirm fold vs standalone vs CARD-269 before any edit. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [ ] **[REQ-ASST-WIKI-001]**: Assistant constitution / instructions no longer carry Wiki-specific operating procedure.
- [ ] **[REQ-ASST-WIKI-002]**: Assistant remains general day-to-day helper scope.
- [ ] **[REQ-ASST-WIKI-003]**: Wiki work / Wiki operating instructions stay with Wiki agent.
- [ ] **[REQ-ASST-WIKI-004]**: Proof: diff + live smoke that Assistant no longer routes Wiki ops as its constitution. No toast-only Done.

---

## 3. Needs discussion

**Overlap CARD-269 agent instructions backfill** — Architect locked: decide **fold vs standalone** before build. Do not edit constitutions until Jacob/Architect confirm whether this scrub folds into CARD-269 or ships as its own Done bar.

---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first where applicable. Leave `uv.lock` dirty/uncommitted.
- **Do not implement** until Needs discussion (CARD-269 overlap) is resolved.
- No product code on this scaffold commit.

---

## 5. Out of scope

- Broader agent-fleet constitution rewrite
- Help Studio (CARD-331)
- Education Studio Learning OS cards

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-332**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
