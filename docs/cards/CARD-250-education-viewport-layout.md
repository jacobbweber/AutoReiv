# [CARD-250] Education Studio Viewport Layout (Learning OS usable)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - All Learning OS panels usable in one viewport (wrap/stack or in-panel scroll) — no sideways peek / forever-horizontal overflow. Don't reopen 242–249. Lumina out of scope. CoS scaffold + Architect locked Done = build now for P0 Studio usability.
> **Labels**: type:fix, P0, Education, LearningOS, UX, Viewport
> **Branch**: `feat/education-viewport-layout-250` (off `grok` @ 0e4cb94)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob needs **Education Studio usable** — every Learning OS panel (Quiz, Elaboration, Construction, Application, Analysis, Environment, Amplifiers) reachable in **one viewport**.
2. No **sideways peek** / forever-horizontal overflow that hides panels off-screen.
3. Acceptable fixes: **wrap/stack** pedagogy columns **or** **overflow-y scroll inside** a bounded panel region.
4. Do **not** reopen CARD-242..249 pedagogy engines. Lumina / concept-player film stays out of scope.
5. P0 usability: Architect locked Done bar — ship layout so Studio is operator-usable now.

### Beat 2: What AutoReiv Does Now
1. CARD-237..249 shipped Ask + Learning OS panels into `#view-education`.
2. Panels sit as siblings under `lg:flex-row`, so wide Studio windows create **forever-horizontal** overflow — operators must sideways-scroll to peek Amplifiers / Environment / etc.
3. Vertical in-panel scroll exists on some lists (due list, error log) but **not** on the pedagogy column region as a whole.
4. Session list competes with panels in the same horizontal flex row.

### Beat 3: What Will Change
1. Wrap Learning OS pedagogy panels in `#educationPedagogyColumns` with **flex-wrap / stack** + **overflow-y-auto** + **overflow-x-hidden** (`min-w-0`) so content fits the viewport without sideways peek.
2. Ask pane + main column (`#educationMainColumn`) keep Studio chrome; Jobs list stays reachable below/beside pedagogy with its own vertical scroll.
3. Vitest locks the layout contract (panels inside wrap/scroll region; no forever-horizontal pedagogy row).
4. Cache-bust bump so Jacob's Ctrl+F5 picks up CSS/HTML.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-VP-001]**: All Learning OS pedagogy panels (Quiz through Amplifiers) are usable in one Education Studio viewport via wrap/stack and/or in-panel vertical scroll.
- [x] **[REQ-EDU-VP-002]**: Education Studio pedagogy region does **not** require forever-horizontal / sideways-peek overflow to reach panels (`overflow-x` hidden on pedagogy columns; `min-width: 0` on main column).
- [x] **[REQ-EDU-VP-003]**: Do not reopen CARD-242..249 pedagogy engines; Lumina / concept-player film remains OUT of scope.
- [x] **[REQ-EDU-VP-004]**: Vitest covers the viewport layout contract; cache-bust bumped for live verify.
- [x] **Proof**: vitest green + Jacob verify (Ctrl+F5, open Education — all panels visible without sideways peek).

## 3. Constraints

- Branch `feat/education-viewport-layout-250` off `grok` @ 0e4cb94. Never qa/main. Do **not** merge to grok until asked.
- Layout/CSS/HTML (+ light education.js contract) only — no SRS/quiz/amplifier engine changes.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (Studio vitest).
- Skip Lumina film.

## 4. Out of scope (follow-on)

- Lumina / concept-player film / video.
- Reopening or redesigning CARD-242..249 pedagogy APIs.
- Mobile-only redesign beyond wrap/stack + scroll.

## 5. Proof (when building)

- Vitest: `#educationPedagogyColumns` wraps Learning OS panels; overflow-y / overflow-x-hidden contract; panels still present; no Lumina.
- Live: Ctrl+F5 → Education — all panels reachable without sideways peek.
