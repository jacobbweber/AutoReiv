# [CARD-328] Education Learning OS — Amplifiers / Lumina polish (LAST)

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/card-328-education-amplifiers-lumina`
> **Depends**: CARD-321–327 Done
> **Labels**: type:feature, P2, Education, LearningOS, Amplifiers, Lumina, Polish, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Amplifiers (Lumina-style) polish only **AFTER** core Learning OS course path is real.
2. Honest wiring to existing ledger / course state — no fake autonomy.
3. Dedicated Lumina Studio (`#luminaStudio`) for multimodal concept cinema and visual layout exploration.
4. Harmonized bridge: Lumina films can be sent directly into the Education course pipeline; Education Studio's `amplifiers` step wires visual schemas to `education_course` and `education_mastery`.

### Beat 2: What AutoReiv Does Now
1. Amplifiers parked repeatedly; course step 9 `amplifiers` fell back to a generic study note.
2. Core course path (320–327) is fully Done on `qa`.
3. Standalone Grok prototype in `D:\Projects\Exprimentation\Lumina-grok-workspace` has rich 14-archetype SVG engine and concept player, but runs in React/Node sandbox.
4. AutoReiv lacks Lumina Studio navigation and native concept playback.

### Beat 3: What Will Change
1. Native Lumina Studio in AutoReiv navigation (`#luminaStudio`) with stage player (audio/narration, timeline scrub, subtitles, ambient visuals).
2. Pure ES Module SVG visual layout engine implementing 14 geometric archetypes (`flow`, `cycle`, `compare`, `orbit`, `stack`, `split`, `wave`, `network`, `scale`, `balance`, `grow`, `transform`, `pipeline`, `system`).
3. Seeded starter lessons (Photosynthesis, Black Holes, Entropy, Recursion, etc.) + LLM lesson composition API.
4. Education course pipeline step 9 (`amplifiers`) properly generates and persists visual amplifier schemas to `education_course` + `education_mastery` in agent `memory.db` without fake autonomy.
5. Bidirectional bridge: "Send to Education Course" from Lumina Studio, and "Watch in Lumina" from Education Studio.

---

## 2. Acceptance

- [x] **[REQ-EDU-AMP-001]**: Amplifier / Lumina surfaces wire to existing `education_course` + mastery ledger state.
- [x] **[REQ-EDU-AMP-002]**: No fake autonomy / no second storage brain (same agent `memory.db`).
- [x] **[REQ-EDU-AMP-003]**: Lands only after core Learning OS course path (CARD-321–327 Done).
- [x] **[REQ-EDU-AMP-004]**: Proof: honest demo or smoke; no toast-only “amplified” Done.
- [x] **[REQ-EDU-LUM-001]**: Dedicated Lumina Studio in navigation (`#luminaStudio`) with stage player (timeline, narration, scrub, ambient lighting).
- [x] **[REQ-EDU-LUM-002]**: SVG visual engine supporting the 14 visual archetypes with packet animations and glowing nodes.
- [x] **[REQ-EDU-LUM-003]**: Starter lessons seeded + backend composition endpoint via LLM gateway.
- [x] **[REQ-EDU-LUM-004]**: Bridge between Lumina Studio and Education Studio courses.

---

## 3. Constraints

- Branch `feat/card-328-education-amplifiers-lumina`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Replacing course pipeline
- Adaptive depth / Tutor core work (those are earlier cards)
- Shipping amplifiers before CARD-321–327

## 5. Wave order

1. **CARD-320** — Course + Mastery model (**In Review**)
2. **CARD-321** — Dual Coding as real course step
3. **CARD-322** — Wiki templates for every Education artifact
4. **CARD-323** — Elaboration course step
5. **CARD-324** — Construction / Application labs
6. **CARD-325** — Environment framing + Analysis→Retention handoff
7. **CARD-326** — Tutor agent (Wiki + ledger aware)
8. **CARD-327** — Adaptive depth + mastery chrome + Studio usability
9. **CARD-328** — Amplifiers / Lumina polish (**P2**, last)

Hold merge to `qa` until Jacob says **merge to qa**. Do not merge earlier cards into `qa` from this wave without Jacob.


## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-328**)
- After live OK → Jacob: **merge to qa**
