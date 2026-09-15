# [CARD-333] Education delivery profiles

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: Keep separate from CARD-327 adaptive depth; confirm UX placement before build
> **Labels**: type:feature, P1, Education, UX, DeliveryProfiles, Studio, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Selectable **presentation / delivery profile** (e.g. ADHD/focus) — how material is presented.
2. Separate from **academic depth** (kindergarten → graduate) owned by CARD-327.
3. Studio chrome for picker; honest empty states; depth vs presentation stay separate (UI/UX).

### Beat 2: What AutoReiv Does Now
1. CARD-327 covers adaptive depth / mastery chrome; no delivery-profile picker.
2. Risk of collapsing presentation profile into the depth control (theatre / confused UX).
3. Empty states for missing profile / unset preference are undefined.

### Beat 3: What Will Change
1. Delivery-profile picker in Education Studio chrome, visually separate from academic depth control.
2. Empty / unset states are honest; profile does not mutate depth ladder semantics.
3. TDD + Jarvis live smoke after UX placement lock. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [x] **[REQ-EDU-DELIVERY-001]**: Selectable presentation / delivery profile (e.g. ADHD/focus) exists in Education Studio.
- [x] **[REQ-EDU-DELIVERY-002]**: Delivery profile is separate from academic depth (kindergarten→graduate); does not replace CARD-327 depth model.
- [x] **[REQ-EDU-DELIVERY-003]**: Studio control for delivery profile is **visually separate** from the academic depth control.
- [x] **[REQ-EDU-DELIVERY-004]**: Empty / unset states are honest (no fake “profile applied” theatre).
- [x] **[REQ-EDU-DELIVERY-005]**: Proof: TDD + Jarvis live smoke. Labels include Education, UX.

---

## 3. Needs discussion

**Overlap CARD-327 adaptive depth** — Resolved: Architect & Product locked separate controls. Delivery profile controls presentation pacing, timers, and bite-size only, without altering depth ladder or SRS intervals.

**Studio control for delivery profile must stay visually separate from academic depth control** — Resolved: Implemented `#educationDeliveryProfileToolbar` with emerald styling and active profile badge (`#educationActiveDeliveryProfileBadge`), distinctly separated from sky-blue `#educationCourseChrome` (CARD-327).


---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- **Do not implement** until Needs discussion (CARD-327 separation + UX placement) is resolved.
- Do **not** change CARD-327 Status from this card's work.

---

## 5. Out of scope

- Adaptive depth / mastery ladder (CARD-327)
- Knowledge-type teaching artifacts (CARD-334)
- Amplifiers / Lumina (CARD-328)

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-333**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
