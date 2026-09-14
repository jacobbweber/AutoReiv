# [CARD-330] Platform skill tiers (required / optional / agent-pack)

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-199–203 platform/pack inventory (discuss Done bar first)
> **Labels**: type:feature, P1, Platform, Skills, Packs, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Enforced tiers at **mount time**: required platform, optional platform, agent-pack only.
2. Not folder-layout theatre — tiers must change what actually mounts / is callable.
3. Operator can tell required vs optional vs pack-only without reading folder trees.

### Beat 2: What AutoReiv Does Now
1. CARD-199–203 already did substantial platform / pack / tier architecture work.
2. Mount-time enforcement of required / optional / agent-pack-only may be partial or Done-bar ambiguous vs those cards.
3. Risk of “tiers” that are docs/folders only without mount enforcement.

### Beat 3: What Will Change
1. Mount-time enforcement for the three tiers (required platform / optional platform / agent-pack only).
2. Honest failure when a required platform skill is missing; optional skips cleanly; pack-only stays pack-scoped.
3. TDD + Jarvis live smoke. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [ ] **[REQ-SKILL-TIER-001]**: Mount-time enforcement distinguishes required platform, optional platform, and agent-pack-only skills.
- [ ] **[REQ-SKILL-TIER-002]**: Missing required platform skill fails honestly at mount (no silent degrade theatre).
- [ ] **[REQ-SKILL-TIER-003]**: Optional platform skills may be absent without blocking mount; agent-pack-only stay pack-scoped.
- [ ] **[REQ-SKILL-TIER-004]**: Proof: failing test → green; Jarvis live smoke. Not folder-layout theatre.

---

## 3. Needs discussion

**Overlap CARD-199–203** — Architect locked: must discuss **Done bar vs existing platform/pack work** before build. Confirm what is already shipped on those cards vs what this card still owns.

---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- **Do not implement** until Needs discussion (CARD-199–203 overlap) is resolved.
- No product code on this scaffold commit.

---

## 5. Out of scope

- Capability-gap smoke (CARD-329)
- Education Studio course chrome
- Renaming Platform vs Global product language beyond existing locks

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-330**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
